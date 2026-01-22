import os
import datetime
import asyncio
import psutil
from github import Github
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Tool Definitions (Real Action Tools) ---

def get_server_time():
    """Returns the current server time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_system_health():
    """
    Retrieves real-time system metrics (CPU, RAM, Disk) from the hosting server.
    Useful for SRE tasks or checking infrastructure load.
    """
    try:
        # Interval of 0.1s to get an immediate reading
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
    """
    Updates a file in a GitHub repository. If the file doesn't exist, it creates it.
    Args:
        repo_name: The full repository name (e.g., 'username/repo').
        file_path: The path to the file within the repository.
        content: The new content for the file.
        commit_message: The commit message for the update.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN environment variable is missing."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        try:
            # Try to get the file to update it
            file_content = repo.get_contents(file_path)
            repo.update_file(file_path, commit_message, content, file_content.sha)
            return f"Successfully updated '{file_path}' in '{repo_name}'."
        except Exception:
            # File likely doesn't exist, create it
            repo.create_file(file_path, commit_message, content)
            return f"Successfully created new file '{file_path}' in '{repo_name}'."
            
    except Exception as e:
        return f"GitHub Action Failed: {str(e)}"

def create_github_issue(repo_name: str, title: str, body: str):
    """
    Creates a new issue in a GitHub repository.
    Args:
        repo_name: The full repository name (e.g., 'username/repo').
        title: The title of the issue.
        body: The detailed description of the issue.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN environment variable is missing."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        return f"Issue created successfully. URL: {issue.html_url}"
    except Exception as e:
        return f"GitHub Action Failed: {str(e)}"

def run_diagnostic(service_name: str):
    """Runs a simulated diagnostic check on a specific service (Mock)."""
    if service_name.lower() == "database":
        return "Database latency: 12ms. Connection pool: 80%."
    elif service_name.lower() == "api":
        return "API Uptime: 99.9%. Error rate: 0.01%."
    else:
        return f"Service {service_name} is running normally."

class GeminiService:
    """
    Service layer for interacting with Google AI Studio (Gemini) using Tiered Compute.
    """
    
    # Tiered Model Constants
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
        
        # Register Tools - Mixing Real SRE/GitHub tools with some essential mocks
        self.tools = [
            get_server_time, 
            get_system_health, 
            update_github_file, 
            create_github_issue,
            run_diagnostic
        ]

    async def generate_audio_response(self, audio_stream: bytes) -> str:
        """
        Processes audio input using the Native Audio model.
        Currently mocked for REST API context, as real-time audio uses WebRTC on client.
        """
        return "Audio processed (Mock)"

    async def generate_reflex_response(self, prompt: str) -> str:
        """
        Fast, deterministic response for simple queries and tool routing.
        Uses Gemini 3 Flash.
        """
        try:
            model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
            # Low temperature for deterministic, quick answers
            config = GenerationConfig(temperature=0.3)
            
            response = await asyncio.to_thread(
                model.generate_content, 
                prompt, 
                generation_config=config
            )
            return response.text
        except Exception as e:
            print(f"Reflex Error: {e}")
            return f"Error (Reflex): {str(e)}"

    async def generate_deep_thought(self, prompt: str) -> str:
        """
        Complex reasoning, coding, and architecture tasks.
        Uses Gemini 3 Pro with Tools and Automatic Function Calling.
        """
        try:
            # Initialize model with tools
            model = genai.GenerativeModel(model_name=self.SMART_TEXT_MODEL, tools=self.tools)
            
            # Enable automatic function calling
            chat = model.start_chat(enable_automatic_function_calling=True)
            config = GenerationConfig(temperature=0.7)
            
            response = await asyncio.to_thread(
                chat.send_message,
                prompt,
                generation_config=config
            )
            
            return response.text
        except Exception as e:
            print(f"Deep Thought Error: {e}")
            return f"Error (Deep Thought): {str(e)}"

    async def process_vision_command(self, image_bytes: bytes, user_prompt: str) -> str:
        """
        Analyzes an image using the Vision Model (Gemini 3 Pro Image).
        Acts as the 'Architect' analyzing diagrams or code screenshots.
        """
        try:
            model = genai.GenerativeModel(self.VISION_MODEL)
            
            # The SDK handles the image object wrapping automatically if dictionary provided
            # Gemini 3 Pro Image supports text + image prompts
            response = await asyncio.to_thread(
                model.generate_content,
                contents=[
                    user_prompt,
                    {'mime_type': 'image/png', 'data': image_bytes}
                ]
            )
            return response.text
        except Exception as e:
            print(f"Vision Error: {e}")
            return f"Error (Vision): {str(e)}"
