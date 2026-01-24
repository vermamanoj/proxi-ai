
import os
import asyncio
import json
import warnings
import time
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Suppress Google SDK Deprecation Warning
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.ai.generativelanguage import FunctionResponse, Part

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
    if not os.getenv("GEMINI_API_KEY"):
         # Manual parsing fallback
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('GEMINI_API_KEY'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            os.environ['GEMINI_API_KEY'] = parts[1].strip().strip('"').strip("'")
        except: pass

# --- Helper for Protobuf Conversion ---
def proto_to_dict(obj):
    if hasattr(obj, 'items'): return {k: proto_to_dict(v) for k, v in obj.items()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)): return [proto_to_dict(v) for v in obj]
    return obj

class GeminiService:
    
    AUDIO_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025" 
    FAST_TEXT_MODEL = "gemini-3-flash-preview"                  
    SMART_TEXT_MODEL = "gemini-3-pro-preview"                   
    VISION_MODEL = "gemini-3-pro-image-preview"                 

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
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
            "get_system_health": self.get_system_health_wrapper, # Route through wrapper
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
        log_system(f"Gemini Service Initialized with {len(self.tools_map)} tools.", "INIT")

    # --- DESKTOP WRAPPERS ---
    def get_system_health_wrapper(self):
        return self.desktop_service.get_system_health()

    def click_at(self, x: int, y: int):
        return self.desktop_service.click_at(x, y)
        
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
        
    def type_text(self, text: str):
        return self.desktop_service.type_text(text)
        
    def press_hotkey(self, keys: list):
        return self.desktop_service.press_hotkey(keys)
        
    def wait_seconds(self, seconds: int):
        return self.desktop_service.wait_seconds(seconds)
        
    def run_terminal_command(self, command: str):
        return self.desktop_service.run_terminal_command(command)
    
    def open_target(self, resource: str):
        return self.desktop_service.open_target(resource)

    def read_page_content(self):
        return self.desktop_service.read_page_content()

    def scroll_page(self, direction: str = 'down'):
        return self.desktop_service.scroll_page(direction)

    def browser_command(self, action: str, url: str = None):
        return self.desktop_service.browser_command(action, url)

    def look_at_screen(self, purpose: str):
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img: return "Screenshot failed"
        try:
            model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
            # Timeout for vision to avoid hangs
            res = model.generate_content([f"Purpose: {purpose}. Describe UI.", {'mime_type': 'image/jpeg', 'data': base64_img}], request_options={'timeout': 15})
            return f"VISION: {res.text}"
        except Exception as e: return f"Vision Error: {e}"

    def scan_ui_tree(self):
        return self.desktop_service.scan_ui_tree()

    # --- EXECUTION ENGINE ---

    async def _execute_with_index(self, index: int, name: str, args: dict):
        func = self.tools_map.get(name)
        if not func: return (index, name, f"Error: Tool {name} not found")
        try:
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = await asyncio.to_thread(func, **args)
            return (index, name, res)
        except Exception as e: return (index, name, str(e))

    async def _send_chat_message_with_healing(self, chat, content, retries=1):
        for attempt in range(retries + 1):
            try:
                # Add strict timeout and increase it for Thinking models
                return await asyncio.wait_for(
                    asyncio.to_thread(chat.send_message, content, request_options={'timeout': 60}), 
                    timeout=65
                )
            except asyncio.TimeoutError:
                log_system("Gemini API Timeout (65s) - Thinking took too long", "WARN")
                if attempt < retries: continue
                raise Exception("Gemini API timed out")
            except Exception as e:
                err_str = str(e)
                log_system(f"API Error ({attempt+1}/{retries+1}): {err_str}", "WARN")
                
                # Check for MALFORMED_FUNCTION_CALL specifically
                if "MALFORMED_FUNCTION_CALL" in err_str or "finish_reason" in err_str:
                     # This usually means the model hallucinated a tool or bad JSON
                     if attempt < retries:
                         log_system("Retrying due to Malformed Call...", "SYS")
                         # Small delay before retry
                         await asyncio.sleep(2)
                         continue
                
                if attempt < retries: continue
                raise e

    async def _verify_outcome(self, claim: str, evidence_json: str, criteria: str):
        """
        The Verifier Persona: A QA Auditor that judges if the task is complete.
        """
        verifier_instruction = """
        You are a Quality Assurance Auditor for Proxi.
        Your Job: Verify if the Worker Agent successfully completed the mission based on HARD EVIDENCE.
        
        INPUTS:
        1. Worker Claim: What the agent says it did.
        2. Real Metrics (Evidence): What the system actually shows (CPU, HTTP status, Visuals).
        3. Success Criteria: The conditions required for success.
        
        OUTPUT:
        Return ONLY a JSON object:
        {
            "verified": boolean,
            "reason": "Explanation of why it passed or failed based on the metrics."
        }
        
        Do not trust the Worker's claim unless the Metrics support it.
        """
        
        # Parse evidence to check for images
        evidence = {}
        try:
            evidence = json.loads(evidence_json)
        except:
            evidence = {"raw": evidence_json}

        # Build prompt parts
        prompt_text = f"Worker Claim: {claim}\nCriteria: {criteria}\n"
        
        prompt_parts = [prompt_text]
        
        # Multimodal Injection (Screenshots)
        if "screenshot_base64" in evidence:
            prompt_parts.append(f"Visual Evidence Target: {evidence.get('visual_target', 'Screen State')}")
            prompt_parts.append({'mime_type': 'image/jpeg', 'data': evidence['screenshot_base64']})
            # Remove huge base64 from text log to avoid clutter
            evidence_lite = evidence.copy()
            del evidence_lite['screenshot_base64']
            prompt_parts.append(f"System Vitals: {json.dumps(evidence_lite)}")
        else:
            prompt_parts.append(f"Real Metrics: {evidence_json}")

        try:
            model = genai.GenerativeModel(self.SMART_TEXT_MODEL, system_instruction=verifier_instruction)
            res = await asyncio.to_thread(model.generate_content, prompt_parts)
            
            # Extract JSON
            text = res.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            return {"verified": False, "reason": "Verifier output malformed."}
        except Exception as e:
            return {"verified": False, "reason": f"Verifier Error: {e}"}

    # --- THE HIVE ORCHESTRATOR ---
    
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast"):
        """
        HIVE Architecture: Planner -> Executor -> Verifier.
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
           - For Visuals: {"metric": "visual", "description": "Login button visible"}.
        2. **EXECUTE**: Use tools (GCP, GitHub, Desktop) to fix the issue.
        3. **REPORT**: When done, call `report_execution(mission_id, summary)`.
        
        **HIGH-SPEED BROWSER NAVIGATION:**
        - You have access to `browser_command(action, url)`.
        - Actions: NEW_TAB, CLOSE_TAB, REFRESH, NAVIGATE, SEARCH.
        - PREFER this tool over manual clicking for web tasks. It is 10x faster.
        - After navigating, use `read_page_content` to verify the page loaded (it scrapes text via Ctrl+A/Ctrl+C).
        - Only use Vision/Clicking if you need to interact with a specific button or complex UI element.
        
        **STUCK DETECTION:**
        - If you try the same fix twice and it fails, STOP and call `escalate_to_human`.
        - Do not lie about success. The Verifier will catch you.
        
        **TOOLS:**
        - `assign_mission`: Start.
        - `report_execution`: End.
        - `open_target`/`read_page_content`: Research.
        - `browser_command`: Fast web control.
        - `run_terminal_command`: Fix stuff.
        """

        tools = list(self.tools_map.values())
        
        # --- NEW: Enable Thinking Logic for Stability & Visibility ---
        generation_config = GenerationConfig(
            temperature=0.7,
            thinking_config={"thinking_budget": 1024} # Give the model a budget to plan
        )
        
        model = genai.GenerativeModel(
            model_name=self.SMART_TEXT_MODEL, 
            tools=tools,
            generation_config=generation_config
        )
        chat = model.start_chat(enable_automatic_function_calling=False)

        # Emit Initial Status
        yield json.dumps({"type": "status_change", "phase": "planning", "content": "Initializing Mission..."}) + "\n"

        full_prompt = f"{hive_instruction}\n\nGOAL: {message}"
        
        # State Tracking
        current_mission_id = None
        current_criteria = None
        verification_fails = 0
        
        try:
            response = await self._send_chat_message_with_healing(chat, full_prompt)
            
            max_turns = 30
            current_turn = 0
            
            while current_turn < max_turns:
                current_turn += 1
                
                # --- CRASH FIX: Check for Valid Candidate ---
                if not response.candidates:
                    err_msg = "No candidates returned. Model likely blocked."
                    if response.prompt_feedback:
                         err_msg += f" Feedback: {response.prompt_feedback}"
                    log_system(err_msg, "ERR")
                    yield json.dumps({"type": "error", "content": err_msg}) + "\n"
                    break
                
                # Check finish reason specifically
                candidate = response.candidates[0]
                # Finish Reason 5 = MALFORMED_FUNCTION_CALL
                # Finish Reason 3 = SAFETY
                # Finish Reason 4 = RECITATION
                if candidate.finish_reason not in [0, 1]: # 0=STOP, 1=MAX_TOKENS
                     reason_map = {3: "SAFETY", 4: "RECITATION", 5: "MALFORMED_FUNCTION_CALL"}
                     reason_str = reason_map.get(candidate.finish_reason, f"UNKNOWN({candidate.finish_reason})")
                     err_msg = f"Model stopped unexpectedly. Reason: {reason_str}."
                     log_system(err_msg, "ERR")
                     yield json.dumps({"type": "error", "content": err_msg}) + "\n"
                     break

                # --- Extract Content ---
                # Check for parts
                if not candidate.content or not candidate.content.parts:
                     # Sometimes Thinking models have content but it is in a different structure or empty if thinking consumed it all? 
                     # Actually standard API should return text in parts[0]
                     log_system("Empty content parts in candidate.", "WARN")
                     # We can try to continue or break
                     break

                parts = candidate.content.parts
                
                text_content = ""
                function_calls = []

                for part in parts:
                    # Check for explicit 'thought' field if available in future SDKs, 
                    # but currently it appears as text before the function call
                    if part.text: 
                        text_content += part.text
                    if part.function_call: 
                        function_calls.append(part.function_call)

                # --- VISIBILITY: Stream the Thought/Plan ---
                if text_content:
                    log_system(f"AGENT THOUGHT: {text_content[:100]}...", "THOUGHT")
                    msg_type = "llm_thought" if function_calls else "response"
                    yield json.dumps({"type": msg_type, "content": text_content}) + "\n"
                    # If no function calls, we might be done, but we force report_execution in prompt
                    if not function_calls: break

                if function_calls:
                    safe_calls = [{"name": fc.name, "args": proto_to_dict(fc.args)} for fc in function_calls]
                    yield json.dumps({"type": "tool_call_batch", "calls": safe_calls}) + "\n"

                    results_ordered = []
                    
                    # Intercept Special Calls for State Tracking
                    for i, call in enumerate(safe_calls):
                        name = call['name']
                        args = call['args']

                        # Emit Execution Status
                        yield json.dumps({"type": "status_change", "phase": "executing", "tool": name}) + "\n"
                        
                        # EXECUTE
                        _, _, res = await self._execute_with_index(i, name, args)
                        
                        # POST-EXECUTION HOOKS
                        if name == "assign_mission":
                            try:
                                # Extract ID from string like "Mission 1234 assigned..."
                                if "Mission" in str(res):
                                    current_mission_id = str(res).split("Mission ")[1].split(" ")[0]
                                    current_criteria = args.get('verification_criteria', {})
                            except: pass
                            
                        elif name == "report_execution":
                            # TRIGGER VERIFICATION
                            if current_mission_id:
                                log_system(f"Triggering Auto-Verification for {current_mission_id}...", "SYS")
                                
                                # Emit Verification Status
                                yield json.dumps({"type": "status_change", "phase": "verifying"}) + "\n"
                                yield json.dumps({"type": "llm_thought", "content": "Verifying work (Truth Layer)..."}) + "\n"
                                
                                # 1. Get Evidence (Orchestrator Logic)
                                evidence_json = verify_mission(current_mission_id)
                                
                                # 2. Judge (Verifier Logic)
                                judgment = await self._verify_outcome(
                                    claim=args.get('summary', 'Done'),
                                    evidence_json=evidence_json,
                                    criteria=json.dumps(current_criteria)
                                )
                                
                                if judgment['verified']:
                                    finalize_mission(current_mission_id, "VERIFIED")
                                    res = f"VERIFICATION PASSED: {judgment['reason']}"
                                    yield json.dumps({"type": "tool_result", "name": "VERIFIER", "content": "PASSED"}) + "\n"
                                    yield json.dumps({"type": "verification", "status": "success", "reason": judgment['reason']}) + "\n"
                                else:
                                    finalize_mission(current_mission_id, "FAILED")
                                    verification_fails += 1
                                    res = f"VERIFICATION FAILED: {judgment['reason']}. You must try a different approach."
                                    yield json.dumps({"type": "tool_result", "name": "VERIFIER", "content": f"FAILED: {judgment['reason']}"}) + "\n"
                                    yield json.dumps({"type": "verification", "status": "failed", "reason": judgment['reason']}) + "\n"
                                    
                                    # STUCK DETECTION
                                    if verification_fails >= 2:
                                        log_system("Stuck detected. Escalating...", "SYS")
                                        esc_res = escalate_to_human(current_mission_id, f"Failed verification {verification_fails} times. Last error: {judgment['reason']}")
                                        res += f" \nAUTO-ESCALATION: {esc_res}"
                                    else:
                                        # If failed but retrying, signal back to planning/executing
                                        yield json.dumps({"type": "status_change", "phase": "planning", "content": "Verification Failed. Retrying..."}) + "\n"

                        results_ordered.append(res)
                        yield json.dumps({"type": "tool_result", "name": name, "content": str(res)[:500]}) + "\n"

                    response_parts = [Part(function_response=FunctionResponse(name=function_calls[i].name, response={"result": res})) for i, res in enumerate(results_ordered)]
                    response = await self._send_chat_message_with_healing(chat, response_parts)
                else:
                    break
            
            # End Status
            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

        except Exception as e:
            log_system(f"HIVE ERROR: {e}", "ERR")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"
            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

    async def process_vision_command(self, image_bytes, user_prompt):
        model = genai.GenerativeModel(self.VISION_MODEL)
        res = await asyncio.to_thread(model.generate_content, [user_prompt, {'mime_type': 'image/png', 'data': image_bytes}])
        return res.text
