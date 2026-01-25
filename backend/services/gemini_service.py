
import os
import asyncio
import json
import warnings
import time
import base64
from pathlib import Path
from dotenv import load_dotenv

# Suppress Pydantic Warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# OLD STABLE SDK
import google.generativeai as genai
from google.generativeai import protos
from google.generativeai.types import FunctionDeclaration, Tool

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

from backend.tools.ppt_tools import (
    ppt_get_active_presentation,
    ppt_open_presentation,
    ppt_get_slide_info,
    ppt_edit_text,
    ppt_add_slide,
    ppt_duplicate_slide,
    ppt_delete_slide,
    ppt_save_presentation,
    ppt_goto_slide,
    ppt_add_picture,
    ppt_add_shape,
    ppt_move_shape,
    ppt_resize_shape,
    ppt_format_text,
    ppt_get_theme_colors,
)

# Load .env
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"
log_system(f"Loading environment variables from: {env_path}", "INIT")
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# Helper for protobuf conversion
def proto_to_dict(obj):
    if hasattr(obj, 'items'):
        return {k: proto_to_dict(v) for k, v in obj.items()}
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        return [proto_to_dict(v) for v in obj]
    return obj

class GeminiService:
    
    FAST_TEXT_MODEL = "gemini-3-flash-preview"  # Reflex mode
    SMART_TEXT_MODEL = "gemini-3-pro-preview"   # Deep reasoning mode
    VISION_MODEL = "gemini-3-flash-preview"     # Vision analysis
    IMAGE_GEN_MODEL = "gemini-3-pro-image-preview"    # Image generation

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            log_system(f"GEMINI_API_KEY loaded. ({self.api_key[:8]}...{self.api_key[-4:]})", "INIT")
        else:
            log_system("CRITICAL: GEMINI_API_KEY not found.", "ERR")
        
        try:
            init_db()
        except Exception as e:
            log_system(f"DB Init Failed: {e}", "ERR")

        self.desktop_service = get_desktop_service()
        
        # Session-based conversation history for multi-turn interactions
        self.sessions = {}  # {session_id: [{"role": "user/model", "parts": [...]}]}

        # EXECUTION MAP - Keys must match function names exactly
        self.tools_map = {
            "get_server_time": get_server_time,
            "get_system_health": self.get_system_health,
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
            "share_screenshot": self.share_screenshot,
            "scan_ui_tree": self.scan_ui_tree,
            "wait_seconds": self.wait_seconds,
            "run_terminal_command": self.run_terminal_command,
            "open_target": self.open_target,
            "read_page_content": self.read_page_content,
            "scroll_page": self.scroll_page,
            "browser_command": self.browser_command,
            # Window Management Tools
            "focus_window": self.focus_window,
            "get_window_rect": self.get_window_rect,
            "list_windows": self.list_windows,
            # PowerPoint Tools
            "ppt_get_active_presentation": ppt_get_active_presentation,
            "ppt_open_presentation": ppt_open_presentation,
            "ppt_get_slide_info": ppt_get_slide_info,
            "ppt_edit_text": ppt_edit_text,
            "ppt_add_slide": ppt_add_slide,
            "ppt_duplicate_slide": ppt_duplicate_slide,
            "ppt_delete_slide": ppt_delete_slide,
            "ppt_save_presentation": ppt_save_presentation,
            "ppt_goto_slide": ppt_goto_slide,
            "ppt_add_picture": ppt_add_picture,
            "ppt_add_shape": ppt_add_shape,
            "ppt_move_shape": ppt_move_shape,
            "ppt_resize_shape": ppt_resize_shape,
            "ppt_format_text": ppt_format_text,
            "ppt_get_theme_colors": ppt_get_theme_colors,
        }
        
        log_system(f"Gemini Service Initialized with {len(self.tools_map)} tools.", "INIT")

    # --- DESKTOP WRAPPERS (names must match tools_map keys for SDK inference) ---
    def get_system_health(self): 
        """Returns system CPU, memory, and status."""
        return self.desktop_service.get_system_health()
    
    def click_at(self, x: int, y: int): 
        """Clicks at the specified X,Y screen coordinates."""
        return self.desktop_service.click_at(x, y)
    
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int): 
        """Drags from start coordinates to end coordinates."""
        return self.desktop_service.drag_mouse(start_x, start_y, end_x, end_y)
    
    def type_text(self, text: str): 
        """Types the specified text using keyboard."""
        return self.desktop_service.type_text(text)
    
    def press_hotkey(self, keys: list[str]): 
        """Presses a keyboard hotkey combination."""
        return self.desktop_service.press_hotkey(keys)
    
    def wait_seconds(self, seconds: int): 
        """Waits for the specified number of seconds."""
        return self.desktop_service.wait_seconds(seconds)
    
    def run_terminal_command(self, command: str): 
        """Executes a shell/terminal command."""
        return self.desktop_service.run_terminal_command(command)
    
    def open_target(self, resource: str): 
        """Opens a URL or file."""
        return self.desktop_service.open_target(resource)
    
    def read_page_content(self): 
        """Reads text content from the active window/page."""
        return self.desktop_service.read_page_content()
    
    def scroll_page(self, direction: str = 'down'): 
        """Scrolls the active window up or down."""
        return self.desktop_service.scroll_page(direction)
    
    def browser_command(self, action: str, url: str = None): 
        """Controls browser via hotkeys (NEW_TAB, CLOSE_TAB, NAVIGATE, REFRESH, SEARCH)."""
        return self.desktop_service.browser_command(action, url)
    
    def scan_ui_tree(self): 
        """Scans the accessibility tree for UI elements."""
        return self.desktop_service.scan_ui_tree()

    def focus_window(self, title: str):
        """Brings a window to the foreground by title (partial match). Use before interacting with a specific app."""
        return self.desktop_service.focus_window(title)

    def get_window_rect(self, title: str):
        """Gets window position and size: {x, y, width, height}. Use to calculate safe drawing coordinates."""
        return self.desktop_service.get_window_rect(title)

    def list_windows(self):
        """Lists all visible windows with their titles and positions."""
        return self.desktop_service.list_windows()

    def look_at_screen(self, purpose: str):
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img: return "Screenshot failed"
        try:
            model = genai.GenerativeModel(self.VISION_MODEL)
            response = model.generate_content([
                f"Purpose: {purpose}. Describe the UI layout and key elements visible.",
                {'mime_type': 'image/jpeg', 'data': base64.b64decode(base64_img)}
            ])
            log_system(f"Vision analysis complete for: {purpose}", "VISION")
            return f"VISION: {response.text}"
        except Exception as e: 
            return f"Vision Error: {e}"

    def share_screenshot(self, caption: str = "Screenshot"):
        """
        Takes a screenshot and shares it with the user in the chat UI.
        Use this when the user asks to SEE or be SHOWN something on screen.
        
        Args:
            caption: A brief description of what the screenshot shows.
        
        Returns:
            Special marker that triggers screenshot display in UI.
        """
        base64_img = self.desktop_service.get_screenshot_base64()
        if not base64_img: 
            return "Screenshot failed - could not capture screen"
        log_system(f"Screenshot captured for user: {caption}", "SCREENSHOT")
        # Return special marker with base64 data - handled in streaming loop
        return f"__SCREENSHOT__:data:image/jpeg;base64,{base64_img}:__CAPTION__:{caption}"

    async def _execute_with_index(self, index: int, name: str, args: dict):
        func = self.tools_map.get(name)
        if not func: return (index, name, f"Error: Tool {name} not found")
        try:
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = await asyncio.to_thread(func, **args)
            return (index, name, res)
        except Exception as e: return (index, name, str(e))

    async def _send_with_retry(self, chat, content, retries=2):
        """Send message with retry on MALFORMED_FUNCTION_CALL errors"""
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(chat.send_message, content)
            except Exception as e:
                if "MALFORMED_FUNCTION_CALL" in str(e) and attempt < retries:
                    log_system(f"MALFORMED_FUNCTION_CALL - Retrying ({attempt+1}/{retries})", "WARN")
                    await asyncio.sleep(1)
                    continue
                raise e

    # --- MAIN ORCHESTRATOR ---
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast", session_id: str = None):
        log_system(f"NEW REQUEST: {message} (Mode: {complexity_request}, Session: {session_id})", "ROUTER")
        
        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        # Get or create session history
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            log_system(f"New session created: {session_id}", "SESSION")
        else:
            log_system(f"Continuing session: {session_id} with {len(self.sessions[session_id])} messages", "SESSION")

        if not self.api_key:
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        # Tool declarations
        tools = list(self.tools_map.values())
        log_system(f"Tools loaded: {len(tools)} functions", "ROUTER")

        # Model selection
        model_name = self.SMART_TEXT_MODEL if complexity_request == "deep" else self.FAST_TEXT_MODEL
        log_system(f"Using model: {model_name} (complexity: {complexity_request})", "ROUTER")

        # System instruction for transparency
        system_instruction = """You are Proxi, a Headless Operator with FULL OS-level access on this Windows computer.

YOU HAVE ACCESS TO THESE CAPABILITIES - USE THEM:
- run_terminal_command: Execute PowerShell commands (dir, ls, Get-Process, etc.)
- look_at_screen: Take screenshot and analyze what's visible (for YOUR analysis only)
- share_screenshot: Take screenshot and SHOW it to the user in the chat UI
- open_target: Open files, folders, URLs, or applications
- click_at, type_text, press_hotkey: Control mouse and keyboard
- ppt_* tools: Edit PowerPoint presentations
- get_system_health: Check CPU, memory, disk usage

TO LIST FILES ON DESKTOP, use: run_terminal_command with "dir $env:USERPROFILE\\Desktop" or "ls ~/Desktop"
TO OPEN AN IMAGE, use: open_target with the image path
TO SEE THE SCREEN (for your analysis), use: look_at_screen
TO SHOW THE USER A SCREENSHOT, use: share_screenshot - this displays it in the chat!

CRITICAL RULE - THINK BEFORE YOU ACT:
Before EVERY tool call, explain: WHAT you're doing, WHY, and WHAT you expect.

INCIDENT RESOLUTION FLOW:
1. DIAGNOSE: Check system health, then list processes (use `ps aux` or `top`) to identify the culprit
2. ANALYZE: Identify the specific process causing issues (name, PID, resource usage)
3. PRESENT OPTIONS: Tell the user what you found and what actions are available
4. **STOP AND ASK**: For destructive actions, END your response with a question asking for approval
5. EXECUTE: Only after user replies with approval, run the command
6. VERIFY: Check system health again to confirm resolution
7. CONFIRM: Report the final outcome to the user

CRITICAL - APPROVAL MECHANISM:
- Do NOT use send_slack_message for approvals
- Do NOT use escalate_to_human for things you can fix
- Instead, STOP your response and ask the user directly in the chat
- End your message with: "Should I proceed? Reply 'yes' to approve or 'no' to cancel."
- Then WAIT - do not call any more tools until user responds

APPROVAL REQUIRED FOR:
- Killing processes
- Restarting services  
- Deleting files
- Modifying system configuration
- Any action that could cause data loss

WHEN PRESENTING FINDINGS:
Include ALL relevant details so user can make an informed decision:
- Process name and what it does
- PID and resource usage (CPU%, memory)
- How long it has been running
- Who/what started it (owner/service)
- Impact of killing it (data loss? can restart later?)
- Your recommendation

EXAMPLE APPROVAL REQUEST:
"I found the issue:

**Process:** ffmpeg (PID 1337)
**Usage:** 99.8% CPU, 45% Memory
**Task:** Video transcoding - converting wedding_video.mp4 to 4K format
**Running for:** 45 minutes
**Owner:** media-service (batch job)
**Impact if killed:** Low - batch job can be restarted later, no data loss

Recommended action: Kill process 1337 to restore system performance.

Should I proceed? Reply 'yes' to approve or 'no' to cancel."
[STOP HERE - wait for user response]

GUIDELINES:
- For status checks: Explain what you're checking, then call the tool.
- Use `ps aux | head -20` or `top -b -n1 | head -20` to list processes.
- After fixing, ALWAYS verify by checking system health again.
- Use PowerShell on Windows (`;` not `&&`), bash on Linux.
- Only use send_slack_message for NOTIFICATIONS after resolution, not for approvals.

CRITICAL - ALWAYS CONFIRM TO USER:
After completing any task, you MUST tell the user the final outcome in plain text BEFORE or AFTER any Slack/ticket notifications.
Example: "Done! Process 1337 has been killed. CPU is now at 15.4% (normal). I've also notified the ops team on Slack."
NEVER end a conversation with just a tool call - always provide a human-readable summary.

POWERPOINT WORKFLOW:
When creating or editing presentations, follow this goal-based workflow:

1. ANALYZE PHASE:
   - FIRST: ppt_get_active_presentation() to check if a presentation is ALREADY OPEN
   - If no presentation open: ppt_open_presentation(path) to open a file
   - ppt_get_theme_colors() to understand colors and fonts
   - ppt_get_slide_info(0) to see all slides
   - If user references specific slides, use ppt_goto_slide(N) then look_at_screen() to visually analyze

2. PLAN PHASE (think before acting):
   - Structure your content (titles, key points, flow)
   - Decide which reference slide to duplicate as template
   - Plan visual elements (shapes, images) if needed

3. BUILD PHASE:
   - ppt_duplicate_slide() to clone a well-designed reference slide
   - ppt_edit_text() to replace content while preserving formatting
   - ppt_add_shape() for visual elements (arrows, callouts)
   - ppt_add_picture() to insert images
   - ppt_move_shape() and ppt_resize_shape() for layout adjustments

4. VERIFY PHASE:
   - ppt_goto_slide() and look_at_screen() to verify result
   - Ensure consistency with original theme
   - ppt_save_presentation() when complete

IMPORTANT: Duplicate existing slides rather than creating blank ones - this preserves theme formatting perfectly."""

        yield json.dumps({"type": "status_change", "phase": "planning", "content": f"Initializing ({complexity_request} mode)..."}) + "\n"

        current_mission_id = None
        current_criteria = None

        try:
            # Create model with tools
            log_system(f"Creating model: {model_name} with {len(tools)} tools", "MODEL")
            model = genai.GenerativeModel(
                model_name=model_name,
                tools=tools,
                system_instruction=system_instruction
            )
            log_system(f"Model created successfully", "MODEL")
            
            # Use session history for conversation continuity
            history = self.sessions[session_id]
            chat = model.start_chat(history=history, enable_automatic_function_calling=False)
            log_system(f"Chat started with {len(history)} history items", "MODEL")

            # Format message based on context
            if len(history) > 0:
                # This is a follow-up message (like "yes" for approval)
                user_message = message
                log_system(f"Follow-up message in session: {message}", "SESSION")
            else:
                # New conversation - prefix with GOAL
                user_message = f"GOAL: {message}"
            
            # Send message and store in history
            log_system(f"Sending to model: {user_message[:100]}...", "MODEL")
            response = await self._send_with_retry(chat, user_message)
            log_system(f"Response received from model", "MODEL")
            
            # Update session history with user message
            self.sessions[session_id].append({"role": "user", "parts": [user_message]})

            max_turns = 15
            for turn in range(max_turns):
                # Extract parts safely
                if not response.candidates or not response.candidates[0].content.parts:
                    break
                parts = response.candidates[0].content.parts
                text_content = ""
                function_calls = []

                for part in parts:
                    if part.text:
                        text_content += part.text
                    if part.function_call:
                        function_calls.append(part.function_call)

                # Stream thought/text to UI
                if text_content:
                    msg_type = "llm_thought" if function_calls else "response"
                    log_system(f"LLM: {text_content[:100]}...", "THOUGHT" if function_calls else "RESPONSE")
                    yield json.dumps({"type": msg_type, "content": text_content}) + "\n"

                # No tools = done - save model response to session
                if not function_calls:
                    if text_content:
                        self.sessions[session_id].append({"role": "model", "parts": [text_content]})
                    break

                # Execute tools
                safe_calls = [{"name": fc.name, "args": proto_to_dict(fc.args)} for fc in function_calls]
                yield json.dumps({"type": "tool_call_batch", "calls": safe_calls}) + "\n"

                response_parts = []
                for i, call_info in enumerate(safe_calls):
                    name = call_info['name']
                    args = call_info['args']
                    
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

                    # Handle screenshot sharing specially
                    if str(res).startswith("__SCREENSHOT__:"):
                        parts = str(res).split(":__CAPTION__:")
                        image_data = parts[0].replace("__SCREENSHOT__:", "")
                        caption = parts[1] if len(parts) > 1 else "Screenshot"
                        yield json.dumps({"type": "status_change", "phase": "screenshot", "metadata": {"screenshot": image_data}, "content": caption}) + "\n"
                        res = f"Screenshot shared with user: {caption}"
                    
                    # Build response
                    response_parts.append(protos.Part(function_response=protos.FunctionResponse(
                        name=function_calls[i].name,
                        response={"result": str(res)}
                    )))
                    yield json.dumps({"type": "tool_result", "name": name, "content": str(res)[:500]}) + "\n"

                # Send results back
                response = await self._send_with_retry(chat, response_parts)

            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

        except Exception as e:
            log_system(f"HIVE ERROR: {e}", "ERR")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    async def _verify_outcome(self, claim, evidence, criteria):
        prompt = f"You are a QA Auditor. Verify if the claim is supported by evidence.\nClaim: {claim}\nEvidence: {evidence}\nCriteria: {criteria}\n\nRespond with JSON: {{\"verified\": true/false, \"reason\": \"...\"}}"
        try:
            model = genai.GenerativeModel(self.FAST_TEXT_MODEL)
            response = await asyncio.to_thread(model.generate_content, prompt)
            text = response.text
            start, end = text.find('{'), text.rfind('}') + 1
            return json.loads(text[start:end])
        except Exception as e:
            return {"verified": False, "reason": f"Verifier error: {e}"}

    async def process_vision_command(self, image_bytes: bytes, user_prompt: str) -> str:
        if not self.api_key: return "System Error: API Key missing."
        model = genai.GenerativeModel(self.VISION_MODEL)
        response = await asyncio.to_thread(
            model.generate_content,
            [user_prompt, {'mime_type': 'image/png', 'data': image_bytes}]
        )
        return response.text
