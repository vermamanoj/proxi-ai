import os
import datetime
import asyncio
import psutil
import json
from github import Github
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv
from backend.services.desktop_service import DesktopService
from backend.models.api_models import PendingAction

# Load environment variables from .env file
load_dotenv()

# --- Tool Definitions ---

def get_server_time():
    """Returns the current server time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    """
    Retrieves real-time system metrics (CPU, RAM, Disk) from the hosting server.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "online",
            "cpu_usage_percent": cpu_percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_used_percent": memory.percent,
            "disk_usage_percent": disk.percent
        }
    except Exception as e:
        return f"Error reading system stats: {str(e)}"

def update_github_file(repo_name: str, file_path: str, content: str, commit_message: str = "Update via Proxi"):
    """Updates or creates a file in a GitHub repository."""
    token = os.getenv("GITHUB_TOKEN")
    if not token: return "Error: GITHUB_TOKEN environment variable is missing."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            file_content = repo.get_contents(file_path)
            repo.update_file(file_path, commit_message, content, file_content.sha)
            return f"Successfully updated '{file_path}' in '{repo_name}'."
        except Exception:
            repo.create_file(file_path, commit_message, content)
            return f"Successfully created new file '{file_path}' in '{repo_name}'."
    except Exception as e:
        return f"GitHub Action Failed: {str(e)}"

def create_github_issue(repo_name: str, title: str, body: str):
    """Creates a new issue in a GitHub repository."""
    token = os.getenv("GITHUB_TOKEN")
    if not token: return "Error: GITHUB_TOKEN environment variable is missing."
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        return f"Issue created successfully. URL: {issue.html_url}"
    except Exception as e:
        return f"GitHub Action Failed: {str(e)}"

def run_diagnostic(service_name: str):
    """Runs a simulated diagnostic check on a specific service."""
    if service_name.lower() == "database":
        return "Database latency: 12ms. Connection pool: 80%."
    elif service_name.lower() == "api":
        return "API Uptime: 99.9%. Error rate: 0.01%."
    else:
        return f"Service {service_name} is running normally."

class GeminiService:
    """
    Service layer for interacting with Google AI Studio (Gemini).
    """
    
    AUDIO_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025" 
    FAST_TEXT_MODEL = "gemini-3-flash-preview"                  
    SMART_TEXT_MODEL = "gemini-3-pro-preview"                   
    VISION_MODEL = "gemini-3-pro-image-preview"                 

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set in environment variables.")
        else:
            genai.configure(api_key=self.api_key)
        
        # Initialize Desktop Service
        try:
            self.desktop_service = DesktopService()
        except Exception as e:
            print(f"Failed to init DesktopService (Headless mode?): {e}")
            self.desktop_service = None

        # State to hold the latest pending action for HITL
        self.latest_pending_action = None

    # --- Tool Wrapper for HITL ---
    def operate_desktop(self, task_description: str):
        """
        Uses computer vision to find UI elements and propose an action.
        This tool DOES NOT execute the action. It returns a proposal for User Approval.
        """
        if not self.desktop_service:
            return "Desktop service unavailable."

        print(f"Ghost Operator: Analyzing screen for task '{task_description}'...")
        
        # 1. Get UI Manifest
        elements = self.desktop_service.get_ui_manifest()
        screen_size = self.desktop_service.get_screen_size()
        
        # 2. Ask Gemini (Internal Thought) to map Task -> Coordinates
        # We use a separate model call here to reason about the UI
        prompt = f"""
        You are a UI Automation Agent.
        Screen Size: {screen_size}
        Task: {task_description}
        
        Visible UI Elements (Text & Coordinates):
        {json.dumps(elements[:50])} 
        (List truncated to top 50 elements for context)

        Determine the best single action (click, type, or hotkey).
        Return ONLY valid JSON. Format:
        {{ "action": "click", "x": 123, "y": 456, "reason": "Clicked File menu" }}
        OR
        {{ "action": "type", "text": "hello", "reason": "Typed into text box" }}
        """

        try:
            model = genai.GenerativeModel("gemini-3-flash-preview")
            result = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            plan = json.loads(result.text)
            
            # 3. Store the pending action
            self.latest_pending_action = PendingAction(
                type=plan.get("action"),
                description=f"Desktop Action: {plan.get('reason', task_description)}",
                data=plan
            )
            
            return f"ACTION_PROPOSED: {plan.get('reason')}. Waiting for user confirmation."
        except Exception as e:
            print(f"Planning failed: {e}")
            return f"Failed to plan desktop action: {e}"

    async def generate_reflex_response(self, prompt: str) -> str:
        model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text

    async def generate_deep_thought(self, prompt: str) -> str:
        """
        Executes with tools. Checks for desktop actions.
        """
        self.latest_pending_action = None # Reset state

        # Register tools including the bound method for desktop
        tools = [
            get_server_time, 
            get_system_health, 
            update_github_file, 
            create_github_issue,
            run_diagnostic,
            self.operate_desktop
        ]

        try:
            model = genai.GenerativeModel(model_name=self.SMART_TEXT_MODEL, tools=tools)
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            # System instruction update for desktop awareness
            sys_prompt = "You have access to the user's desktop via 'operate_desktop'. If the user asks to click/type something, use it. The tool will pause for confirmation."
            
            # We append the user prompt to the system context implicitly or explicitly
            full_prompt = f"{sys_prompt}\nUser: {prompt}"

            response = await asyncio.to_thread(
                chat.send_message,
                full_prompt
            )
            
            return response.text
        except Exception as e:
            print(f"Deep Thought Error: {e}")
            return f"Error (Deep Thought): {str(e)}"

    async def process_vision_command(self, image_bytes: bytes, user_prompt: str) -> str:
        model = genai.GenerativeModel(self.VISION_MODEL)
        response = await asyncio.to_thread(
            model.generate_content,
            contents=[user_prompt, {'mime_type': 'image/png', 'data': image_bytes}]
        )
        return response.text
        
    def execute_pending_action(self):
        """Called by the confirmation endpoint."""
        if self.latest_pending_action and self.desktop_service:
            action = self.latest_pending_action
            result = self.desktop_service.execute_action(action.type, action.data)
            self.latest_pending_action = None
            return result
        return "No pending action or desktop service unavailable."
