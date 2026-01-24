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
from backend.services.desktop_service import DesktopService
from backend.utils.logger import log_system
from backend.database import init_db
from backend.services.orchestrator import create_mission, add_item, update_item_status

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

        try:
            self.desktop_service = DesktopService()
        except:
            self.desktop_service = None

        # MAPPING: Combines Standard Tools + Service Wrappers
        self.tools_map = {
            # Standard
            "get_server_time": get_server_time,
            "get_system_health": get_system_health,
            "update_github_file": update_github_file,
            "create_github_issue": create_github_issue,
            "send_slack_message": send_slack_message,
            "create_linear_ticket": create_linear_ticket,
            "query_knowledge_base": query_knowledge_base,
            
            # Orchestrator (Memory)
            "create_mission": create_mission,
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
            "scroll_page": self.scroll_page
        }
        log_system(f"Gemini Service Initialized with {len(self.tools_map)} tools.", "INIT")

    # --- DESKTOP WRAPPERS ---
    def click_at(self, x: int, y: int):
        """Moves mouse to (x, y) and clicks."""
        if self.desktop_service: return self.desktop_service.click_at(x, y)
        return "Desktop Unavailable"
        
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Drags mouse from start to end coordinates."""
        if self.desktop_service: return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
        return "Desktop Unavailable"
        
    def type_text(self, text: str):
        """Types text into the active window."""
        if self.desktop_service: return self.desktop_service.type_text(text)
        return "Desktop Unavailable"
        
    def press_hotkey(self, keys: list):
        """Presses a hotkey combination (e.g. ['ctrl', 'c'])."""
        if self.desktop_service: return self.desktop_service.press_hotkey(keys)
        return "Desktop Unavailable"
        
    def wait_seconds(self, seconds: int):
        """Pauses execution."""
        time.sleep(seconds)
        return f"Waited {seconds}s"
        
    def run_terminal_command(self, command: str):
        """Executes a shell command."""
        if self.desktop_service: return self.desktop_service.run_terminal_command(command)
        return "Desktop Unavailable"
    
    def open_target(self, resource: str):
        """
        Opens a URL in the browser or a local file. 
        Use this to start researching a topic or inspecting a file.
        """
        if self.desktop_service: return self.desktop_service.open_target(resource)
        return "Desktop Unavailable"

    def read_page_content(self):
        """
        INSTANTLY reads the text content of the active window/page.
        It simulates Ctrl+A (Select All) -> Ctrl+C (Copy) and reads the clipboard.
        Use this to ingest web pages, documents, or logs efficiently.
        """
        if self.desktop_service: return self.desktop_service.read_page_content()
        return "Desktop Unavailable"

    def scroll_page(self, direction: str = 'down'):
        """Scrolls the active window 'down' or 'up'."""
        if self.desktop_service: return self.desktop_service.scroll_page(direction)
        return "Desktop Unavailable"

    def look_at_screen(self, purpose: str):
        """Takes a screenshot and analyzes it visually."""
        if not self.desktop_service: return "Desktop Unavailable"
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img: return "Screenshot failed"
        try:
            model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
            res = model.generate_content([f"Purpose: {purpose}. Describe UI.", {'mime_type': 'image/jpeg', 'data': base64_img}])
            return f"VISION: {res.text}"
        except Exception as e: return f"Vision Error: {e}"

    def scan_ui_tree(self):
        """Scans accessibility tree for clickable elements."""
        if self.desktop_service: return self.desktop_service.scan_ui_tree()
        return "Desktop Unavailable"

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
                return await asyncio.to_thread(chat.send_message, content)
            except Exception as e:
                if "MALFORMED_FUNCTION_CALL" in str(e) and attempt < retries:
                    log_system("Healing malformed call...", "WARN")
                    await asyncio.sleep(1)
                    continue
                raise e

    # --- THE HIVE ORCHESTRATOR ---
    
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast"):
        """
        HIVE Architecture: Planner -> Executor.
        """
        log_system(f"HIVE ORCHESTRATOR: {message}", "ROUTER")
        
        if not self.api_key: 
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        hive_instruction = """
        You are Proxi, an Autonomous Orchestrator Agent.
        
        **CORE MISSION:**
        You can execute long-running tasks by interacting with the computer and saving your findings to memory.

        **RESEARCH & MEMORY TOOLS:**
        1. `create_mission(goal)`: Start a new task.
        2. `open_target(url)`: Open a webpage.
        3. `read_page_content()`: INSTANTLY read the page text (via Clipboard). PREFER THIS over Vision for text.
        4. `add_item(mission_id, type, source, attributes)`: SAVE what you found.
        
        **EXAMPLE WORKFLOW (Researching Startups):**
        1. `create_mission("Find 3 AI startups")` -> returns ID "123".
        2. `open_target("google.com")` -> `type_text("AI startups SF")` -> `press_hotkey(['enter'])`.
        3. `read_page_content()` -> You see search results.
        4. `open_target("found_url.com")`
        5. `read_page_content()` -> You see "CEO: Jane Doe".
        6. `add_item("123", "LEAD", "found_url.com", {"ceo": "Jane Doe", "name": "AI Co"})`.
        
        **STANDARD OPS:**
        - Consult `query_knowledge_base` for internal docs.
        - Use `send_slack_message` to notify humans.
        """

        tools = list(self.tools_map.values())
        model = genai.GenerativeModel(model_name=self.SMART_TEXT_MODEL, tools=tools)
        chat = model.start_chat(enable_automatic_function_calling=False)

        yield json.dumps({"type": "meta", "model": "HIVE_MIND", "step": "planning", "content": message}) + "\n"

        full_prompt = f"{hive_instruction}\n\nGOAL: {message}"
        
        try:
            response = await self._send_chat_message_with_healing(chat, full_prompt)
            
            # The Executor Loop
            max_turns = 30 # Increased for research loops
            current_turn = 0
            
            while current_turn < max_turns:
                current_turn += 1
                parts = response.candidates[0].content.parts
                
                text_content = ""
                function_calls = []

                for part in parts:
                    if part.text: text_content += part.text
                    if part.function_call: function_calls.append(part.function_call)

                if text_content:
                    log_system(f"AGENT THOUGHT: {text_content[:100]}...", "THOUGHT")
                    msg_type = "llm_thought" if function_calls else "response"
                    yield json.dumps({"type": msg_type, "content": text_content}) + "\n"
                    if not function_calls: break

                if function_calls:
                    safe_calls = [{"name": fc.name, "args": proto_to_dict(fc.args)} for fc in function_calls]
                    yield json.dumps({"type": "tool_call_batch", "calls": safe_calls}) + "\n"

                    # Serial Execution for Desktop Tasks (Important for Mouse/Keyboard/Clipboard)
                    # We cannot run `click` and `type` in parallel.
                    results_ordered = []
                    for i, call in enumerate(safe_calls):
                        _, name, res = await self._execute_with_index(i, call['name'], call['args'])
                        results_ordered.append(res)
                        yield json.dumps({"type": "tool_result", "name": name, "content": str(res)[:500]}) + "\n"

                    response_parts = [Part(function_response=FunctionResponse(name=function_calls[i].name, response={"result": res})) for i, res in enumerate(results_ordered)]
                    response = await self._send_chat_message_with_healing(chat, response_parts)
                else:
                    break

        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    async def process_vision_command(self, image_bytes, user_prompt):
        model = genai.GenerativeModel(self.VISION_MODEL)
        res = await asyncio.to_thread(model.generate_content, [user_prompt, {'mime_type': 'image/png', 'data': image_bytes}])
        return res.text
