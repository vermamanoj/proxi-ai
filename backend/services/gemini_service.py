import os
import datetime
import asyncio
import psutil
import json
import warnings
import time
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

# 2. Force Load .env from Project Root with Robust Parsing
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"

print(f"Loading environment variables from: {env_path}")

# Robust loading strategy for Windows (handling UTF-16/BOM from PowerShell)
if env_path.exists():
    # Try standard load
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Fallback: Manual parse if key is missing (fixes encoding issues)
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ Standard .env load failed. Attempting manual parsing...")
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
                                    print(f"✅ Successfully loaded key using encoding: {enc}")
                                    found = True
                                    break
                if found: break
            except Exception:
                continue
        
        if not found:
             print("❌ Manual parsing also failed. Please check .env file content.")
else:
    print(f"❌ .env file NOT found at: {env_path}")

# --- Standard Tools ---

def get_server_time():
    """Returns the current server time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    """Returns basic system stats."""
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
    """Updates a file in GitHub."""
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
    """Creates a GitHub issue."""
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
            print(f"✅ GEMINI_API_KEY loaded successfully. ({masked_key})")
            genai.configure(api_key=self.api_key)
        else:
            print("❌ CRITICAL ERROR: GEMINI_API_KEY still missing after all attempts.")
        
        try:
            self.desktop_service = DesktopService()
        except Exception as e:
            print(f"Desktop Service Failed: {e}")
            self.desktop_service = None

        self.latest_pending_action = None

    # --- Atomic Motor Skills (Tools) ---
    # We add print statements here to debug tool execution flow
    
    def click_at(self, x: int, y: int):
        """Moves mouse to (x,y) and clicks."""
        print(f"[DEBUG] Tool Call: click_at({x}, {y})")
        if self.desktop_service: return self.desktop_service.click_at(x, y)
        return "Desktop Service Unavailable"

    def type_text(self, text: str):
        """Types the specified text string."""
        print(f"[DEBUG] Tool Call: type_text('{text}')")
        if self.desktop_service: return self.desktop_service.type_text(text)
        return "Desktop Service Unavailable"

    def press_hotkey(self, keys: list):
        """Presses a key combination (e.g. ['ctrl', 's'])."""
        print(f"[DEBUG] Tool Call: press_hotkey({keys})")
        if self.desktop_service: return self.desktop_service.press_hotkey(keys)
        return "Desktop Service Unavailable"

    def get_screen_map(self):
        """Returns a list of visible text elements and their (x,y) coordinates."""
        print(f"[DEBUG] Tool Call: get_screen_map() - Capturing screen...")
        if self.desktop_service: return self.desktop_service.get_screen_map()
        return "Desktop Service Unavailable"

    # --- Router & Execution ---

    async def route_and_execute(self, message: str, complexity_request: str = "fast"):
        """
        Main entry point. Routes request to Flash or Pro based on complexity.
        """
        print(f"\n--- NEW REQUEST: {message} (Mode: {complexity_request}) ---")
        if not self.api_key: return "Error: API Key Missing (Check Server Logs)", "error", "none"

        # 1. Gather all tools (Atomic + Cloud)
        tools = [
            get_server_time, get_system_health, 
            update_github_file, create_github_issue,
            self.click_at, self.type_text, self.press_hotkey, self.get_screen_map
        ]

        model_name = self.FAST_TEXT_MODEL
        reasoning_path = "flash_direct"

        # 2. Decision Tree
        if complexity_request == "deep":
            print("[DEBUG] User explicitly requested DEEP mode.")
            model_name = self.SMART_TEXT_MODEL
            reasoning_path = "pro_escalation_user"
        else:
            # 3. Router (Flash Triage)
            print("[DEBUG] Triaging with Flash...")
            triage_prompt = f"""
            Classify this task. 
            Task: "{message}"
            
            Respond only with 'SIMPLE' or 'COMPLEX'.
            SIMPLE: UI navigation, clicking things, typing text, explaining concepts, answering questions.
            COMPLEX: Writing new code from scratch, complex debugging, architectural planning, creative writing.
            """
            try:
                triage_start = time.time()
                triage_model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
                triage_res = await asyncio.to_thread(triage_model.generate_content, triage_prompt)
                classification = triage_res.text.strip().upper()
                print(f"[DEBUG] Triage Result: {classification} (Time: {round(time.time() - triage_start, 2)}s)")
                
                if "COMPLEX" in classification:
                    model_name = self.SMART_TEXT_MODEL
                    reasoning_path = "pro_escalation_auto"
                    print("[DEBUG] Escalating to Gemini Pro.")
                else:
                    reasoning_path = "flash_direct"
                    print("[DEBUG] Staying on Gemini Flash.")
            except Exception as e:
                print(f"[DEBUG] Triage Failed ({e}). Defaulting to Flash.")
                reasoning_path = "flash_fallback"

        # 4. Execution
        try:
            print(f"[DEBUG] Executing with Model: {model_name}")
            model = genai.GenerativeModel(model_name=model_name, tools=tools)
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            system_instruction = """
            You are a Hand-Eye Coordinator and DevOps Operator.
            
            DESKTOP GUIDELINES:
            - You have Atomic Motor Skills: `click_at`, `type_text`, `press_hotkey`, `get_screen_map`.
            - IMPORTANT: You cannot read files directly from the filesystem. You are a Ghost Operator.
            - To check a file: 
              1. Call `get_screen_map` to find the icon. 
              2. `click_at` (twice) to open it. 
              3. `get_screen_map` again to read the content visible on screen.
            - Do NOT hallucinate a 'read_file' or 'open_file' tool.
            
            GENERAL GUIDELINES:
            - Execute tasks autonomously.
            - If you need to click, find the coordinates first using `get_screen_map`.
            """
            
            full_prompt = f"{system_instruction}\n\nUser Task: {message}"
            
            exec_start = time.time()
            response = await asyncio.to_thread(chat.send_message, full_prompt)
            print(f"[DEBUG] Execution Complete (Time: {round(time.time() - exec_start, 2)}s)")
            
            return response.text, model_name, reasoning_path

        except Exception as e:
            print(f"[ERROR] Execution Failed: {str(e)}")
            # Sometimes response.parts contains the tool call that failed
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
        return "Atomic Mode Active: Pending actions are executed autonomously."

