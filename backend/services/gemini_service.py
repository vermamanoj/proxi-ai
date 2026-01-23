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
from backend.services.desktop_service import DesktopService
from backend.models.api_models import PendingAction

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

    # --- Atomic Motor Skills (Tools) ---
    
    def click_at(self, x: int, y: int):
        log_system(f"TOOL_CALL: click_at({x}, {y})", "ACTION")
        if self.desktop_service: return self.desktop_service.click_at(x, y)
        return "Desktop Service Unavailable"

    def type_text(self, text: str):
        log_system(f"TOOL_CALL: type_text('{text}')", "ACTION")
        if self.desktop_service: return self.desktop_service.type_text(text)
        return "Desktop Service Unavailable"

    def press_hotkey(self, keys: list):
        log_system(f"TOOL_CALL: press_hotkey({keys})", "ACTION")
        if self.desktop_service: return self.desktop_service.press_hotkey(keys)
        return "Desktop Service Unavailable"

    def get_screen_map(self):
        log_system("TOOL_CALL: get_screen_map() - Scanning...", "VISION")
        if self.desktop_service: 
            result = self.desktop_service.get_screen_map()
            log_system(f"VISION_RESULT_LEN: {len(result)} chars", "VISION")
            return result
        return "Desktop Service Unavailable"

    def run_terminal_command(self, command: str):
        log_system(f"TOOL_CALL: run_terminal_command('{command}')", "SHELL")
        if self.desktop_service:
            result = self.desktop_service.run_terminal_command(command)
            log_system(f"SHELL_OUTPUT: {result[:100]}...", "SHELL")
            return result
        return "Desktop Service Unavailable"

    # --- Router & Execution ---

    async def route_and_execute(self, message: str, complexity_request: str = "fast"):
        log_system(f"NEW REQUEST: {message} (Mode: {complexity_request})", "ROUTER")
        
        if not self.api_key: return "Error: API Key Missing", "error", "none"

        # 1. Gather all tools
        tools = [
            get_server_time, get_system_health, 
            update_github_file, create_github_issue,
            self.click_at, self.type_text, self.press_hotkey, 
            self.get_screen_map, self.run_terminal_command
        ]

        model_name = self.FAST_TEXT_MODEL
        reasoning_path = "flash_direct"

        # 2. Decision Tree
        if complexity_request == "deep":
            model_name = self.SMART_TEXT_MODEL
            reasoning_path = "pro_escalation_user"
        else:
            if any(x in message.lower() for x in ["check", "click", "open", "type", "press"]):
                 reasoning_path = "flash_heuristic"
            else:
                 model_name = self.SMART_TEXT_MODEL
                 reasoning_path = "pro_escalation_auto"

        # 4. Execution
        try:
            log_system(f"Executing with Model: {model_name}", "EXEC")
            model = genai.GenerativeModel(model_name=model_name, tools=tools)
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            system_instruction = """
            You are Proxi, a Headless Operator for a remote server.
            
            CRITICAL PROTOCOL:
            1. **PREFER SHELL OVER GUI:** The server screen might be locked or black. 
               - If the user asks to "check logs", "restart service", or "list files", USE `run_terminal_command`.
               - Do NOT try to open the Event Viewer or Task Manager GUI unless explicitly asked.
               - Example: Use `run_terminal_command('Get-Service *nginx*')` instead of clicking menus.
            
            2. **GUI FALLBACK (Hybrid):** 
               - Only if the task requires a visual interface (e.g., "Click the button in this specific app"), use `get_screen_map` and `click_at`.
               - Note: If `get_screen_map` returns errors or blank data, report that the session appears locked and offer to try a shell command instead.
            
            3. **TOOLS:**
               - `run_terminal_command(str)`: Execute PowerShell/CMD. **(Primary)**
               - `get_screen_map()`: See the screen. (Secondary)
               - `click_at(x,y)`, `type_text(str)`: Interact physically. (Secondary)
            """
            
            full_prompt = f"{system_instruction}\n\nUser Task: {message}"
            
            exec_start = time.time()
            response = await asyncio.to_thread(chat.send_message, full_prompt)
            duration = round(time.time() - exec_start, 2)
            
            log_system(f"Execution Complete in {duration}s", "EXEC")
            
            return response.text, model_name, reasoning_path

        except Exception as e:
            log_system(f"Execution Failed: {str(e)}", "ERROR")
            return f"Execution Error: {str(e)}", model_name, "error"

    async def process_vision_command(self, image_bytes: bytes, user_prompt: str) -> str:
        if not self.api_key: return "System Error: API Key missing."
        model = genai.GenerativeModel(self.VISION_MODEL)
        response = await asyncio.to_thread(
            model.generate_content,
            contents=[user_prompt, {'mime_type': 'image/png', 'data': image_bytes}]
        )
        return response.text
    
    def execute_pending_action(self):
        return "Atomic Mode Active."
