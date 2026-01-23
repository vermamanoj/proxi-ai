import os
import datetime
import asyncio
import psutil
import json
import warnings
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
                            # Handle formats: KEY=VALUE, KEY="VALUE", KEY='VALUE'
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
    # These wrapper methods are necessary to bind the DesktopService instance to the tool call
    
    def click_at(self, x: int, y: int):
        """Moves mouse to (x,y) and clicks."""
        if self.desktop_service: return self.desktop_service.click_at(x, y)
        return "Desktop Service Unavailable"

    def type_text(self, text: str):
        """Types the specified text string."""
        if self.desktop_service: return self.desktop_service.type_text(text)
        return "Desktop Service Unavailable"

    def press_hotkey(self, keys: list):
        """Presses a key combination (e.g. ['ctrl', 's'])."""
        if self.desktop_service: return self.desktop_service.press_hotkey(keys)
        return "Desktop Service Unavailable"

    def get_screen_map(self):
        """Returns a list of visible text elements and their (x,y) coordinates."""
        if self.desktop_service: return self.desktop_service.get_screen_map()
        return "Desktop Service Unavailable"

    # --- Router & Execution ---

    async def route_and_execute(self, message: str, complexity_request: str = "fast"):
        """
        Main entry point. Routes request to Flash or Pro based on complexity.
        """
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
            model_name = self.SMART_TEXT_MODEL
            reasoning_path = "pro_escalation_user"
        else:
            # 3. Router (Flash Triage)
            triage_prompt = f"""
            Classify this task. 
            Task: "{message}"
            
            Respond only with 'SIMPLE' or 'COMPLEX'.
            SIMPLE: UI navigation, clicking things, typing text, querying simple stats.
            COMPLEX: Code architecture, debugging, multi-step reasoning, explaining concepts.
            """
            try:
                triage_model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
                triage_res = await asyncio.to_thread(triage_model.generate_content, triage_prompt)
                classification = triage_res.text.strip().upper()
                
                if "COMPLEX" in classification:
                    model_name = self.SMART_TEXT_MODEL
                    reasoning_path = "pro_escalation_auto"
                else:
                    reasoning_path = "flash_direct"
            except Exception:
                # Fallback to Flash
                reasoning_path = "flash_fallback"

        # 4. Execution
        try:
            model = genai.GenerativeModel(model_name=model_name, tools=tools)
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            system_instruction = """
            You are a Hand-Eye Coordinator and DevOps Operator.
            
            DESKTOP GUIDELINES:
            - You do NOT have high-level tools like 'save_file' or 'open_app'.
            - You have Atomic Motor Skills: `click_at`, `type_text`, `press_hotkey`, `get_screen_map`.
            - To perform a desktop task:
              1. Call `get_screen_map` to see the screen layout and coordinates.
              2. Analyze the coordinates of the target text.
              3. Chain `click_at` and `type_text` to navigate step-by-step.
              4. If you need to save, find 'File' -> Click it -> Find 'Save' -> Click it.
            
            GENERAL GUIDELINES:
            - Execute tasks autonomously. Do not ask for permission for every click.
            - If a tool fails, retry or explain why.
            """
            
            full_prompt = f"{system_instruction}\n\nUser Task: {message}"
            
            response = await asyncio.to_thread(chat.send_message, full_prompt)
            return response.text, model_name, reasoning_path

        except Exception as e:
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
        # Deprecated in Atomic Mode
        return "Atomic Mode Active: Pending actions are executed autonomously."
