import os
import datetime
import asyncio
import psutil
import json
import warnings
import time
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Suppress Google SDK Deprecation Warning
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from github import Github
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.ai.generativelanguage import FunctionResponse, Part
from backend.services.desktop_service import DesktopService
from backend.models.api_models import PendingAction, TraceStep

# 2. Force Load .env from Project Root
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"
DEBUG_LOG_PATH = root_dir / "proxi_debug.log"

# --- Logging Helper ---
def log_system(message: str, category: str = "INFO"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{category}] {message}"
    print(formatted_msg, flush=True)
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}", flush=True)

log_system(f"Loading environment variables from: {env_path}", "INIT")

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    if not os.getenv("GEMINI_API_KEY"):
        log_system("Standard .env load failed. Attempting manual parsing...", "WARN")
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1']
        found = False
        for enc in encodings:
            try:
                with open(env_path, 'r', encoding=enc) as f:
                    for line in f:
                        if line.strip().startswith('GEMINI_API_KEY'):
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                clean_key = parts[1].strip().strip('"').strip("'")
                                if clean_key:
                                    os.environ['GEMINI_API_KEY'] = clean_key
                                    log_system(f"Successfully loaded key using encoding: {enc}", "SUCCESS")
                                    found = True
                                    break
                if found: break
            except Exception:
                continue
else:
    log_system(f".env file NOT found at: {env_path}", "ERROR")

# --- Helper for Protobuf Conversion ---
def proto_to_dict(obj):
    """
    Recursively converts Google Protobuf MapComposite/RepeatedComposite 
    objects to native Python dicts and lists for JSON serialization.
    """
    if hasattr(obj, 'items'): # MapComposite or dict
        return {k: proto_to_dict(v) for k, v in obj.items()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)): # RepeatedComposite or list
        return [proto_to_dict(v) for v in obj]
    return obj # Scalar

# --- Standard Tools ---

def get_server_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        return {
            "status": "online",
            "cpu": cpu_percent,
            "ram_gb": round(memory.total / (1024**3), 2)
        }
    except Exception as e:
        return f"Error: {str(e)}"

def update_github_file(repo_name: str, file_path: str, content: str):
    token = os.getenv("GITHUB_TOKEN")
    if not token: return "Error: GITHUB_TOKEN missing."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            file_content = repo.get_contents(file_path)
            repo.update_file(file_path, "Update via Proxi", content, file_content.sha)
            return f"Updated {file_path}"
        except Exception:
            repo.create_file(file_path, "Create via Proxi", content)
            return f"Created {file_path}"
    except Exception as e:
        return f"GitHub Error: {e}"

def create_github_issue(repo_name: str, title: str, body: str):
    token = os.getenv("GITHUB_TOKEN")
    if not token: return "Error: GITHUB_TOKEN missing."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        return f"Issue Created: {issue.html_url}"
    except Exception as e:
        return f"GitHub Error: {e}"

class GeminiService:
    
    AUDIO_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025" 
    FAST_TEXT_MODEL = "gemini-3-flash-preview"                  
    SMART_TEXT_MODEL = "gemini-3-pro-preview"                   
    VISION_MODEL = "gemini-3-pro-image-preview"                 

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
            log_system(f"GEMINI_API_KEY loaded. ({masked_key})", "INIT")
            genai.configure(api_key=self.api_key)
        else:
            log_system("CRITICAL ERROR: GEMINI_API_KEY missing.", "ERROR")
        
        try:
            self.desktop_service = DesktopService()
        except Exception as e:
            log_system(f"Desktop Service Failed: {e}", "ERROR")
            self.desktop_service = None

        self.latest_pending_action = None
        
        # Tools Mapping for Execution
        self.tools_map = {
            "get_server_time": get_server_time,
            "get_system_health": get_system_health,
            "update_github_file": update_github_file,
            "create_github_issue": create_github_issue,
            "click_at": self.click_at,
            "drag_mouse": self.drag_mouse,
            "type_text": self.type_text,
            "press_hotkey": self.press_hotkey,
            "look_at_screen": self.look_at_screen,
            "scan_ui_tree": self.scan_ui_tree,
            "wait_seconds": self.wait_seconds,
            "run_terminal_command": self.run_terminal_command
        }

    # --- Atomic Motor Skills (Tools) ---
    
    def click_at(self, x: int, y: int):
        log_system(f"TOOL_CALL: click_at({x}, {y})", "ACTION")
        if self.desktop_service: return self.desktop_service.click_at(x, y)
        return "Desktop Service Unavailable"

    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        log_system(f"TOOL_CALL: drag_mouse({start_x},{start_y} -> {end_x},{end_y})", "ACTION")
        if self.desktop_service: return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
        return "Desktop Service Unavailable"

    def type_text(self, text: str):
        log_system(f"TOOL_CALL: type_text('{text}')", "ACTION")
        if self.desktop_service: return self.desktop_service.type_text(text)
        return "Desktop Service Unavailable"

    def press_hotkey(self, keys: list):
        log_system(f"TOOL_CALL: press_hotkey({keys})", "ACTION")
        if self.desktop_service: return self.desktop_service.press_hotkey(keys)
        return "Desktop Service Unavailable"
    
    def wait_seconds(self, seconds: int):
        log_system(f"TOOL_CALL: wait_seconds({seconds})", "ACTION")
        time.sleep(seconds)
        return f"Waited {seconds} seconds."

    def look_at_screen(self, purpose: str):
        """Dedicated Vision Tool - Explicitly requests a visual check"""
        log_system(f"TOOL_CALL: look_at_screen(purpose='{purpose}')", "VISION")
        if not self.desktop_service: return "Desktop Service Unavailable"
        
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img:
            return "Error: Failed to capture screen."
            

        try:
            log_system("Sending Screenshot to Gemini 3 Flash...", "VISION")
            model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
            response = model.generate_content([
                f"Task: {purpose}\nAnalyze the screenshot. Be concise. Describe UI elements, coordinates, and active windows.",
                {'mime_type': 'image/jpeg', 'data': base64_img}
            ])
            log_system(f"Vision Verdict: {response.text[:100]}...", "VISION")
            return f"VISION_RESULT: {response.text}"
        except Exception as e:
            return f"Vision Analysis Failed: {e}"

    def scan_ui_tree(self):
        """Dedicated Structure Tool - Fast, no image analysis"""
        log_system(f"TOOL_CALL: scan_ui_tree()", "VISION")
        if self.desktop_service:
            # Replaces the old 'get_screen_map(mode="hybrid")'
            result = self.desktop_service.scan_ui_tree()
            return result
        return "Desktop Service Unavailable"

    def run_terminal_command(self, command: str):
        log_system(f"TOOL_CALL: run_terminal_command('{command}')", "SHELL")
        if self.desktop_service:
            result = self.desktop_service.run_terminal_command(command)
            return result
        return "Desktop Service Unavailable"

    # --- Helper to Execute Tool (Parallel Ready) ---
    async def _execute_tool_wrapper(self, name: str, args: dict):
        func = self.tools_map.get(name)
        if not func:
            return f"Error: Tool '{name}' not found."
        
        try:
            # Most tools are synchronous, run them in thread pool to not block loop
            if asyncio.iscoroutinefunction(func):
                return await func(**args)
            else:
                return await asyncio.to_thread(func, **args)
        except Exception as e:
            return f"Tool Execution Error: {str(e)}"
    
    # Wrapper to track index for preserving order in API response
    async def _execute_with_index(self, index: int, name: str, args: dict):
        res = await self._execute_tool_wrapper(name, args)
        return (index, name, res)

    async def _send_chat_message_with_healing(self, chat, content, retries=1):
        """
        Robust wrapper for chat.send_message.
        If MALFORMED_FUNCTION_CALL occurs, it attempts to 'heal' the conversation
        by sending a correction prompt to the model instead of just retrying the same request.
        """
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(chat.send_message, content)
            except Exception as e:
                error_str = str(e)
                
                # Check for Malformed Function Call error
                if "MALFORMED_FUNCTION_CALL" in error_str:
                    log_system(f"Gemini API Error: MALFORMED_FUNCTION_CALL (Attempt {attempt+1}/{retries+1}).", "WARN")
                    
                    if attempt < retries:
                        # HEALING STRATEGY:
                        # Instead of retrying the exact same request, we catch the error 
                        # and ask the model to fix its output.
                        # Since we can't easily 'inject' a user message in the middle of a failed turn in this SDK wrapper easily,
                        # We will try a simple retry first, but with a slight delay.
                        # A true "Healing" would require manually appending the error to history, 
                        # but genai SDK manages history statefully.
                        
                        log_system("Retrying request...", "WARN")
                        await asyncio.sleep(1) # Backoff
                        continue
                    else:
                        # Final Attempt Failed
                        log_system("All retries failed.", "ERROR")
                        raise e
                else:
                    raise e

    # --- Router & Execution (Streaming Generator) ---

    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast"):
        log_system(f"NEW REQUEST: {message} (Mode: {complexity_request})", "ROUTER")
        
        if not self.api_key: 
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        # 1. Setup Tools (Declarations)
        tools = list(self.tools_map.values())

        model_name = self.FAST_TEXT_MODEL if complexity_request == "fast" else self.SMART_TEXT_MODEL
        
        # 2. System Prompt
        system_instruction = """
        You are Proxi, a Headless Operator.
        Interact via voice and tools.
        
        CRITICAL OPERATIONAL RULES:
        1. **NO AMBIGUITY**:
           - Use `look_at_screen(purpose="...")` to SEE the screen (Verification, Reading text).
           - Use `scan_ui_tree()` to get internal accessibility data (Finding Buttons/Window Names).
           - DO NOT guess arguments. 
        2. **WAIT FOR UI**:
           - When opening apps or loading webpages, ALWAYS use `wait_seconds(3)` before trying to click or type.
        3. **VERIFY ACTIONS**:
           - After drawing or navigating, call `look_at_screen("Did the action succeed?")`.
           - If it failed, try again with different coordinates or methods.
        4. **POWERSHELL**:
           - Use `;` separator. 
           - Example: `start chrome https://draw.io`
        5. **DRAWING**: 
           - `start mspaint` -> `wait_seconds(2)` -> `drag_mouse`.
        """
        
        full_prompt = f"{system_instruction}\n\nUser Task: {message}"

        # 3. Start Chat (Manual Loop for Parallel Execution)
        try:
            model = genai.GenerativeModel(model_name=model_name, tools=tools)
            chat = model.start_chat(enable_automatic_function_calling=False) # We handle it manually!

            # Notify UI of start
            yield json.dumps({
                "type": "meta", 
                "model": model_name, 
                "step": "user_input", 
                "content": message
            }) + "\n"

            # Initial Message with Retry
            response = await self._send_chat_message_with_healing(chat, full_prompt)
            
            # Loop for multi-turn tool use
            max_turns = 15
            current_turn = 0

            while current_turn < max_turns:
                current_turn += 1
                
                # Check parts
                # Gemini response structure: candidates[0].content.parts
                parts = response.candidates[0].content.parts
                
                # Extract Text Thoughts & Function Calls
                text_content = ""
                function_calls = []

                for part in parts:
                    if part.text:
                        text_content += part.text
                    if part.function_call:
                        function_calls.append(part.function_call)

                # Streaming Thought to UI
                if text_content:
                    log_system(f"LLM THOUGHT: {text_content[:100]}...", "THOUGHT")
                    msg_type = "llm_thought" if function_calls else "response"
                    yield json.dumps({"type": msg_type, "content": text_content}) + "\n"
                    
                    if not function_calls:
                        # Done!
                        break
                elif function_calls:
                     # FALLBACK thought
                     tool_names = [fc.name for fc in function_calls]
                     fallback = f"Executing actions: {', '.join(tool_names)}..."
                     log_system(f"LLM SILENT - GENERATING FALLBACK THOUGHT: {fallback}", "WARN")
                     yield json.dumps({"type": "llm_thought", "content": fallback}) + "\n"

                # Handle Parallel Function Calls
                if function_calls:
                    # Convert Protobuf Args to Dict safe for JSON
                    safe_calls = []
                    for fc in function_calls:
                         safe_calls.append({
                             "name": fc.name,
                             "args": proto_to_dict(fc.args) # Recursive fix for RepeatedComposite
                         })

                    # Notify UI of upcoming tools
                    yield json.dumps({
                        "type": "tool_call_batch", 
                        "calls": safe_calls
                    }) + "\n"

                    # Create Tasks (Wrapped to return index)
                    tasks = []
                    for i, call_info in enumerate(safe_calls):
                        tasks.append(
                            self._execute_with_index(i, call_info['name'], call_info['args'])
                        )
                    
                    log_system(f"Executing {len(tasks)} tools in PARALLEL (Streaming)...", "EXEC")
                    
                    # Store results in ordered list for API consistency
                    results_ordered = [None] * len(safe_calls)
                    
                    # Yield results AS THEY COMPLETE to update UI immediately
                    for completed_task in asyncio.as_completed(tasks):
                        idx, name, res = await completed_task
                        results_ordered[idx] = res
                        
                        yield json.dumps({
                            "type": "tool_result", 
                            "name": name, 
                            "content": str(res)[:500]
                        }) + "\n"

                    # Construct Response Parts for Gemini
                    response_parts = []
                    for i, res in enumerate(results_ordered):
                        response_parts.append(
                            Part(function_response=FunctionResponse(
                                name=function_calls[i].name, 
                                response={"result": res}
                            ))
                        )
                    
                    # Send results back to model with healing
                    response = await self._send_chat_message_with_healing(chat, response_parts)
                else:
                    break

        except Exception as e:
            log_system(f"Execution Error: {e}", "ERROR")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    async def process_vision_command(self, image_bytes: bytes, user_prompt: str) -> str:
        # Standard non-stream for simple vision
        if not self.api_key: return "System Error: API Key missing."
        model = genai.GenerativeModel(self.VISION_MODEL)
        response = await asyncio.to_thread(
            model.generate_content,
            contents=[user_prompt, {'mime_type': 'image/png', 'data': image_bytes}],
            request_options={"timeout": 60}
        )
        return response.text