
import os
import asyncio
import json
import warnings
import time
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv

# 1. Suppress Pydantic Warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# NEW SDK IMPORT
from google import genai
from google.genai import types

# Internal Imports
from backend.services.desktop.factory import get_desktop_service
from backend.utils.logger import log_system
from backend.database import init_db
from backend.services.orchestrator import (
    assign_mission, 
    report_execution, 
    verify_mission, 
    finalize_mission,
    escalate_to_human,
    add_item, 
    update_item_status
)

from backend.tools.standard_tools import (
    get_server_time,
    get_system_health,
    send_slack_message,
    create_linear_ticket,
    query_knowledge_base,
    update_github_file,
    create_github_issue
)

# 2. Force Load .env
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"

log_system(f"Loading environment variables from: {env_path}", "INIT")

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# --- Helper for Dict Conversion ---
def to_dict(obj):
    # The new SDK returns types that might need conversion
    if hasattr(obj, 'to_dict'): return obj.to_dict()
    if isinstance(obj, dict): return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list): return [to_dict(v) for v in obj]
    return obj

class GeminiService:
    
    AUDIO_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025" 
    FAST_TEXT_MODEL = "gemini-3-flash-preview"                  
    SMART_TEXT_MODEL = "gemini-3-pro-preview"                   
    VISION_MODEL = "gemini-3-pro-image-preview"                 

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
             # Manual fallback
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('GEMINI_API_KEY'):
                            self.api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
            except: pass
        
        # Initialize Client
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            log_system("CRITICAL: GEMINI_API_KEY not found.", "ERR")
        
        # Initialize DB
        try:
            init_db()
        except Exception as e:
            log_system(f"DB Init Failed: {e}", "ERR")

        # Initialize Desktop Service via Factory
        self.desktop_service = get_desktop_service()

        # MAPPING: Combines Standard Tools + Service Wrappers
        self.tools_map = {
            # Standard
            "get_server_time": get_server_time,
            "get_system_health": self.get_system_health_wrapper, 
            "update_github_file": update_github_file,
            "create_github_issue": create_github_issue,
            "send_slack_message": send_slack_message,
            "create_linear_ticket": create_linear_ticket,
            "query_knowledge_base": query_knowledge_base,
            
            # Orchestrator (Truth Layer)
            "assign_mission": assign_mission,
            "report_execution": report_execution,
            "verify_mission": verify_mission,
            "escalate_to_human": escalate_to_human,
            "add_item": add_item,
            "update_item_status": update_item_status,

            # Desktop (Motor + Sense)
            "click_at": self.click_at,
            "drag_mouse": self.drag_mouse,
            "type_text": self.type_text,
            "press_hotkey": self.press_hotkey,
            "look_at_screen": self.look_at_screen,
            "scan_ui_tree": self.scan_ui_tree,
            "wait_seconds": self.wait_seconds,
            "run_terminal_command": self.run_terminal_command,
            "open_target": self.open_target,
            "read_page_content": self.read_page_content,
            "scroll_page": self.scroll_page,
            
            # New Semantic Browser
            "browser_command": self.browser_command
        }
        log_system(f"Gemini Service Initialized (New SDK) with {len(self.tools_map)} tools.", "INIT")

    # --- DESKTOP WRAPPERS ---
    def get_system_health_wrapper(self): return self.desktop_service.get_system_health()
    def click_at(self, x: int, y: int): return self.desktop_service.click_at(x, y)
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int): return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
    def type_text(self, text: str): return self.desktop_service.type_text(text)
    def press_hotkey(self, keys: list): return self.desktop_service.press_hotkey(keys)
    def wait_seconds(self, seconds: int): return self.desktop_service.wait_seconds(seconds)
    def run_terminal_command(self, command: str): return self.desktop_service.run_terminal_command(command)
    def open_target(self, resource: str): return self.desktop_service.open_target(resource)
    def read_page_content(self): return self.desktop_service.read_page_content()
    def scroll_page(self, direction: str = 'down'): return self.desktop_service.scroll_page(direction)
    def browser_command(self, action: str, url: str = None): return self.desktop_service.browser_command(action, url)
    def scan_ui_tree(self): return self.desktop_service.scan_ui_tree()

    def look_at_screen(self, purpose: str):
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img: return "Screenshot failed"
        try:
            # Synchronous call via standard client for simplicity in tools
            response = self.client.models.generate_content(
                model=self.FAST_TEXT_MODEL,
                contents=[
                    f"Purpose: {purpose}. Describe UI layout and key elements.",
                    types.Part.from_bytes(data=base64.b64decode(base64_img), mime_type='image/jpeg')
                ]
            )
            return f"VISION: {response.text}"
        except Exception as e: return f"Vision Error: {e}"

    # --- EXECUTION ENGINE ---

    async def _execute_with_index(self, index: int, name: str, args: dict):
        func = self.tools_map.get(name)
        if not func: return (index, name, f"Error: Tool {name} not found")
        try:
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = await asyncio.to_thread(func, **args)
            return (index, name, res)
        except Exception as e: return (index, name, str(e))

    # --- THE HIVE ORCHESTRATOR (NEW SDK) ---
    
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast"):
        """
        HIVE Architecture using google-genai SDK (Gemini 3 Native).
        """
        log_system(f"HIVE ORCHESTRATOR: {message}", "ROUTER")
        
        if not self.api_key: 
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        hive_instruction = """
        You are Proxi, a Verifiable Autonomous Agent.
        
        **CORE PROTOCOL (The Triple Handshake):**
        1. **ASSIGN**: Start by using `assign_mission(goal, verification_criteria)`.
           - ALWAYS define criteria. E.g. {"metric": "cpu", "threshold": 80, "condition": "less_than"}.
        2. **EXECUTE**: Use tools (GCP, GitHub, Desktop) to fix the issue.
        3. **REPORT**: When done, call `report_execution(mission_id, summary)`.
        
        **HIGH-SPEED BROWSER NAVIGATION:**
        - You have access to `browser_command(action, url)`.
        - Actions: NEW_TAB, CLOSE_TAB, REFRESH, NAVIGATE, SEARCH.
        - PREFER this tool over manual clicking for web tasks.
        
        **STUCK DETECTION:**
        - If you try the same fix twice and it fails, STOP and call `escalate_to_human`.
        """

        # Provide tools as a list of callables. The SDK handles schema generation.
        tools_list = list(self.tools_map.values())
        
        # Configure Gemini 3 Thinking
        config = types.GenerateContentConfig(
            temperature=0.7,
            tools=tools_list,
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
        
        # Create Async Chat Session
        # CRITICAL FIX: Use client.aio for Async Chat
        chat = self.client.aio.chats.create(
            model=self.SMART_TEXT_MODEL,
            config=config
        )

        # Emit Initial Status
        yield json.dumps({"type": "status_change", "phase": "planning", "content": "Initializing Mission..."}) + "\n"

        full_prompt = f"{hive_instruction}\n\nGOAL: {message}"
        
        # State Tracking
        current_mission_id = None
        current_criteria = None
        verification_fails = 0
        
        # The ReAct Loop Variable
        next_input = full_prompt

        try:
            max_turns = 30
            current_turn = 0
            
            while current_turn < max_turns:
                current_turn += 1
                
                function_calls = []
                results_ordered = []
                text_buffer = ""
                
                # STREAMING REQUEST
                # We iterate the AsyncIterator returned by send_message_stream
                async for chunk in chat.send_message_stream(next_input):
                    if not chunk.candidates: continue
                    part = chunk.candidates[0].content.parts[0]
                    
                    # 1. Handle Thoughts
                    if part.thought:
                         log_system(f"THOUGHT: {part.text[:50]}...", "THOUGHT")
                         yield json.dumps({"type": "llm_thought", "content": part.text}) + "\n"
                    
                    # 2. Handle Text Response (The actual answer)
                    elif part.text:
                         text_buffer += part.text
                         # Optional: Yield partial text if desired, but buffering helps cleanliness
                         
                    # 3. Handle Function Calls
                    if part.function_call:
                         function_calls.append(part.function_call)

                # End of Stream for this Turn
                
                # If we received text (and it wasn't just a thought), send it to UI
                if text_buffer:
                    yield json.dumps({"type": "response", "content": text_buffer}) + "\n"

                # If no function calls, we are done
                if not function_calls:
                    break

                # PROCESS TOOLS
                safe_calls = []
                for fc in function_calls:
                    args = to_dict(fc.args)
                    safe_calls.append({"name": fc.name, "args": args, "id": fc.id if hasattr(fc, 'id') else None})
                
                yield json.dumps({"type": "tool_call_batch", "calls": safe_calls}) + "\n"

                # Execute
                tool_output_parts = []
                
                for i, call in enumerate(safe_calls):
                    name = call['name']
                    args = call['args']
                    
                    yield json.dumps({"type": "status_change", "phase": "executing", "tool": name}) + "\n"
                    _, _, res = await self._execute_with_index(i, name, args)
                    
                    # --- ORCHESTRATOR LOGIC (Intercepts) ---
                    if name == "assign_mission":
                        if "Mission" in str(res):
                            current_mission_id = str(res).split("Mission ")[1].split(" ")[0]
                            current_criteria = args.get('verification_criteria', {})
                    elif name == "report_execution":
                        # Verification Logic
                            if current_mission_id:
                            log_system(f"Verifying {current_mission_id}...", "SYS")
                            yield json.dumps({"type": "status_change", "phase": "verifying"}) + "\n"
                            
                            # Run verification in thread to avoid blocking loop
                            evidence = await asyncio.to_thread(verify_mission, current_mission_id)
                            
                            # Judge
                            judgment = await self._verify_outcome(args.get('summary', 'Done'), evidence, json.dumps(current_criteria))
                            
                            if judgment['verified']:
                                finalize_mission(current_mission_id, "VERIFIED")
                                res = f"VERIFICATION PASSED: {judgment['reason']}"
                                yield json.dumps({"type": "verification", "status": "success", "reason": judgment['reason']}) + "\n"
                            else:
                                finalize_mission(current_mission_id, "FAILED")
                                verification_fails += 1
                                res = f"VERIFICATION FAILED: {judgment['reason']}"
                                yield json.dumps({"type": "verification", "status": "failed", "reason": judgment['reason']}) + "\n"

                    # Build Response Part for Next Turn
                    tool_output_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=name,
                                response={"result": res}
                            )
                        )
                    )
                    yield json.dumps({"type": "tool_result", "name": name, "content": str(res)[:500]}) + "\n"

                # Set inputs for next loop iteration
                next_input = tool_output_parts
            
            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

        except Exception as e:
            log_system(f"HIVE ERROR: {e}", "ERR")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    async def _verify_outcome(self, claim, evidence, criteria):
        # Using a one-off generation for verification (Standard Client)
        verifier_instruction = "You are a QA Auditor. Output JSON: {verified: bool, reason: str}."
        prompt = f"Claim: {claim}\nEvidence: {evidence}\nCriteria: {criteria}"
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.SMART_TEXT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=verifier_instruction)
            )
            text = response.text
            start, end = text.find('{'), text.rfind('}') + 1
            return json.loads(text[start:end])
        except Exception as e:
            return {"verified": False, "reason": f"Verifier crash: {e}"}

    async def process_vision_command(self, image_bytes, user_prompt):
        # Async Vision
        response = await self.client.aio.models.generate_content(
            model=self.VISION_MODEL,
            contents=[
                user_prompt,
                types.Part.from_bytes(data=image_bytes, mime_type='image/png')
            ]
        )
        return response.text
