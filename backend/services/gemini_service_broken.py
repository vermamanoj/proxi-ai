
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
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            log_system("CRITICAL: GEMINI_API_KEY not found.", "ERR")
        
        try:
            init_db()
        except Exception as e:
            log_system(f"DB Init Failed: {e}", "ERR")

        self.desktop_service = get_desktop_service()

        # 1. EXECUTION MAP
        self.tools_map = {
            "get_server_time": get_server_time,
            "get_system_health": self.get_system_health_wrapper, 
            "update_github_file": update_github_file,
            "create_github_issue": create_github_issue,
            "send_slack_message": send_slack_message,
            "create_linear_ticket": create_linear_ticket,
            "query_knowledge_base": query_knowledge_base,
            "assign_mission": assign_mission,
            "report_execution": report_execution,
            "verify_mission": verify_mission,
            "escalate_to_human": escalate_to_human,
            "add_item": add_item,
            "update_item_status": update_item_status,
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
            "browser_command": self.browser_command
        }

        # 2. DEFINITION LIST
        self.tool_definitions = [
            types.FunctionDeclaration(
                name="assign_mission",
                description="Starts a verifiable mission. Use this when the user reports a problem like 'Health Check', 'Fix CPU', or 'Deploy'.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "goal": types.Schema(type=types.Type.STRING, description="The objective"),
                        "verification_criteria": types.Schema(
                            type=types.Type.OBJECT, 
                            description="Metrics to verify success (e.g. {'metric': 'cpu', 'threshold': 50})"
                        )
                    },
                    required=["goal", "verification_criteria"]
                )
            ),
            types.FunctionDeclaration(
                name="get_system_health",
                description="Retrieves current CPU, Memory, and System Status.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={})
            ),
             types.FunctionDeclaration(
                name="get_server_time",
                description="Gets server clock time.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={})
            ),
            types.FunctionDeclaration(
                name="run_terminal_command",
                description="Executes a shell command.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"command": types.Schema(type=types.Type.STRING)},
                    required=["command"]
                )
            ),
            types.FunctionDeclaration(
                name="look_at_screen",
                description="Takes a screenshot and analyzes it.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"purpose": types.Schema(type=types.Type.STRING)},
                    required=["purpose"]
                )
            ),
            types.FunctionDeclaration(
                name="report_execution",
                description="Call this when the task is done.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "mission_id": types.Schema(type=types.Type.STRING),
                        "summary": types.Schema(type=types.Type.STRING)
                    },
                    required=["mission_id", "summary"]
                )
            ),
            types.FunctionDeclaration(
                name="browser_command",
                description="Controls the web browser.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": types.Schema(type=types.Type.STRING, enum=["NAVIGATE", "NEW_TAB", "CLOSE_TAB", "REFRESH", "SEARCH"]),
                        "url": types.Schema(type=types.Type.STRING)
                    },
                    required=["action"]
                )
            ),
            types.FunctionDeclaration(name="create_linear_ticket", description="Creates a ticket.", parameters=types.Schema(type=types.Type.OBJECT, properties={"title": types.Schema(type=types.Type.STRING), "priority": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="send_slack_message", description="Sends a Slack msg.", parameters=types.Schema(type=types.Type.OBJECT, properties={"channel": types.Schema(type=types.Type.STRING), "message": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="query_knowledge_base", description="Searches docs.", parameters=types.Schema(type=types.Type.OBJECT, properties={"query": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="escalate_to_human", description="Escalates failure.", parameters=types.Schema(type=types.Type.OBJECT, properties={"mission_id": types.Schema(type=types.Type.STRING), "reason": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="wait_seconds", description="Waits for X seconds.", parameters=types.Schema(type=types.Type.OBJECT, properties={"seconds": types.Schema(type=types.Type.INTEGER)})),
            types.FunctionDeclaration(name="click_at", description="Clicks at X,Y coordinates.", parameters=types.Schema(type=types.Type.OBJECT, properties={"x": types.Schema(type=types.Type.INTEGER), "y": types.Schema(type=types.Type.INTEGER)})),
            types.FunctionDeclaration(name="type_text", description="Types text.", parameters=types.Schema(type=types.Type.OBJECT, properties={"text": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="scroll_page", description="Scrolls page.", parameters=types.Schema(type=types.Type.OBJECT, properties={"direction": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="open_target", description="Opens file/url.", parameters=types.Schema(type=types.Type.OBJECT, properties={"resource": types.Schema(type=types.Type.STRING)})),
            types.FunctionDeclaration(name="read_page_content", description="Reads text from active page.", parameters=types.Schema(type=types.Type.OBJECT, properties={})),
        ]
        
        log_system(f"Gemini Service Initialized (New SDK) with {len(self.tools_map)} tools.", "INIT")

    # --- DESKTOP WRAPPERS ---
    def get_system_health_wrapper(self): return self.desktop_service.get_system_health()
    def click_at(self, x: int, y: int): return self.desktop_service.click_at(x, y)
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int): return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
    def type_text(self, text: str): return self.desktop_service.type_text(text)
    def press_hotkey(self, keys: list[str]): return self.desktop_service.press_hotkey(keys)
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
            response = self.client.models.generate_content(
                model=self.FAST_TEXT_MODEL,
                contents=[
                    f"Purpose: {purpose}. Describe UI layout and key elements.",
                    types.Part.from_bytes(data=base64.b64decode(base64_img), mime_type='image/jpeg')
                ]
            )
            return f"VISION: {response.text}"
        except Exception as e: return f"Vision Error: {e}"

    async def _execute_with_index(self, index: int, name: str, args: dict):
        func = self.tools_map.get(name)
        if not func: return (index, name, f"Error: Tool {name} not found")
        try:
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = await asyncio.to_thread(func, **args)
            return (index, name, res)
        except Exception as e: return (index, name, str(e))

    # --- THE HIVE ORCHESTRATOR (USING CHAT SESSION API) ---
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast"):
        log_system(f"NEW REQUEST: {message} (Mode: {complexity_request})", "ROUTER")
        
        if not self.api_key: 
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        final_tools = [types.Tool(function_declarations=self.tool_definitions)]
        
        # SYSTEM INSTRUCTION - REQUIRES TRANSPARENCY
        hive_instruction = """You are Proxi, a technical AI operator with OS-level access.

CRITICAL RULE - THINK BEFORE YOU ACT:
Before EVERY tool call, you MUST first explain:
1. WHAT you are about to do
2. WHY you are doing it
3. WHAT you expect to happen

Example: "I will check the running processes to identify CPU-intensive applications."
[Then call the tool]

GUIDELINES:
- For status checks: Explain what metric you're checking, then call the tool.
- For multi-step tasks: Start with `assign_mission` to define success criteria.
- For desktop actions: ALWAYS explain the targets before clicking.
- After each tool result: Briefly summarize what you observed.

SAFETY: You control real hardware. Never execute without explaining first."""

        # Model selection
        active_model = self.SMART_TEXT_MODEL if complexity_request == "deep" else self.FAST_TEXT_MODEL
        
        # Config with thinking enabled for transparency
        gen_config = types.GenerateContentConfig(
            temperature=0.3,
            tools=final_tools,
            system_instruction=hive_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
        
        yield json.dumps({"type": "status_change", "phase": "planning", "content": f"Initializing ({complexity_request} mode)..."}) + "\n"

        current_mission_id = None
        current_criteria = None
        max_turns = 20

        try:
            # CREATE CHAT SESSION - handles thought_signatures automatically
            chat = await self.client.aio.chats.create(
                model=active_model,
                config=gen_config
            )
            
            # Send initial message
            response = await chat.send_message(f"GOAL: {message}")
            
            for turn in range(max_turns):
                # Process response parts
                function_calls = []
                text_content = ""
                
                for part in response.candidates[0].content.parts:
                    # Stream thoughts for transparency
                    is_thought = getattr(part, 'thought', False)
                    if is_thought and part.text:
                        thought_preview = part.text[:100].replace('\n', ' ')
                        log_system(f"THINKING: {thought_preview}...", "THOUGHT")
                        yield json.dumps({"type": "llm_thought", "content": part.text}) + "\n"
                        continue
                    
                    if part.text:
                        text_content += part.text
                    
                    if part.function_call:
                        function_calls.append(part.function_call)
                
                # Stream text to UI
                if text_content:
                    log_system(f"LLM: {text_content[:100]}...", "RESPONSE")
                    yield json.dumps({"type": "response", "content": text_content}) + "\n"
                
                # No tools = done
                if not function_calls:
                    break
                
                # Execute tools
                yield json.dumps({"type": "tool_call_batch", "calls": [{"name": fc.name, "args": to_dict(fc.args)} for fc in function_calls]}) + "\n"
                
                tool_results = []
                for i, fc in enumerate(function_calls):
                    name = fc.name
                    args = to_dict(fc.args)
                    
                    yield json.dumps({"type": "status_change", "phase": "executing", "tool": name}) + "\n"
                    log_system(f"TOOL_CALL: {name}({args})", "EXEC")
                    
                    # Execute
                    _, _, res = await self._execute_with_index(i, name, args)
                    
                    # Mission tracking
                    if name == "assign_mission" and "Mission" in str(res):
                        try:
                            current_mission_id = str(res).split("Mission ")[1].split(" ")[0]
                            current_criteria = args.get('verification_criteria', {})
                        except: pass
                    elif name == "report_execution" and current_mission_id:
                        yield json.dumps({"type": "status_change", "phase": "verifying"}) + "\n"
                        evidence = await asyncio.to_thread(verify_mission, current_mission_id)
                        judgment = await self._verify_outcome(args.get('summary', 'Done'), evidence, json.dumps(current_criteria))
                        
                        if judgment.get('verified'):
                            finalize_mission(current_mission_id, "VERIFIED")
                            res = f"VERIFICATION PASSED: {judgment.get('reason')}"
                            yield json.dumps({"type": "verification", "status": "success", "reason": judgment.get('reason')}) + "\n"
                        else:
                            finalize_mission(current_mission_id, "FAILED")
                            res = f"VERIFICATION FAILED: {judgment.get('reason')}"
                            yield json.dumps({"type": "verification", "status": "failed", "reason": judgment.get('reason')}) + "\n"
                    
                    tool_results.append(types.Part(
                        function_response=types.FunctionResponse(name=name, response={"result": str(res)})
                    ))
                    yield json.dumps({"type": "tool_result", "name": name, "content": str(res)[:500]}) + "\n"
                
                # Send tool results back to chat - SDK handles thought_signature
                response = await chat.send_message(tool_results)
            
            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

        except Exception as e:
            log_system(f"HIVE ERROR: {e}", "ERR")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    async def _verify_outcome(self, claim, evidence, criteria):
        verifier_instruction = "You are a QA Auditor. Output JSON: {verified: bool, reason: str}."
        prompt = f"Claim: {claim}\nEvidence: {evidence}\nCriteria: {criteria}"
        try:
            # Stateless verification
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
        response = await self.client.aio.models.generate_content(
            model=self.VISION_MODEL,
            contents=[
                user_prompt,
                types.Part.from_bytes(data=image_bytes, mime_type='image/png')
            ]
        )
        return response.text
