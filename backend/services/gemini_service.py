
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
from backend.services.desktop.factory import get_desktop_service, _active_agent_url
from backend.utils.logger import log_system
from backend.registry.workstation_registry import get_registry
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

        # NOTE: Desktop service is fetched dynamically via get_desktop_service() 
        # to support agent switching at runtime
        
        # Session-based conversation history for multi-turn interactions
        self.sessions = {}  # {session_id: [{"role": "user/model", "parts": [...]}]}
        
        # Track approved commands per session (for command guard bypass after user approval)
        self.approved_commands = {}  # {session_id: set(command_hashes)}
        
        # Temporary storage for uploaded images (for save_uploaded_image tool)
        self.current_uploaded_image = None  # {"bytes": bytes, "mime_type": str}

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
            # Image handling
            "save_uploaded_image": self.save_uploaded_image,
        }
        
        log_system(f"Gemini Service Initialized with {len(self.tools_map)} tools.", "INIT")

    def _get_active_agent_os(self) -> tuple[str, str]:
        """Get the active agent's OS type and shell commands."""
        from backend.services.desktop.factory import _active_agent_url
        
        if _active_agent_url:
            # Find the workstation by URL
            registry = get_registry()
            for ws in registry.workstations.values():
                if ws.api_url == _active_agent_url:
                    ws_type = ws.workstation_type.lower()
                    if ws_type == "windows":
                        return ("Windows", "PowerShell (use `;` not `&&`)")
                    elif ws_type in ["linux", "container"]:
                        return ("Linux", "bash (use `&&` for chaining)")
                    else:
                        return (ws_type.title(), "appropriate shell")
        
        # Default: check local OS
        import platform
        local_os = platform.system()
        if local_os == "Windows":
            return ("Windows", "PowerShell (use `;` not `&&`)")
        return ("Linux", "bash (use `&&` for chaining)")

    # --- DESKTOP WRAPPERS (names must match tools_map keys for SDK inference) ---
    def get_system_health(self): 
        """Returns system CPU, memory, and status."""
        return get_desktop_service().get_system_health()
    
    def click_at(self, x: int, y: int): 
        """Clicks at the specified X,Y screen coordinates."""
        return get_desktop_service().click_at(x, y)
    
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int): 
        """Drags from start coordinates to end coordinates."""
        return get_desktop_service().drag_mouse(start_x, start_y, end_x, end_y)
    
    def type_text(self, text: str): 
        """Types the specified text using keyboard."""
        return get_desktop_service().type_text(text)
    
    def press_hotkey(self, keys: list[str]): 
        """Presses a keyboard hotkey combination."""
        return get_desktop_service().press_hotkey(keys)
    
    def wait_seconds(self, seconds: int): 
        """Waits for the specified number of seconds."""
        return get_desktop_service().wait_seconds(seconds)
    
    def run_terminal_command(self, command: str, session_id: str = None): 
        """Executes a shell/terminal command with security guardrails."""
        import sys, os
        # Add backend directory to path for tools import
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from tools.command_guard import check_command_safety, CommandRisk
        import hashlib
        
        # Check command safety before execution
        check_result = check_command_safety(command)
        
        if check_result.risk_level == CommandRisk.BLOCKED:
            return f"BLOCKED: {check_result.reason}. This command is not allowed for security reasons."
        
        if check_result.risk_level == CommandRisk.NEEDS_APPROVAL:
            # Check if this command was already approved in current session
            cmd_hash = hashlib.md5(command.encode()).hexdigest()
            if session_id and session_id in self.approved_commands:
                if cmd_hash in self.approved_commands[session_id]:
                    # Previously approved - execute it
                    return get_desktop_service().run_terminal_command(command)
            
            # Mark as pending approval (will be added to approved set when user says yes)
            if session_id:
                if session_id not in self.approved_commands:
                    self.approved_commands[session_id] = set()
                self.approved_commands[session_id].add(cmd_hash)
            
            # Return approval request - agent should ask user before proceeding
            return f"APPROVAL_REQUIRED: {check_result.reason}. Command: {command}. Should I proceed? Reply 'yes' to approve or 'no' to cancel."
        
        # Safe command - execute directly
        return get_desktop_service().run_terminal_command(command)
    
    def open_target(self, resource: str): 
        """Opens a URL or file."""
        return get_desktop_service().open_target(resource)
    
    def read_page_content(self): 
        """Reads text content from the active window/page."""
        return get_desktop_service().read_page_content()
    
    def scroll_page(self, direction: str = 'down'): 
        """Scrolls the active window up or down."""
        return get_desktop_service().scroll_page(direction)
    
    def browser_command(self, action: str, url: str = None): 
        """Controls browser via hotkeys (NEW_TAB, CLOSE_TAB, NAVIGATE, REFRESH, SEARCH)."""
        return get_desktop_service().browser_command(action, url)
    
    def scan_ui_tree(self): 
        """Scans the accessibility tree for UI elements."""
        return get_desktop_service().scan_ui_tree()

    def focus_window(self, title: str):
        """Brings a window to the foreground by title (partial match). Use before interacting with a specific app."""
        return get_desktop_service().focus_window(title)

    def get_window_rect(self, title: str):
        """Gets window position and size: {x, y, width, height}. Use to calculate safe drawing coordinates."""
        return get_desktop_service().get_window_rect(title)

    def list_windows(self):
        """Lists all visible windows with their titles and positions."""
        return get_desktop_service().list_windows()

    def look_at_screen(self, purpose: str):
        base64_img = get_desktop_service().get_screenshot_base64()
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
        base64_img = get_desktop_service().get_screenshot_base64()
        if not base64_img: 
            return "Screenshot failed - could not capture screen"
        log_system(f"Screenshot captured for user: {caption}", "SCREENSHOT")
        # Return special marker with base64 data - handled in streaming loop
        return f"__SCREENSHOT__:data:image/jpeg;base64,{base64_img}:__CAPTION__:{caption}"

    def save_uploaded_image(self, file_path: str):
        """Save the currently uploaded image to the specified file path. Use this when user uploads an image and asks to save it."""
        if not self.current_uploaded_image:
            return "ERROR: No uploaded image available. The user must upload an image first."
        
        try:
            import os
            # Expand user paths like ~/Desktop
            expanded_path = os.path.expanduser(file_path)
            # Expand environment variables like $env:USERPROFILE
            expanded_path = os.path.expandvars(expanded_path)
            
            # Ensure directory exists
            dir_path = os.path.dirname(expanded_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # Write the image bytes
            with open(expanded_path, 'wb') as f:
                f.write(self.current_uploaded_image['bytes'])
            
            log_system(f"Uploaded image saved to: {expanded_path}", "IMAGE")
            return f"SUCCESS: Image saved to {expanded_path}"
        except Exception as e:
            return f"ERROR: Failed to save image: {str(e)}"

    async def _execute_with_index(self, index: int, name: str, args: dict, session_id: str = None):
        func = self.tools_map.get(name)
        if not func: return (index, name, f"Error: Tool {name} not found")
        try:
            # Special handling for run_terminal_command to pass session_id for approval tracking
            if name == "run_terminal_command" and session_id:
                args = {**args, "session_id": session_id}
            
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = await asyncio.to_thread(func, **args)
            return (index, name, res)
        except Exception as e: return (index, name, str(e))

    async def _send_with_retry(self, chat, content, retries=2):
        """Send message with retry on transient errors (500, MALFORMED_FUNCTION_CALL)"""
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(chat.send_message, content)
            except Exception as e:
                error_str = str(e)
                is_retryable = (
                    "MALFORMED_FUNCTION_CALL" in error_str or
                    "500" in error_str or
                    "Internal error" in error_str or
                    "UNAVAILABLE" in error_str
                )
                if is_retryable and attempt < retries:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s
                    log_system(f"Retryable error: {error_str[:100]} - Retry {attempt+1}/{retries} in {wait_time}s", "WARN")
                    await asyncio.sleep(wait_time)
                    continue
                raise e

    # --- DIRECT COMMAND DETECTION ---
    def _is_shell_command(self, message: str) -> tuple[bool, str]:
        """
        Detect if message is a shell command prefixed with '!'.
        
        Returns:
            (is_command, command_text) - True if starts with !, and the command without prefix
        """
        msg = message.strip()
        
        # Commands must start with ! prefix to be executed directly
        # This prevents accidental execution (e.g., voice saying "less" heard as "ls")
        if msg.startswith('!'):
            return (True, msg[1:].strip())
        
        return (False, "")

    # --- MAIN ORCHESTRATOR ---
    async def route_and_execute_stream(self, message: str, complexity_request: str = "fast", session_id: str = None):
        log_system(f"NEW REQUEST: {message} (Mode: {complexity_request}, Session: {session_id})", "ROUTER")
        
        # Generate unique session ID if not provided - use microseconds for uniqueness
        import uuid
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # --- DIRECT COMMAND EXECUTION ---
        # If input starts with !, execute as shell command directly (with guardrails)
        is_command, command = self._is_shell_command(message)
        if is_command:
            log_system(f"DIRECT COMMAND DETECTED: !{command}", "ROUTER")
            yield json.dumps({"type": "llm_thought", "content": f"Executing: `{command}`"}) + "\n"
            
            result = self.run_terminal_command(command, session_id)
            
            # Check if approval is required
            if isinstance(result, str) and result.startswith("APPROVAL_REQUIRED:"):
                yield json.dumps({"type": "final_response", "content": result}) + "\n"
                return
            elif isinstance(result, str) and result.startswith("BLOCKED:"):
                yield json.dumps({"type": "final_response", "content": result}) + "\n"
                return
            
            # Format and return result
            if isinstance(result, dict):
                if result.get('success'):
                    output = result.get('output', 'Command completed')
                    yield json.dumps({"type": "final_response", "content": f"```\n{output}\n```"}) + "\n"
                else:
                    error = result.get('error', 'Command failed')
                    yield json.dumps({"type": "final_response", "content": f"Error: {error}"}) + "\n"
            else:
                yield json.dumps({"type": "final_response", "content": f"```\n{result}\n```"}) + "\n"
            return
        
        # Get or create session history - limit to last 6 messages (3 exchanges) to prevent stale command re-execution
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            log_system(f"New session created: {session_id}", "SESSION")
        else:
            # Trim old history to prevent model from re-executing old commands
            if len(self.sessions[session_id]) > 6:
                self.sessions[session_id] = self.sessions[session_id][-6:]
                log_system(f"Trimmed session history to last 6 messages", "SESSION")
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

        # Get active agent's OS context
        agent_os, shell_type = self._get_active_agent_os()
        log_system(f"Active agent OS: {agent_os}, Shell: {shell_type}", "ROUTER")

        # System instruction for transparency - dynamic OS context
        system_instruction = f"""You are Proxi, a Headless Operator with FULL OS-level access on this {agent_os} computer.

IMPORTANT: You are connected to a {agent_os} system. Use {shell_type} for commands.

YOU HAVE ACCESS TO THESE CAPABILITIES - USE THEM:
- run_terminal_command: Execute PowerShell commands (dir, ls, Get-Process, etc.)
- look_at_screen: Take screenshot and analyze what's visible (for YOUR analysis only)
- share_screenshot: Take screenshot and SHOW it to the user in the chat UI
- save_uploaded_image: Save an image the user uploaded to a file path (e.g. Desktop)
- open_target: Open files, folders, URLs, or applications
- click_at, type_text, press_hotkey: Control mouse and keyboard
- ppt_* tools: Edit PowerPoint presentations
- get_system_health: Check CPU, memory, disk usage

TO LIST FILES ON DESKTOP, use: run_terminal_command with "dir $env:USERPROFILE\\Desktop" or "ls ~/Desktop"
TO OPEN AN IMAGE, use: open_target with the image path
TO SEE THE SCREEN (for your analysis), use: look_at_screen
TO SHOW THE USER A SCREENSHOT, use: share_screenshot - this displays it in the chat!
TO SAVE AN UPLOADED IMAGE, use: save_uploaded_image with full path like "C:\\Users\\azureuser\\Desktop\\image.jpg"

CRITICAL - ALWAYS BRING WINDOWS TO FRONT:
Before clicking, typing, or analyzing any application window:
1. Call focus_window(title) to bring it to foreground
2. Wait briefly with wait_seconds(0.5) if needed
3. Then proceed with your action
This ensures the user can SEE what you're doing. Never interact with background windows!

CRITICAL RULE - THINK BEFORE YOU ACT:
Before EVERY tool call, explain: WHAT you're doing, WHY, and WHAT you expect.

=== MISSION PLANNING ===
For COMPLEX REQUESTS (multiple steps/tools), output a PLAN block FIRST:

PLAN_START
G1: [First goal title] - [brief description]
G2: [Second goal title] - [brief description]
G3: [Third goal title] - [brief description]
PLAN_END

Then as you complete each goal, output:
GOAL_UPDATE: G1 COMPLETE - [result summary]
GOAL_UPDATE: G2 ACTIVE
GOAL_UPDATE: G2 COMPLETE - [result summary]

This helps the user track progress. For simple single-step requests, skip the plan.

=== VERIFIABLE AGENT PROTOCOL ===
Use Triple Handshake ONLY for STATE-CHANGING ACTIONS that can be verified:

WHEN TO USE (action tasks with persistent results):
  ✓ "Kill process X" → verify process no longer exists
  ✓ "Delete file Y" → verify file is gone
  ✓ "Stop service Z" → verify service stopped
  ✓ "Create backup" → verify backup file exists

WHEN NOT TO USE (query tasks with transient results):
  ✗ "Check CPU usage" → just call get_system_health and report the value
  ✗ "List processes" → just run command and report results
  ✗ "What's memory usage?" → just report current snapshot
  (These metrics change every second - verification would always fail!)

FOR QUERY TASKS: Just use tools directly and report results. No assign_mission needed.

FOR ACTION TASKS - Triple Handshake:
  STEP 1: assign_mission(goal, verification_criteria)
    - verification_criteria: '{{"type": "process_killed", "pid": 1234}}' or '{{"type": "file_exists", "path": "/tmp/backup.zip"}}'
  STEP 2: Execute the action (kill process, delete file, etc.)
  STEP 3: report_execution(mission_id, summary)

Example - Kill process:
  assign_mission("Kill high-CPU process", '{{"type": "process_killed", "pid": 41652}}')
  run_terminal_command("taskkill /PID 41652 /F")
  report_execution("abc123", "Process 41652 terminated")
=== END VERIFIABLE AGENT ===

INCIDENT RESOLUTION FLOW:
1. DIAGNOSE: Check system health, identify the problem
2. ANALYZE: Identify the specific process causing issues (name, PID, resource usage)
3. EXECUTE DIRECTLY: Just run the command - Command Guard will intercept if approval needed
4. VERIFY: Check system health again to confirm resolution
5. CONFIRM: Report the final outcome to the user

CRITICAL - COMMAND GUARD HANDLES APPROVALS AUTOMATICALLY:
- Do NOT pre-ask for approval before running commands
- Just run the command directly (e.g., taskkill, Stop-Process)
- If command needs approval, run_terminal_command will return "APPROVAL_REQUIRED:..."
- When you see APPROVAL_REQUIRED: Tell user what command needs approval and ask "Should I proceed?"
- When user says "yes": Retry the SAME command - it will execute this time
- BLOCKED commands: Inform user and suggest alternatives

IMPORTANT - DO NOT DOUBLE-ASK:
- Do NOT ask "Should I proceed?" BEFORE trying a command
- Let Command Guard handle the approval gate
- Only ask AFTER you see APPROVAL_REQUIRED in the tool response
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
            
            # Check if message contains embedded image data (from vision-action endpoint)
            message_content = user_message
            if "IMAGE_DATA:" in message:
                # Extract image data and create multimodal content
                import re
                match = re.search(r'IMAGE_DATA:([^;]+);base64,([^\s]+)', message)
                if match:
                    mime_type = match.group(1)
                    image_b64 = match.group(2)
                    # Remove the IMAGE_DATA from text prompt
                    text_prompt = re.sub(r'IMAGE_DATA:[^\s]+', '', message).strip()
                    log_system(f"Multimodal request detected, image size: {len(image_b64)} chars", "VISION")
                    # Create multimodal content for Gemini
                    import base64
                    image_bytes = base64.b64decode(image_b64)
                    
                    # Store image for save_uploaded_image tool
                    self.current_uploaded_image = {'bytes': image_bytes, 'mime_type': mime_type}
                    log_system(f"Uploaded image stored ({len(image_bytes)} bytes) for save_uploaded_image tool", "IMAGE")
                    
                    message_content = [
                        text_prompt,
                        {'mime_type': mime_type, 'data': image_bytes}
                    ]
            
            # Send message and store in history
            log_system(f"Sending to model: {str(message_content)[:100]}...", "MODEL")
            response = await self._send_with_retry(chat, message_content)
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
                    
                    # Parse PLAN blocks for goal tracking
                    if "PLAN_START" in text_content and "PLAN_END" in text_content:
                        try:
                            plan_match = text_content.split("PLAN_START")[1].split("PLAN_END")[0]
                            goals = []
                            goal_counter = 0
                            step_counter = 0
                            current_goal_num = 0
                            for line in plan_match.strip().split("\n"):
                                line = line.strip()
                                if line.startswith("G") and ":" in line:
                                    # Main goal: G1 -> 1, G2 -> 2
                                    goal_counter += 1
                                    current_goal_num = goal_counter
                                    step_counter = 0
                                    parts = line.split(":", 1)
                                    original_id = parts[0].strip()  # e.g., "G1"
                                    goal_text = parts[1].strip() if len(parts) > 1 else ""
                                    if " - " in goal_text:
                                        title, desc = goal_text.split(" - ", 1)
                                    else:
                                        title, desc = goal_text, ""
                                    goals.append({"id": str(goal_counter), "original_id": original_id, "title": title.strip(), "description": desc.strip(), "status": "pending"})
                                elif line.startswith("S") and ":" in line:
                                    # Sub-step: S1 -> 1.1, S2 -> 1.2
                                    step_counter += 1
                                    parts = line.split(":", 1)
                                    original_id = parts[0].strip()  # e.g., "S1"
                                    step_text = parts[1].strip() if len(parts) > 1 else ""
                                    if " - " in step_text:
                                        title, desc = step_text.split(" - ", 1)
                                    else:
                                        title, desc = step_text, ""
                                    goals.append({"id": f"{current_goal_num}.{step_counter}", "original_id": original_id, "title": title.strip(), "description": desc.strip(), "status": "pending", "is_step": True})
                            if goals:
                                yield json.dumps({"type": "plan", "goals": goals}) + "\n"
                                log_system(f"Plan extracted: {len(goals)} goals", "PLAN")
                        except Exception as e:
                            log_system(f"Failed to parse plan: {e}", "PLAN")
                    
                    # Parse GOAL_UPDATE for progress tracking
                    # Convert G1->1, G2->2, S1->x.1 format
                    if "GOAL_UPDATE:" in text_content:
                        try:
                            for line in text_content.split("\n"):
                                if "GOAL_UPDATE:" in line:
                                    update_part = line.split("GOAL_UPDATE:")[1].strip()
                                    # Format: G1 COMPLETE - result or G2 ACTIVE
                                    parts = update_part.split(" ", 1)
                                    original_id = parts[0]  # e.g., "G1" or "S2"
                                    rest = parts[1] if len(parts) > 1 else ""
                                    
                                    # Convert G1->1, G2->2 (simple numeric extraction)
                                    if original_id.startswith("G"):
                                        goal_id = original_id[1:]  # G1 -> 1
                                    elif original_id.startswith("S"):
                                        # For steps, we need context - for now keep as-is
                                        goal_id = original_id
                                    else:
                                        goal_id = original_id
                                    
                                    if "COMPLETE" in rest:
                                        status = "complete"
                                        result = rest.replace("COMPLETE", "").replace("-", "").strip()
                                    elif "ACTIVE" in rest:
                                        status = "active"
                                        result = ""
                                    elif "FAILED" in rest:
                                        status = "failed"
                                        result = rest.replace("FAILED", "").replace("-", "").strip()
                                    else:
                                        status = "active"
                                        result = rest
                                    yield json.dumps({"type": "goal_update", "goal_id": goal_id, "status": status, "result": result}) + "\n"
                                    log_system(f"Goal update: {original_id} -> {goal_id} ({status})", "PLAN")
                        except Exception as e:
                            log_system(f"Failed to parse goal update: {e}", "PLAN")

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

                    # Execute (pass session_id for approval tracking)
                    _, _, res = await self._execute_with_index(i, name, args, session_id)

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
                    res_str = str(res)
                    log_system(f"Tool result preview: {res_str[:100]}...", "DEBUG")
                    if res_str.startswith("__SCREENSHOT__:"):
                        log_system("Screenshot marker detected, sending to UI", "SCREENSHOT")
                        parts = res_str.split(":__CAPTION__:")
                        image_data = parts[0].replace("__SCREENSHOT__:", "")
                        caption = parts[1] if len(parts) > 1 else "Screenshot"
                        log_system(f"Screenshot data length: {len(image_data)}, caption: {caption}", "SCREENSHOT")
                        yield json.dumps({"type": "status_change", "phase": "screenshot", "metadata": {"screenshot": image_data}, "content": caption}) + "\n"
                        res = f"Screenshot shared with user: {caption}"
                    
                    # Check for approval required
                    res_str = str(res)
                    if res_str.startswith("APPROVAL_REQUIRED:"):
                        # Parse: "APPROVAL_REQUIRED: reason. Command: cmd. Should I proceed?"
                        import re
                        match = re.search(r'APPROVAL_REQUIRED:\s*(.+?)\.\s*Command:\s*(.+?)\.\s*Should', res_str)
                        if match:
                            reason, command = match.group(1), match.group(2)
                            yield json.dumps({"type": "approval_required", "reason": reason, "command": command, "risk_level": "moderate"}) + "\n"
                    
                    # Check for escalation
                    if "ESCALATED" in res_str and "Human Operator" in res_str:
                        import re
                        match = re.search(r'Mission\s+(\S+)\s+ESCALATED.*Reason:\s*(.+)', res_str)
                        if match:
                            mission_id, reason = match.group(1), match.group(2)
                            yield json.dumps({"type": "escalation", "mission_id": mission_id, "reason": reason}) + "\n"
                    
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
