import os
import datetime
import asyncio
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Tool Definitions ---
def get_server_time():
    """Returns the current server time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_diagnostic(service_name: str):
    """Runs a diagnostic check on a specific service."""
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
    AUDIO_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025" # The Interface
    FAST_TEXT_MODEL = "gemini-3-flash-preview"                  # The Reflex
    SMART_TEXT_MODEL = "gemini-3-pro-preview"                   # The Brain
    VISION_MODEL = "gemini-3-pro-image-preview"                 # The Eyes

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set in environment variables.")
        else:
            genai.configure(api_key=self.api_key)
        
        # Register Tools
        self.tools = [get_server_time, run_diagnostic]

    async def generate_audio_response(self, audio_stream: bytes) -> str:
        """
        Processes audio input using the Native Audio model.
        Currently mocked for REST API context, as real-time audio uses WebRTC on client.
        """
        # In a full backend streaming implementation, this would handle the WebSocket/Bidi stream.
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
            
            # Run blocking call in a separate thread
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
            
            # Start a chat session with automatic function calling enabled.
            # This allows the model to decide to call a tool, execute it, and use the result
            # to generate the final response without manual loops.
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            # Higher temperature for creativity and reasoning
            config = GenerationConfig(temperature=0.7)
            
            # Use asyncio.to_thread with the synchronous send_message method.
            # This avoids "object can't be used in await expression" errors with the SDK's async implementation
            # and prevents blocking the FastAPI event loop during the potentially long function calling loop.
            response = await asyncio.to_thread(
                chat.send_message,
                prompt,
                generation_config=config
            )
            
            return response.text
        except Exception as e:
            print(f"Deep Thought Error: {e}")
            return f"Error (Deep Thought): {str(e)}"

    async def analyze_image(self, image_bytes: bytes, prompt: str = "Describe this image") -> str:
        """
        Analyzes an image using the Vision Model (Gemini 3 Pro Image).
        """
        try:
            model = genai.GenerativeModel(self.VISION_MODEL)
            # The SDK handles the image object wrapping automatically if dictionary provided
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, {'mime_type': 'image/png', 'data': image_bytes}]
            )
            return response.text
        except Exception as e:
            print(f"Vision Error: {e}")
            return f"Error (Vision): {str(e)}"