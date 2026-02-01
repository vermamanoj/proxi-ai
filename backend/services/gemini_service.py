
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

# PPT tools are now proxied via get_desktop_service() to Windows agent
# Direct imports removed - using wrapper methods instead

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
    
    # Execution mode configurations - loaded from external config file
    @staticmethod
    def _load_mode_configs():
        """Load mode configurations from external JSON file for easy editing."""
        config_path = Path(__file__).parent.parent / "config" / "modes.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
                # Remove comment fields
                return {k: v for k, v in configs.items() if not k.startswith('_')}
        except FileNotFoundError:
            log_system(f"Mode config not found at {config_path}, using defaults", "WARN")
            return {
                "quick": {"model": "flash", "verify": False, "max_turns": 5, "max_tool_calls": 8, "timeout": 30, "prompt_suffix": "", "description": "Quick mode"},
                "balanced": {"model": "flash", "verify": "auto", "max_turns": 10, "max_tool_calls": 20, "timeout": 60, "prompt_suffix": "", "description": "Balanced mode"},
                "thorough": {"model": "pro", "verify": True, "max_turns": 15, "max_tool_calls": 40, "timeout": 90, "prompt_suffix": "", "description": "Thorough mode"}
            }
    
    MODE_CONFIGS = None  # Loaded dynamically in __init__

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            log_system(f"GEMINI_API_KEY loaded. ({self.api_key[:8]}...{self.api_key[-4:]})", "INIT")
        else:
            log_system("CRITICAL: GEMINI_API_KEY not found.", "ERR")
        
        # Load mode configurations from external file
        GeminiService.MODE_CONFIGS = self._load_mode_configs()
        log_system(f"Loaded {len(GeminiService.MODE_CONFIGS)} execution modes from config", "INIT")
        
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
        
        # Track pending approvals awaiting user decision
        self.pending_approvals = {}  # {approval_id: {command, session_id, timestamp, cmd_hash}}
        
        # Temporary storage for uploaded images (for save_uploaded_image tool)
        self.current_uploaded_image = None  # {"bytes": bytes, "mime_type": str}
        
        # Track cancelled sessions for Stop button functionality
        self.cancelled_sessions = set()  # {session_id}
        
        # Track last active agent per session (for switch notifications)
        self.session_agents = {}  # {session_id: "agent_name"}
        
        # Evidence store for "evidence on demand" pattern
        # Claims are presented first, artifacts fetched when user asks
        self.evidence_store = {}  # {evidence_id: {claim, evidence_type, data, timestamp}}
        
        # Log dev mode status at startup
        dev_mode = os.environ.get("PROXI_DEV_MODE", "").lower() in ("true", "1", "yes")
        if dev_mode:
            log_system("[!] DEV MODE ENABLED - Command approvals DISABLED (sandbox/demo mode)", "WARN")

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
            "ground_and_click": self.ground_and_click,
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
            # PowerPoint Tools (proxied to Windows agent)
            "ppt_get_active_presentation": self.ppt_get_active_presentation,
            "ppt_open_presentation": self.ppt_open_presentation,
            "ppt_get_slide_info": self.ppt_get_slide_info,
            "ppt_edit_text": self.ppt_edit_text,
            "ppt_add_slide": self.ppt_add_slide,
            "ppt_duplicate_slide": self.ppt_duplicate_slide,
            "ppt_delete_slide": self.ppt_delete_slide,
            "ppt_save_presentation": self.ppt_save_presentation,
            "ppt_goto_slide": self.ppt_goto_slide,
            "ppt_add_picture": self.ppt_add_picture,
            "ppt_add_shape": self.ppt_add_shape,
            "ppt_move_shape": self.ppt_move_shape,
            "ppt_resize_shape": self.ppt_resize_shape,
            "ppt_format_text": self.ppt_format_text,
            "ppt_get_theme_colors": self.ppt_get_theme_colors,
            "ppt_add_table": self.ppt_add_table,
            "ppt_set_shape_style": self.ppt_set_shape_style,
            "ppt_add_textbox": self.ppt_add_textbox,
            "ppt_create_business_slide": self.ppt_create_business_slide,
            # Visual elements - charts, images, icons
            "ppt_add_chart": self.ppt_add_chart,
            "ppt_add_image_from_url": self.ppt_add_image_from_url,
            "ppt_add_icon": self.ppt_add_icon,
            "ppt_insert_smartart": self.ppt_insert_smartart,
            # Image handling
            "save_uploaded_image": self.save_uploaded_image,
            # File transfer
            "send_file_to_user": self.send_file_to_user,
            # Macro-action tools (action chunking for smoother automation)
            "open_app": self.open_app,
            "draw_shape": self.draw_shape,
            "navigate_app": self.navigate_app,
            "interact_element": self.interact_element,
            "fill_form": self.fill_form,
            "perform_workflow": self.perform_workflow,
            # Attack path visualization
            "render_attack_path": self.render_attack_path,
            # Evidence on demand
            "store_evidence": self.store_evidence,
            "get_evidence": self.get_evidence,
            "list_evidence": self.list_evidence,
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

    def _get_active_agent_name(self) -> str:
        """Get the active agent's display name."""
        from backend.services.desktop.factory import _active_agent_url
        
        if _active_agent_url:
            # Find the workstation by URL
            registry = get_registry()
            for ws_id, ws in registry.workstations.items():
                if ws.api_url == _active_agent_url:
                    return ws.name or ws_id
        
        # Default: local execution
        import platform
        return f"Local ({platform.system()})"

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
        import secrets
        import time
        
        # DEV MODE: Skip all approvals when PROXI_DEV_MODE=true (for demos/sandbox testing)
        dev_mode = os.environ.get("PROXI_DEV_MODE", "").lower() in ("true", "1", "yes")
        
        # Check command safety before execution
        check_result = check_command_safety(command)
        
        # In dev mode, only block truly dangerous commands, auto-approve everything else
        if check_result.risk_level == CommandRisk.BLOCKED and not dev_mode:
            return f"BLOCKED: {check_result.reason}. This command is not allowed for security reasons."
        elif check_result.risk_level == CommandRisk.BLOCKED and dev_mode:
            log_system(f"[DEV MODE] Bypassing BLOCKED command: {command[:50]}...", "WARN")
        
        if check_result.risk_level == CommandRisk.NEEDS_APPROVAL and not dev_mode:
            # Check if this command was already approved in current session
            cmd_hash = hashlib.md5(command.encode()).hexdigest()
            if session_id and session_id in self.approved_commands:
                if cmd_hash in self.approved_commands[session_id]:
                    # Previously approved - execute it
                    return get_desktop_service().run_terminal_command(command)
            
            # Check if there's already a pending approval for this exact command (prevent duplicate prompts)
            existing_approval_id = None
            for aid, approval in self.pending_approvals.items():
                if approval.get("cmd_hash") == cmd_hash and approval.get("session_id") == session_id:
                    existing_approval_id = aid
                    break
            
            if existing_approval_id:
                # User is retrying after seeing approval request - this means they approved via chat
                # Execute the command and mark as approved
                approval_id = existing_approval_id
                log_system(f"Chat-approved command executing: {command[:30]}... (approval: {approval_id})", "APPROVAL")
                
                # Add to approved commands for session
                if session_id:
                    if session_id not in self.approved_commands:
                        self.approved_commands[session_id] = set()
                    self.approved_commands[session_id].add(cmd_hash)
                
                # Remove from pending
                if existing_approval_id in self.pending_approvals:
                    del self.pending_approvals[existing_approval_id]
                
                # Execute the command
                return get_desktop_service().run_terminal_command(command)
            else:
                # Generate unique approval ID and store as pending
                approval_id = secrets.token_urlsafe(16)
                self.pending_approvals[approval_id] = {
                    "command": command,
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "cmd_hash": cmd_hash,
                    "reason": check_result.reason
                }
            
            # Return approval request with approval_id
            return f"APPROVAL_REQUIRED:{approval_id}:{check_result.reason}. Command: {command}. Should I proceed? Reply 'yes' to approve or 'no' to cancel."
        elif check_result.risk_level == CommandRisk.NEEDS_APPROVAL and dev_mode:
            log_system(f"[DEV MODE] Auto-approving: {command[:50]}...", "DEV")
        
        # Safe command (or dev mode auto-approved) - execute directly
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

    # --- PPT WRAPPERS (proxied to Windows agent via get_desktop_service) ---
    def ppt_get_active_presentation(self):
        """Gets info about the currently active/open PowerPoint presentation."""
        return get_desktop_service().ppt_get_active_presentation()
    
    def ppt_open_presentation(self, file_path: str):
        """Opens a PowerPoint presentation file."""
        return get_desktop_service().ppt_open_presentation(file_path)
    
    def ppt_get_slide_info(self, slide_number: int = 0):
        """Gets information about a specific slide or all slides if slide_number is 0."""
        return get_desktop_service().ppt_get_slide_info(slide_number)
    
    def ppt_edit_text(self, slide_number: int, shape_name: str, new_text: str):
        """Edits text in a specific shape on a slide, preserving formatting."""
        return get_desktop_service().ppt_edit_text(slide_number, shape_name, new_text)
    
    def ppt_add_slide(self, after_slide: int = 0, layout: str = "title_content"):
        """Adds a new slide to the presentation, inheriting the theme."""
        return get_desktop_service().ppt_add_slide(after_slide, layout)
    
    def ppt_duplicate_slide(self, slide_number: int):
        """Duplicates an existing slide, preserving all formatting and content."""
        return get_desktop_service().ppt_duplicate_slide(slide_number)
    
    def ppt_delete_slide(self, slide_number: int):
        """Deletes a slide from the presentation."""
        return get_desktop_service().ppt_delete_slide(slide_number)
    
    def ppt_save_presentation(self, save_as_path: str = None):
        """Saves the current presentation. Optionally saves to a new file."""
        return get_desktop_service().ppt_save_presentation(save_as_path)
    
    def ppt_goto_slide(self, slide_number: int):
        """Navigates to a specific slide in the presentation."""
        return get_desktop_service().ppt_goto_slide(slide_number)
    
    def ppt_add_picture(self, slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400):
        """Adds a picture to a slide at the specified position."""
        return get_desktop_service().ppt_add_picture(slide_number, image_path, left, top, width)
    
    def ppt_add_shape(self, slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = ""):
        """Adds a shape to a slide with optional text."""
        return get_desktop_service().ppt_add_shape(slide_number, shape_type, left, top, width, height, text)
    
    def ppt_move_shape(self, slide_number: int, shape_name: str, left: int, top: int):
        """Moves a shape to a new position on the slide."""
        return get_desktop_service().ppt_move_shape(slide_number, shape_name, left, top)
    
    def ppt_resize_shape(self, slide_number: int, shape_name: str, width: int, height: int):
        """Resizes a shape on the slide."""
        return get_desktop_service().ppt_resize_shape(slide_number, shape_name, width, height)
    
    def ppt_format_text(self, slide_number: int, shape_name: str, bold: bool = None, italic: bool = None,
                        font_size: int = None, font_color: str = None):
        """Formats text in a shape (bold, italic, size, color)."""
        return get_desktop_service().ppt_format_text(slide_number, shape_name, bold, italic, font_size, font_color)
    
    def ppt_get_theme_colors(self, slide_number: int = 1):
        """Extracts theme colors from the presentation for consistency."""
        return get_desktop_service().ppt_get_theme_colors(slide_number)
    
    def ppt_add_table(self, slide_number: int, rows: int, cols: int, data: list,
                      left: int = 50, top: int = 150, width: int = 600):
        """Adds a professional table to a slide with data. Perfect for business cases."""
        return get_desktop_service().ppt_add_table(slide_number, rows, cols, data, left, top, width)
    
    def ppt_set_shape_style(self, slide_number: int, shape_name: str, fill_color: str = None,
                            line_color: str = None, line_weight: float = None, transparency: float = None):
        """Styles a shape with fill color, border, and transparency. Use theme colors for brand consistency."""
        return get_desktop_service().ppt_set_shape_style(slide_number, shape_name, fill_color, line_color, line_weight, transparency)
    
    def ppt_add_textbox(self, slide_number: int, text: str, left: int, top: int,
                        width: int = 300, height: int = 50, font_size: int = None,
                        font_color: str = None, bold: bool = False, align: str = "left"):
        """Adds a text box to a slide with custom positioning and formatting."""
        return get_desktop_service().ppt_add_textbox(slide_number, text, left, top, width, height, font_size, font_color, bold, align)
    
    def ppt_create_business_slide(self, slide_number: int, title: str, points: list, highlight_point: int = None):
        """Creates a professional business case slide with title and bullet points. Perfect for executive summaries."""
        return get_desktop_service().ppt_create_business_slide(slide_number, title, points, highlight_point)

    def ppt_add_chart(self, slide_number: int, chart_type: str, data: list,
                      left: int = 100, top: int = 150, width: int = 500, height: int = 350, title: str = None):
        """Adds a data chart (bar, column, line, pie, area, doughnut) to a slide. Perfect for visualizing metrics."""
        return get_desktop_service().ppt_add_chart(slide_number, chart_type, data, left, top, width, height, title)
    
    def ppt_add_image_from_url(self, slide_number: int, image_url: str,
                               left: int = 100, top: int = 100, width: int = 400, alt_text: str = None):
        """Downloads image from URL and inserts it into slide. Use for web images, logos, photos."""
        return get_desktop_service().ppt_add_image_from_url(slide_number, image_url, left, top, width, alt_text)
    
    def ppt_add_icon(self, slide_number: int, icon_name: str,
                     left: int = 100, top: int = 100, size: int = 64, color: str = None):
        """Adds built-in icon shapes (star, arrow, gear, heart, cloud, etc). Use for visual accents."""
        return get_desktop_service().ppt_add_icon(slide_number, icon_name, left, top, size, color)
    
    def ppt_insert_smartart(self, slide_number: int, layout_type: str, items: list,
                            left: int = 100, top: int = 150, width: int = 600, height: int = 400):
        """Inserts SmartArt-style graphics (process flow, hierarchy, list). Great for workflows and org charts."""
        return get_desktop_service().ppt_insert_smartart(slide_number, layout_type, items, left, top, width, height)

    def look_at_screen(self, purpose: str):
        """
        Enhanced observation: screenshot + UI tree + Set-of-Mark overlay.
        Returns vision analysis with numbered element references for precise clicking.
        """
        ds = get_desktop_service()
        
        # Try new combined observation first
        obs = ds.get_observation(include_som=True)
        
        if isinstance(obs, dict) and "error" not in obs:
            # Use the SoM screenshot for better grounding
            img_b64 = obs.get("som_screenshot_base64") or obs.get("screenshot_base64")
            ui_elements = obs.get("ui_elements", [])
            
            # Build element context for LLM
            elem_context = ""
            if ui_elements:
                elem_context = "\n\nNUMBERED UI ELEMENTS (green boxes in image):\n"
                for elem in ui_elements[:40]:
                    elem_context += f"[{elem['id']}] {elem['type']}: \"{elem['text']}\" at ({elem['x']}, {elem['y']})\n"
                elem_context += "\nTo click an element, use click_at(x, y) with coordinates from above."
            
            if img_b64:
                try:
                    model = genai.GenerativeModel(self.VISION_MODEL)
                    response = model.generate_content([
                        f"Purpose: {purpose}. Describe the UI layout and identify elements by their [N] numbers from the green boxes.{elem_context}",
                        {'mime_type': 'image/jpeg', 'data': base64.b64decode(img_b64)}
                    ])
                    log_system(f"Vision analysis complete with SoM for: {purpose}", "VISION")
                    return f"VISION: {response.text}{elem_context}"
                except Exception as e:
                    return f"Vision Error: {e}"
        
        # Fallback to old method
        base64_img = ds.get_screenshot_base64()
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

    def ground_and_click(self, target: str):
        """
        Uses local Gemini on the agent to find and click a UI element.
        
        This is more reliable than look_at_screen + click_at because:
        1. Visual grounding happens locally on the agent (lower latency)
        2. Uses Set-of-Mark numbered elements for precision
        3. Returns coordinates directly without round-trip to Core
        
        Args:
            target: Description of what to click, e.g., "Submit button", "Sign In link", "element [5]"
        
        Returns:
            Result of the click action or error if element not found.
        """
        from backend.services.desktop.factory import _active_agent_url
        import aiohttp
        import asyncio
        
        if not _active_agent_url:
            return "Error: No agent selected. Cannot use ground_and_click."
        
        agent_key = os.environ.get("PROXI_AGENT_KEY", "")
        
        async def _ground():
            url = f"{_active_agent_url}/ground"
            headers = {"X-Agent-Key": agent_key} if agent_key else {}
            payload = {"query": target, "include_som": True}
            
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        return {"success": False, "error": f"Agent returned {response.status}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Run async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _ground())
                    result = future.result()
            else:
                result = loop.run_until_complete(_ground())
        except RuntimeError:
            result = asyncio.run(_ground())
        
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            log_system(f"Ground failed for '{target}': {error}", "GROUND")
            return f"Could not find '{target}': {error}"
        
        action = result.get("action", "none")
        x, y = result.get("x"), result.get("y")
        reasoning = result.get("reasoning", "")
        confidence = result.get("confidence", "unknown")
        
        if action == "none" or x is None or y is None:
            log_system(f"Ground found no target for '{target}': {reasoning}", "GROUND")
            return f"Could not locate '{target}'. {reasoning}"
        
        # Perform the click
        log_system(f"Ground found '{target}' at ({x}, {y}) with {confidence} confidence: {reasoning}", "GROUND")
        click_result = get_desktop_service().click_at(x, y)
        
        return f"Found and clicked '{target}' at ({x}, {y}). Confidence: {confidence}. {reasoning}. Click result: {click_result}"

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

    def send_file_to_user(self, file_path: str, description: str = "File"):
        """
        Send a file from the agent's filesystem to the user in the chat.
        Use this when you have created or modified a file and want to share it with the user.
        
        Args:
            file_path: Full path to the file on the agent's computer (e.g., "C:\\Users\\user\\Desktop\\report.pptx")
            description: Brief description of the file for the user
        
        Returns:
            Special marker that triggers file download in UI, or error message.
        """
        from backend.services.desktop.factory import _active_agent_url
        import aiohttp
        import asyncio
        
        if not _active_agent_url:
            return "ERROR: No agent connected - cannot retrieve file"
        
        agent_key = os.environ.get("PROXI_AGENT_KEY", "")
        headers = {"X-Agent-Key": agent_key} if agent_key else {}
        
        async def fetch_file():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{_active_agent_url}/files/download",
                        json={"file_path": file_path},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        return await resp.json()
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Run async code synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, fetch_file())
                    result = future.result()
            else:
                result = loop.run_until_complete(fetch_file())
        except RuntimeError:
            result = asyncio.run(fetch_file())
        
        if not result.get("success"):
            return f"ERROR: Failed to retrieve file: {result.get('error', 'Unknown error')}"
        
        log_system(f"File retrieved for user: {result.get('filename')} ({result.get('size_bytes')} bytes)", "FILE")
        
        # Return special marker with file data - handled in streaming loop
        return f"__FILE__:{result.get('filename')}:{result.get('mime_type')}:{result.get('content_base64')}:__DESC__:{description}"
    
    def approve_command(self, approval_id: str) -> dict:
        """Approve a pending command and execute it."""
        import time
        
        if approval_id not in self.pending_approvals:
            return {"success": False, "error": "Invalid or expired approval ID"}
        
        approval = self.pending_approvals[approval_id]
        
        # Check if approval expired (5 minutes)
        if time.time() - approval["timestamp"] > 300:
            del self.pending_approvals[approval_id]
            return {"success": False, "error": "Approval request expired"}
        
        # Move command hash to approved set for session
        session_id = approval["session_id"]
        if session_id:
            if session_id not in self.approved_commands:
                self.approved_commands[session_id] = set()
            self.approved_commands[session_id].add(approval["cmd_hash"])
        
        # Execute the command
        command = approval["command"]
        del self.pending_approvals[approval_id]
        
        try:
            result = get_desktop_service().run_terminal_command(command)
            log_system(f"Approved command executed: {command[:50]}...", "APPROVAL")
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def deny_command(self, approval_id: str) -> dict:
        """Deny a pending command."""
        if approval_id not in self.pending_approvals:
            return {"success": False, "error": "Invalid or expired approval ID"}
        
        approval = self.pending_approvals[approval_id]
        command = approval["command"]
        del self.pending_approvals[approval_id]
        
        log_system(f"Command denied by user: {command[:50]}...", "APPROVAL")
        return {"success": True, "message": "Command denied"}

    # ============ MACRO-ACTION TOOLS (Action Chunking) ============
    # These combine multiple atomic actions into semantic operations
    # for smoother, more natural automation
    
    def navigate_app(self, app_name: str, destination: str, wait_seconds: float = 2.0):
        """
        Open an application and navigate to a specific location within it.
        This is a macro-action that combines: focus/open app → wait → visual grounding → navigation.
        
        Args:
            app_name: Name of the app to open (e.g., "Chrome", "Settings", "File Explorer")
            destination: Where to navigate within the app (e.g., "Network settings", "Downloads folder", "oracle.com")
            wait_seconds: How long to wait for app to load (default 2.0)
        
        Returns:
            Summary of navigation result
        """
        import time
        ds = get_desktop_service()
        steps_log = []
        
        # Windows Settings URI shortcuts - open directly without visual grounding
        settings_uri_map = {
            "network": "ms-settings:network",
            "network settings": "ms-settings:network",
            "network & internet": "ms-settings:network",
            "network and internet": "ms-settings:network",
            "network section": "ms-settings:network",
            "wifi": "ms-settings:network-wifi",
            "ethernet": "ms-settings:network-ethernet",
            "vpn": "ms-settings:network-vpn",
            "display": "ms-settings:display",
            "sound": "ms-settings:sound",
            "notifications": "ms-settings:notifications",
            "power": "ms-settings:powersleep",
            "battery": "ms-settings:batterysaver",
            "storage": "ms-settings:storagesense",
            "apps": "ms-settings:appsfeatures",
            "default apps": "ms-settings:defaultapps",
            "bluetooth": "ms-settings:bluetooth",
            "printers": "ms-settings:printers",
            "mouse": "ms-settings:mousetouchpad",
            "keyboard": "ms-settings:keyboard",
            "updates": "ms-settings:windowsupdate",
            "windows update": "ms-settings:windowsupdate",
            "security": "ms-settings:windowsdefender",
            "firewall": "ms-settings:windowsdefender",
            "accounts": "ms-settings:accounts",
            "privacy": "ms-settings:privacy",
            "time": "ms-settings:dateandtime",
            "language": "ms-settings:regionlanguage",
            "about": "ms-settings:about",
        }
        
        # Check if this is a direct Settings navigation (use URI shortcut)
        dest_lower = destination.lower() if destination else ""
        if app_name.lower() in ["settings", "windows settings"]:
            if dest_lower in settings_uri_map:
                uri = settings_uri_map[dest_lower]
                ds.run_terminal_command(f"start {uri}")
                steps_log.append(f"Opened Settings > {destination} directly via {uri}")
                time.sleep(wait_seconds)
                return f"NAVIGATE_APP completed: {' → '.join(steps_log)}"
        
        # Step 1: Try to focus existing window or open app
        focus_result = ds.focus_window(app_name)
        if "not found" in str(focus_result).lower():
            # App not open, try to open it
            if app_name.lower() in ["chrome", "google chrome"]:
                open_result = ds.open_target(f"https://{destination}" if "." in destination else "https://google.com")
                steps_log.append(f"Opened Chrome with {destination}")
            elif app_name.lower() in ["settings", "windows settings"]:
                # Check if destination matches a known URI
                for key, uri in settings_uri_map.items():
                    if key in dest_lower:
                        ds.run_terminal_command(f"start {uri}")
                        steps_log.append(f"Opened Settings > {destination} via {uri}")
                        time.sleep(wait_seconds)
                        return f"NAVIGATE_APP completed: {' → '.join(steps_log)}"
                # Fallback to generic settings
                ds.run_terminal_command("start ms-settings:")
                steps_log.append("Opened Windows Settings")
            elif app_name.lower() in ["file explorer", "explorer"]:
                ds.run_terminal_command("start explorer")
                steps_log.append("Opened File Explorer")
            else:
                ds.open_target(app_name)
                steps_log.append(f"Attempted to open {app_name}")
            time.sleep(wait_seconds)
        else:
            steps_log.append(f"Focused existing window: {app_name}")
        
        # Step 2: Wait for app to be ready
        time.sleep(wait_seconds)
        
        # Step 3: Use visual grounding to find and click destination if it's a UI element
        if destination and not destination.startswith("http"):
            try:
                # Try ground_and_click for UI navigation
                ground_result = self.ground_and_click(destination)
                if "Found and clicked" in str(ground_result):
                    steps_log.append(f"Navigated to: {destination}")
                else:
                    steps_log.append(f"Could not find '{destination}' visually - may need manual navigation")
            except Exception as e:
                steps_log.append(f"Navigation attempt: {str(e)[:100]}")
        
        return f"NAVIGATE_APP completed: {' → '.join(steps_log)}"

    def open_app(self, app_name: str, wait_seconds: float = 1.5):
        """
        Quickly open an application by name. Uses direct CLI commands - faster than navigate_app.
        Prefer this for simply launching apps. Use navigate_app only when you need to go to a specific location.
        
        Args:
            app_name: Name of app to open (e.g., "Paint", "Notepad", "Chrome", "Calculator", "Settings")
            wait_seconds: How long to wait for app to load (default 1.5)
        
        Returns:
            Result of app launch
        """
        import time
        ds = get_desktop_service()
        
        # Map common app names to launch commands
        app_commands = {
            # Windows apps
            "paint": "mspaint",
            "notepad": "notepad",
            "calculator": "calc",
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "explorer": "explorer",
            "file explorer": "explorer",
            "cmd": "cmd",
            "powershell": "powershell",
            "terminal": "wt",
            "settings": "ms-settings:",
            "task manager": "taskmgr",
            "control panel": "control",
            "snipping tool": "snippingtool",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "outlook": "outlook",
            "vscode": "code",
            "visual studio code": "code",
            # Linux apps
            "gedit": "gedit",
            "nautilus": "nautilus",
            "files": "nautilus",
            "gimp": "gimp",
            "libreoffice": "libreoffice",
        }
        
        # Normalize app name
        app_lower = app_name.lower().strip()
        command = app_commands.get(app_lower, app_name)
        
        # Determine OS and build launch command
        import platform
        if platform.system() == "Windows":
            launch_cmd = f"Start-Process {command}"
        else:
            launch_cmd = f"{command} &"
        
        try:
            result = ds.run_terminal_command(launch_cmd)
            time.sleep(wait_seconds)
            return f"Launched {app_name} successfully"
        except Exception as e:
            return f"Failed to launch {app_name}: {str(e)}"

    def draw_shape(self, shape: str, x: float, y: float, width: float, height: float, app: str = "Paint"):
        """
        Draw a shape at specified position and size. Works with Paint and similar drawing apps.
        More efficient than multiple drag_mouse calls.
        
        Args:
            shape: Shape type - "rectangle", "oval", "line", "circle", "square"
            x: Top-left X coordinate
            y: Top-left Y coordinate  
            width: Width of shape (for line, this is horizontal distance)
            height: Height of shape (for line, this is vertical distance)
            app: Drawing application (default "Paint")
        
        Returns:
            Result of drawing operation
        """
        ds = get_desktop_service()
        
        # Calculate end coordinates
        end_x = x + width
        end_y = y + height
        
        # For circles/squares, make it even
        if shape.lower() == "circle":
            shape = "oval"
            height = width  # Force equal
            end_y = y + width
        elif shape.lower() == "square":
            shape = "rectangle"
            height = width
            end_y = y + width
        
        # Perform the drag operation to draw
        try:
            result = ds.drag_mouse(x, y, end_x, end_y)
            return f"Drew {shape} from ({x},{y}) to ({end_x},{end_y})"
        except Exception as e:
            return f"Failed to draw {shape}: {str(e)}"

    def interact_element(self, element_description: str, action: str = "click", text_to_type: str = None):
        """
        Find a UI element by description and perform an action on it.
        This is a macro-action that combines: visual grounding → action execution.
        
        Args:
            element_description: Natural language description of the element (e.g., "Submit button", "Email input field", "Settings menu")
            action: Action to perform - "click", "double_click", "right_click", "type", "hover"
            text_to_type: Text to type if action is "type"
        
        Returns:
            Result of the interaction
        """
        ds = get_desktop_service()
        
        # Use ground_and_click to find the element
        ground_result = self.ground_and_click(element_description)
        
        if "Could not find" in str(ground_result) or "error" in str(ground_result).lower():
            return f"Could not find element: {element_description}. Try a more specific description."
        
        # For type action, we've already clicked, now type
        if action == "type" and text_to_type:
            import time
            time.sleep(0.3)  # Brief pause after click
            type_result = ds.type_text(text_to_type)
            return f"Clicked '{element_description}' and typed: {text_to_type}"
        
        # For double_click, click again
        if action == "double_click":
            import time
            time.sleep(0.1)
            # Extract coordinates from ground_result if possible
            ground_result_str = str(ground_result)
            if "at (" in ground_result_str:
                try:
                    coords = ground_result_str.split("at (")[1].split(")")[0]
                    x, y = map(float, coords.split(","))
                    ds.click_at(int(x), int(y))
                    return f"Double-clicked '{element_description}'"
                except:
                    pass
        
        return ground_result

    def fill_form(self, fields: list):
        """
        Fill multiple form fields in sequence.
        This is a macro-action that combines: visual grounding → click → type for each field.
        
        Args:
            fields: List of dicts with 'label' and 'value' keys.
                    Example: [{"label": "Email", "value": "user@example.com"}, {"label": "Password", "value": "secret123"}]
        
        Returns:
            Summary of form filling results
        """
        import time
        results = []
        
        for field in fields:
            label = field.get("label", "")
            value = field.get("value", "")
            
            if not label or not value:
                results.append(f"Skipped invalid field: {field}")
                continue
            
            # Try to find and click the field
            try:
                field_result = self.interact_element(f"{label} input field", action="type", text_to_type=value)
                results.append(f"✓ {label}: filled")
                time.sleep(0.5)  # Brief pause between fields
            except Exception as e:
                results.append(f"✗ {label}: failed - {str(e)[:50]}")
        
        return f"FILL_FORM completed: {len([r for r in results if '✓' in r])}/{len(fields)} fields filled. Details: {'; '.join(results)}"

    def perform_workflow(self, workflow_name: str, steps: list):
        """
        Execute a named workflow with multiple steps.
        Each step can be a tool call with arguments.
        
        Args:
            workflow_name: Name for this workflow (for logging)
            steps: List of step dicts with 'action' and 'args' keys.
                   Example: [{"action": "focus_window", "args": {"title": "Chrome"}}, 
                            {"action": "type_text", "args": {"text": "hello"}}]
        
        Returns:
            Summary of workflow execution
        """
        import time
        results = []
        log_system(f"Starting workflow: {workflow_name} with {len(steps)} steps", "WORKFLOW")
        
        for i, step in enumerate(steps):
            action = step.get("action", "")
            args = step.get("args", {})
            wait = step.get("wait", 0.5)  # Default wait between steps
            
            if action not in self.tools_map:
                results.append(f"Step {i+1}: Unknown action '{action}'")
                continue
            
            try:
                func = self.tools_map[action]
                if asyncio.iscoroutinefunction(func):
                    import asyncio
                    result = asyncio.get_event_loop().run_until_complete(func(**args))
                else:
                    result = func(**args)
                results.append(f"Step {i+1} ({action}): OK")
                time.sleep(wait)
            except Exception as e:
                results.append(f"Step {i+1} ({action}): FAILED - {str(e)[:50]}")
                # Don't stop on failure, continue with remaining steps
        
        success_count = len([r for r in results if "OK" in r])
        return f"WORKFLOW '{workflow_name}' completed: {success_count}/{len(steps)} steps succeeded. {'; '.join(results)}"

    def render_attack_path(self, title: str, stages: list, annotations: dict = None):
        """
        Generate a Mermaid attack path diagram for forensic investigations.
        The diagram will be automatically rendered in the chat UI.
        
        Args:
            title: Title for the attack path (e.g., "Cryptominer Infection Chain")
            stages: List of attack stages in order. Each stage is a dict with:
                    - id: Short identifier (e.g., "RCE", "PERSIST", "C2")
                    - label: Description of the stage
                    - type: Optional - "entry", "execution", "persistence", "c2", "impact"
            annotations: Optional dict mapping stage IDs to evidence counts or notes
        
        Returns:
            Mermaid diagram code that will render in the UI
        
        Example:
            render_attack_path(
                title="Attack Chain",
                stages=[
                    {"id": "RCE", "label": "Next.js Server Action RCE", "type": "entry"},
                    {"id": "DROP", "label": "Payload dropped to /tmp", "type": "execution"},
                    {"id": "PERSIST", "label": "Systemd service installed", "type": "persistence"},
                    {"id": "C2", "label": "Fake PostgreSQL on 5432", "type": "c2"}
                ],
                annotations={"RCE": "4 log lines", "PERSIST": "2 files"}
            )
        """
        # Build Mermaid flowchart
        lines = ["```mermaid", "flowchart TD"]
        lines.append(f"    title[{title}]")
        lines.append("    style title fill:#1a1a2e,stroke:#6366f1,color:#fff")
        
        # Node type styles
        type_styles = {
            "entry": "fill:#dc2626,stroke:#991b1b,color:#fff",      # Red
            "execution": "fill:#f59e0b,stroke:#b45309,color:#000",   # Orange
            "persistence": "fill:#8b5cf6,stroke:#6d28d9,color:#fff", # Purple
            "c2": "fill:#06b6d4,stroke:#0891b2,color:#000",          # Cyan
            "impact": "fill:#ef4444,stroke:#b91c1c,color:#fff",      # Dark red
            "default": "fill:#6366f1,stroke:#4f46e5,color:#fff"      # Indigo
        }
        
        prev_id = "title"
        for i, stage in enumerate(stages):
            stage_id = stage.get("id", f"S{i}")
            label = stage.get("label", stage_id)
            stage_type = stage.get("type", "default")
            
            # Add annotation if present
            if annotations and stage_id in annotations:
                label = f"{label}<br/><small>📎 {annotations[stage_id]}</small>"
            
            # Define node
            lines.append(f"    {stage_id}[{label}]")
            
            # Apply style based on type
            style = type_styles.get(stage_type, type_styles["default"])
            lines.append(f"    style {stage_id} {style}")
            
            # Connect to previous
            if prev_id != "title":
                lines.append(f"    {prev_id} --> {stage_id}")
            else:
                lines.append(f"    {prev_id} -.-> {stage_id}")
            
            prev_id = stage_id
        
        lines.append("```")
        
        diagram = "\n".join(lines)
        log_system(f"Generated attack path diagram: {title} with {len(stages)} stages", "DIAGRAM")
        
        return f"ATTACK_PATH_DIAGRAM:\n{diagram}\n\nThis diagram will render automatically in the chat. Use it to explain the attack chain to the user."

    # ============ EVIDENCE ON DEMAND ============
    # Pattern: Present claims first, fetch artifacts when user asks
    
    def store_evidence(self, claim: str, evidence_type: str, data: str, confidence: str = "high"):
        """
        Store evidence to support a claim. The evidence can be retrieved later when user asks.
        Use this to build an evidence-backed investigation without overwhelming the user with details.
        
        Args:
            claim: The claim this evidence supports (e.g., "Attacker used RCE via Next.js")
            evidence_type: Type of evidence - "log", "file", "process", "network", "screenshot", "config"
            data: The actual evidence data (log lines, file contents, command output, etc.)
            confidence: "high", "medium", or "low"
        
        Returns:
            Evidence ID that can be referenced later
        """
        import time
        import hashlib
        
        # Generate short evidence ID
        evidence_id = hashlib.md5(f"{claim}{time.time()}".encode()).hexdigest()[:8]
        
        self.evidence_store[evidence_id] = {
            "claim": claim,
            "evidence_type": evidence_type,
            "data": data[:5000],  # Limit data size
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        log_system(f"Evidence stored: {evidence_id} for claim: {claim[:50]}...", "EVIDENCE")
        return f"📎 Evidence #{evidence_id} stored for: {claim} (Type: {evidence_type}, Confidence: {confidence})"

    def get_evidence(self, evidence_id: str):
        """
        Retrieve stored evidence by ID. Use when user asks "show me proof" or "what's the evidence".
        
        Args:
            evidence_id: The evidence ID returned by store_evidence
        
        Returns:
            The full evidence details including raw data
        """
        if evidence_id not in self.evidence_store:
            return f"Evidence #{evidence_id} not found. Use list_evidence to see available evidence."
        
        evidence = self.evidence_store[evidence_id]
        return f"""📎 EVIDENCE #{evidence_id}
**Claim:** {evidence['claim']}
**Type:** {evidence['evidence_type']}
**Confidence:** {evidence['confidence']}

**Raw Data:**
```
{evidence['data']}
```"""

    def list_evidence(self):
        """
        List all stored evidence with their IDs and claims.
        Use this to show the user what evidence is available.
        
        Returns:
            Summary of all stored evidence
        """
        if not self.evidence_store:
            return "No evidence stored yet. Use store_evidence during investigation to build an evidence trail."
        
        lines = ["📋 **Available Evidence:**\n"]
        for eid, ev in self.evidence_store.items():
            lines.append(f"- **#{eid}** ({ev['evidence_type']}, {ev['confidence']}): {ev['claim'][:60]}...")
        
        lines.append(f"\nTotal: {len(self.evidence_store)} items. Say 'show evidence #ID' to view details.")
        return "\n".join(lines)

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

    async def _send_with_retry(self, chat, content, retries=2, timeout_seconds=90):
        """Send message with retry on transient errors (500, MALFORMED_FUNCTION_CALL)"""
        for attempt in range(retries + 1):
            try:
                # Add timeout to detect silent Gemini hangs
                return await asyncio.wait_for(
                    asyncio.to_thread(chat.send_message, content),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                log_system(f"Gemini API timeout after {timeout_seconds}s", "TIMEOUT")
                raise Exception(f"Model response timed out after {timeout_seconds}s. The model may be overloaded. Please try again.")
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
    async def route_and_execute_stream(self, message: str, complexity_request: str = "balanced", session_id: str = None):
        """
        Main orchestrator for processing user requests.
        
        Args:
            message: User's request
            complexity_request: Execution mode - "quick", "balanced", or "thorough"
                              (legacy "fast"/"deep" mapped to balanced/thorough)
            session_id: Session identifier for conversation continuity
        """
        # Map legacy complexity values to new modes
        mode_mapping = {"fast": "balanced", "deep": "thorough"}
        mode = mode_mapping.get(complexity_request, complexity_request)
        if mode not in self.MODE_CONFIGS:
            mode = "balanced"
        
        mode_config = self.MODE_CONFIGS[mode]
        log_system(f"NEW REQUEST: {message} (Mode: {mode}, Session: {session_id})", "ROUTER")
        
        # Clear any previous cancellation flag for this session (allows new requests after Stop)
        self.cancelled_sessions.discard(session_id)
        
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
        
        # Get or create session history - limit based on config to prevent stale command re-execution
        history_size = GeminiService.MODE_CONFIGS.get("session_history_size", 6)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            log_system(f"New session created: {session_id}", "SESSION")
        else:
            # Trim old history to prevent model from re-executing old commands
            if len(self.sessions[session_id]) > history_size:
                self.sessions[session_id] = self.sessions[session_id][-history_size:]
                log_system(f"Trimmed session history to last {history_size} messages", "SESSION")
            log_system(f"Continuing session: {session_id} with {len(self.sessions[session_id])} messages", "SESSION")

        if not self.api_key:
            yield json.dumps({"type": "error", "content": "API Key Missing"})
            return

        # Tool declarations
        tools = list(self.tools_map.values())
        log_system(f"Tools loaded: {len(tools)} functions", "ROUTER")

        # Model selection based on mode config
        model_name = self.SMART_TEXT_MODEL if mode_config["model"] == "pro" else self.FAST_TEXT_MODEL
        max_turns = mode_config["max_turns"]
        max_tool_calls = mode_config.get("max_tool_calls", 20)
        mode_timeout = mode_config.get("timeout", 60)
        verify_mode = mode_config["verify"]
        prompt_suffix = mode_config["prompt_suffix"]
        log_system(f"Using model: {model_name} (mode: {mode}, max_turns: {max_turns}, max_tools: {max_tool_calls}, timeout: {mode_timeout}s)", "ROUTER")

        # Get active agent's OS context and name
        agent_os, shell_type = self._get_active_agent_os()
        agent_name = self._get_active_agent_name()
        log_system(f"Active agent OS: {agent_os}, Shell: {shell_type}", "ROUTER")
        
        # Check for agent switch and emit notification
        previous_agent = self.session_agents.get(session_id)
        if previous_agent != agent_name:
            if previous_agent is None:
                # First message in session - show current agent
                switch_msg = f"🖥️ Connected to: **{agent_name}** ({agent_os})"
                log_system(f"Session {session_id} started on agent: {agent_name}", "AGENT")
            else:
                # Agent switched mid-session
                switch_msg = f"🔄 Switched to: **{agent_name}** ({agent_os})"
                log_system(f"Session {session_id} switched from {previous_agent} to {agent_name}", "AGENT")
            
            # Update tracking
            self.session_agents[session_id] = agent_name
            
            # Emit notification to chat
            yield json.dumps({"type": "agent_switch", "agent": agent_name, "os": agent_os, "content": switch_msg}) + "\n"
            
            # Save to session history so LLM knows about the switch
            self.sessions[session_id].append({"role": "user", "parts": [f"[System: {switch_msg}]"]})

        # System instruction for transparency - dynamic OS context
        system_instruction = f"""You are Proxi, a Headless Operator with FULL OS-level access on this {agent_os} computer.

EXPERTISE: You are an IT systems administrator and desktop automation specialist with deep knowledge of:
- Windows: PowerShell, Registry, Services, Event Viewer, Task Manager, Group Policy
- Linux: Bash, systemd, journalctl, top/htop, networking (netstat, ss, iptables)
- Security: Log analysis, process forensics, malware identification, incident response
- Automation: Desktop GUI control, file management, application scripting

IMPORTANT: You are connected to a {agent_os} system. Use {shell_type} for commands.
{"" if agent_os != "Windows" else '''
WINDOWS EFFICIENCY: Always prefer CLI/PowerShell commands over visual grounding:
- Settings: Use "start ms-settings:network", "start ms-settings:display", etc.
- Apps: Use "start notepad", "start chrome", "start explorer C:\\path"
- System info: Use Get-Process, Get-Service, Get-NetAdapter, systeminfo
- Only use look_at_screen/ground_and_click when CLI cannot achieve the goal (e.g., clicking specific UI buttons)
'''}

=== EXECUTION CONSTRAINTS ({mode.upper()} MODE) ===
- Maximum tool calls: {max_tool_calls}
- Timeout per request: {mode_timeout}s
- If your task requires more than {max_tool_calls} tool calls, inform the user early and suggest using a higher mode (Balanced or Thorough).
- Plan your investigation to fit within these limits. Prioritize the most diagnostic commands first.
{f"- {prompt_suffix}" if prompt_suffix else ""}

YOU HAVE ACCESS TO THESE CAPABILITIES - USE THEM:
- run_terminal_command: Execute PowerShell commands (dir, ls, Get-Process, etc.)
- look_at_screen: Take screenshot with Set-of-Mark overlay showing numbered [N] UI elements
- ground_and_click: BEST FOR GUI - finds and clicks UI elements by description (uses local Gemini on agent)
- share_screenshot: Take screenshot and SHOW it to the user in the chat UI
- save_uploaded_image: Save an image the user uploaded to a file path (e.g. Desktop)
- open_target: Open files, folders, URLs, or applications
- click_at, type_text, press_hotkey: Control mouse and keyboard (use coordinates from look_at_screen)
- ppt_* tools: Edit PowerPoint presentations
- get_system_health: Check CPU, memory, disk usage

MACRO-ACTIONS (preferred for efficiency):
- open_app(app_name): FASTEST way to launch apps (Paint, Notepad, Chrome, Settings, etc.) - uses CLI directly
- draw_shape(shape, x, y, width, height): Draw rectangle/oval/line at position - use with Paint instead of drag_mouse
- navigate_app(app_name, destination): Open app AND navigate to specific location in ONE call
- interact_element(description, action, text): Find element and click/type in ONE call  
- fill_form(fields): Fill multiple form fields in sequence
- perform_workflow(name, steps): Execute multi-step workflows smoothly

FOR FORENSIC/SECURITY INVESTIGATIONS:
- render_attack_path(title, stages, annotations): Generate visual attack chain diagram
  Use this after completing an investigation to show the user a clear attack timeline.
  The diagram renders automatically in the chat with color-coded stages (entry→execution→persistence→c2).

EVIDENCE ON DEMAND PATTERN (for audit-grade investigations):
- store_evidence(claim, type, data): Store evidence as you find it (don't dump everything to user)
- list_evidence(): Show user what evidence is available  
- get_evidence(id): Retrieve specific evidence when user asks "show me proof"
Best practice: Present CLAIMS first (brief verdicts), let user request details. This keeps mobile UI clean.

FOR GUI INTERACTIONS (buttons, links, forms):
1. PREFERRED: Use ground_and_click("Submit button") - automatically finds and clicks elements
2. ALTERNATIVE: Use look_at_screen first to see numbered [N] elements, then click_at(x, y) using coordinates

TO LIST FILES ON DESKTOP, use: run_terminal_command with "dir $env:USERPROFILE\\Desktop" or "ls ~/Desktop"
TO OPEN AN IMAGE, use: open_target with the image path
TO SEE THE SCREEN (for your analysis), use: look_at_screen - shows numbered elements [N] you can reference
TO CLICK A UI ELEMENT, use: ground_and_click("element description") - finds and clicks automatically
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

**Process:** ffmpeg
**PID:** 1337
**Usage:** 95% CPU, 45% Memory
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

3. BUILD PHASE (use COM automation for speed):
   - ppt_duplicate_slide() to clone a well-designed reference slide
   - ppt_edit_text() to replace content while preserving formatting
   - ppt_add_shape() for visual elements (arrows, callouts)
   - ppt_add_picture() to insert local images
   - ppt_move_shape() and ppt_resize_shape() for layout adjustments
   
   DATA & TABLES:
   - ppt_add_table(slide, rows, cols, data) - Add formatted data tables with headers
   - ppt_add_chart(slide, "column"|"bar"|"pie"|"line", data, title) - Data visualization charts
   
   VISUAL ELEMENTS:
   - ppt_add_image_from_url(slide, url, left, top, width) - Download & insert web images
   - ppt_add_icon(slide, "star"|"arrow_right"|"gear"|"heart"|"cloud", left, top, size, color) - Built-in icons
   - ppt_insert_smartart(slide, "process"|"hierarchy"|"list", items) - Process flows & org charts
   - ppt_add_textbox(slide, text, left, top) - Custom positioned text boxes
   - ppt_set_shape_style(slide, shape, fill_color, line_color) - Style shapes with brand colors
   
   MACRO-ACTIONS:
   - ppt_create_business_slide(slide, title, points) - Create executive summary slides in ONE call

4. VERIFY PHASE (use visual inspection):
   - ppt_goto_slide() and look_at_screen() to VISUALLY verify the result
   - Check that charts, images, icons rendered correctly
   - Ensure consistency with original theme
   - ppt_save_presentation() when complete

HYBRID APPROACH: Use COM automation for fast bulk edits, then look_at_screen() to visually confirm results.
For complex layouts, alternate between COM tools and visual inspection to ensure accuracy.

IMPORTANT: Duplicate existing slides rather than creating blank ones - this preserves theme formatting perfectly."""

        yield json.dumps({"type": "status_change", "phase": "planning", "content": f"Initializing ({complexity_request} mode)..."}) + "\n"

        current_mission_id = None
        current_criteria = None

        accumulated_content = []  # Track all model responses for session recovery (init before try)
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
            # Detect voice modes: explain, investigate, prove, summarize
            msg_lower = message.strip().lower()
            voice_mode = None
            voice_mode_prefix = ""
            
            # Check for voice mode triggers
            if msg_lower.startswith("explain ") or msg_lower == "explain" or "explain why" in msg_lower or "explain this" in msg_lower:
                voice_mode = "explain"
                voice_mode_prefix = "MODE: EXPLAIN - Provide a clear, concise explanation. Focus on the 'why' and use simple language. No new actions needed.\n\n"
                log_system("Voice mode: EXPLAIN", "MODE")
            elif msg_lower.startswith("investigate ") or msg_lower == "investigate" or "look into" in msg_lower:
                voice_mode = "investigate"
                voice_mode_prefix = "MODE: INVESTIGATE - Dig deeper into this. Use available tools to gather evidence. Be thorough but focused.\n\n"
                log_system("Voice mode: INVESTIGATE", "MODE")
            elif msg_lower.startswith("prove ") or "prove it" in msg_lower or "show me proof" in msg_lower or "show evidence" in msg_lower:
                voice_mode = "prove"
                voice_mode_prefix = "MODE: PROVE - Provide concrete evidence for your claims. Show specific logs, files, or screenshots. Each assertion must have supporting data.\n\n"
                log_system("Voice mode: PROVE", "MODE")
            elif msg_lower.startswith("summarize") or "give me a summary" in msg_lower or "tldr" in msg_lower:
                voice_mode = "summarize"
                voice_mode_prefix = "MODE: SUMMARIZE - Provide a brief, bullet-point summary. Key findings only. No new actions.\n\n"
                log_system("Voice mode: SUMMARIZE", "MODE")
            
            # Inject current OS context into EVERY message (handles mid-session agent switches)
            os_context_prefix = f"[CURRENT AGENT: {agent_os} - use {shell_type}] "
            
            if len(history) > 0:
                # This is a follow-up message
                # Detect "continue" requests and add context to resume, not restart
                if msg_lower in ("continue", "go on", "proceed", "keep going", "please continue", "continue where you left off", "please continue where you left off"):
                    user_message = os_context_prefix + "CONTINUE: Resume exactly where you left off. Do NOT restart analysis or create a new plan. Continue from your last action/thought and complete the remaining goals. Do NOT call get_system_health or other tools you already called."
                    log_system(f"Continue request detected - instructing LLM to resume", "SESSION")
                else:
                    user_message = os_context_prefix + voice_mode_prefix + message
                    log_system(f"Follow-up message in session: {message}", "SESSION")
            else:
                # New conversation - prefix with GOAL
                user_message = os_context_prefix + voice_mode_prefix + f"GOAL: {message}"
            
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
            response = await self._send_with_retry(chat, message_content, timeout_seconds=mode_timeout)
            log_system(f"Response received from model", "MODEL")
            
            # Update session history with user message
            self.sessions[session_id].append({"role": "user", "parts": [user_message]})

            # Tracking variables
            last_activity_had_response = False  # Track if we got a proper response
            total_tool_calls = 0  # Track total tool executions across all turns
            
            for turn in range(max_turns):
                # Check for cancellation at start of each turn
                if session_id in self.cancelled_sessions:
                    self.cancelled_sessions.discard(session_id)
                    log_system(f"Session {session_id} cancelled by user", "CANCEL")
                    yield json.dumps({"type": "cancelled", "content": "Mission stopped by user"}) + "\n"
                    return
                
                # Extract parts safely - detect stalls
                if not response.candidates or not response.candidates[0].content.parts:
                    if not last_activity_had_response:
                        log_system(f"Model returned empty response on turn {turn}", "STALL")
                        yield json.dumps({"type": "stalled", "content": "The model stopped responding. You can send a follow-up message to continue."}) + "\n"
                    break
                
                last_activity_had_response = False  # Reset for this turn
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
                    accumulated_content.append(text_content)  # Track for session recovery
                    msg_type = "llm_thought" if function_calls else "final_response"
                    log_system(f"LLM: {text_content[:100]}...", "THOUGHT" if function_calls else "RESPONSE")
                    yield json.dumps({"type": msg_type, "content": text_content}) + "\n"
                    if not function_calls:
                        last_activity_had_response = True  # Got a final text response
                    
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
                    # Check for cancellation before each tool execution
                    if session_id in self.cancelled_sessions:
                        self.cancelled_sessions.discard(session_id)
                        log_system(f"Session {session_id} cancelled during tool execution", "CANCEL")
                        yield json.dumps({"type": "cancelled", "content": "Mission stopped by user"}) + "\n"
                        return
                    
                    # Enforce max_tool_calls limit
                    total_tool_calls += 1
                    if total_tool_calls > max_tool_calls:
                        log_system(f"Tool call limit reached ({max_tool_calls}) for mode {mode}", "LIMIT")
                        yield json.dumps({"type": "llm_thought", "content": f"I've reached the tool execution limit for {mode} mode ({max_tool_calls} calls). Summarizing findings..."}) + "\n"
                        # Force model to summarize by breaking out
                        break
                    
                    name = call_info['name']
                    args = call_info['args']
                    
                    yield json.dumps({"type": "status_change", "phase": "executing", "tool": name}) + "\n"
                    log_system(f"TOOL_CALL: {name}({args}) [{total_tool_calls}/{max_tool_calls}]", "EXEC")

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
                            res = f"VERIFICATION FAILED: {judgment.get('reason')}. Consider retrying the action or trying an alternative approach."
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
                    
                    # Handle file transfer specially
                    res_str = str(res)
                    if res_str.startswith("__FILE__:"):
                        log_system("File marker detected, sending to UI", "FILE")
                        # Format: __FILE__:filename:mime_type:base64_content:__DESC__:description
                        parts = res_str.split(":__DESC__:")
                        file_parts = parts[0].replace("__FILE__:", "").split(":", 2)
                        filename = file_parts[0] if len(file_parts) > 0 else "file"
                        mime_type = file_parts[1] if len(file_parts) > 1 else "application/octet-stream"
                        content_b64 = file_parts[2] if len(file_parts) > 2 else ""
                        description = parts[1] if len(parts) > 1 else filename
                        log_system(f"File data: {filename} ({mime_type}), {len(content_b64)} chars", "FILE")
                        yield json.dumps({
                            "type": "file_download",
                            "filename": filename,
                            "mime_type": mime_type,
                            "content_base64": content_b64,
                            "description": description
                        }) + "\n"
                        res = f"File sent to user: {filename}"
                    
                    # Check for approval required
                    res_str = str(res)
                    if res_str.startswith("APPROVAL_REQUIRED:"):
                        # Parse: "APPROVAL_REQUIRED:approval_id:reason. Command: cmd. Should I proceed?"
                        import re
                        # Split only on first 2 colons to get [APPROVAL_REQUIRED, approval_id, rest]
                        parts = res_str.split(":", 2)
                        if len(parts) >= 3:
                            approval_id = parts[1]
                            rest = parts[2]  # "reason. Command: cmd. Should I proceed?"
                            # Extract command - handle colon in "Command:"
                            cmd_match = re.search(r'Command:\s*(.+?)\.\s*Should', rest)
                            command = cmd_match.group(1).strip() if cmd_match else "Unknown command"
                            # Extract reason (text before ". Command:")
                            reason_match = re.search(r'^(.+?)\.\s*Command:', rest)
                            reason = reason_match.group(1).strip() if reason_match else "Command requires approval"
                            yield json.dumps({"type": "approval_required", "approval_id": approval_id, "reason": reason, "command": command, "risk_level": "moderate"}) + "\n"
                    
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

                # Check if we hit tool limit and need to break outer loop too
                if total_tool_calls > max_tool_calls:
                    break
                
                # Save model's text content to session history for "continue" to work
                # NOTE: Do NOT save tool call syntax to history - the model will mimic it as text!
                # Instead, save a natural language summary of actions taken
                if text_content:
                    self.sessions[session_id].append({"role": "model", "parts": [text_content]})
                
                # Save tool execution summaries as context (not tool call syntax!)
                action_summaries = []
                for i, call_info in enumerate(safe_calls):
                    result_preview = str(response_parts[i])[:150] if i < len(response_parts) else "executed"
                    action_summaries.append(f"• Executed {call_info['name']}: {result_preview}")
                if action_summaries:
                    summary_text = "Actions completed:\n" + "\n".join(action_summaries)
                    self.sessions[session_id].append({"role": "user", "parts": [f"[System: {summary_text}]"]})
                    
                # Send results back
                response = await self._send_with_retry(chat, response_parts, timeout_seconds=mode_timeout)

            # Ensure we always yield a final response if model only returned tools
            if accumulated_content and not last_activity_had_response:
                # Model finished with tools but no final text - generate completion message
                summary = f"✅ Completed {total_tool_calls} actions successfully."
                yield json.dumps({"type": "final_response", "content": summary}) + "\n"
                log_system(f"Generated completion summary after {total_tool_calls} tool calls", "RESPONSE")
            
            yield json.dumps({"type": "status_change", "phase": "idle"}) + "\n"

        except Exception as e:
            log_system(f"HIVE ERROR: {e}", "ERR")
            # Save partial content to session history for recovery on continue
            if accumulated_content:
                partial_response = "\n".join(accumulated_content[-3:])  # Last 3 responses
                self.sessions[session_id].append({"role": "model", "parts": [partial_response]})
                log_system(f"Saved partial response ({len(accumulated_content)} items) to session for recovery", "SESSION")
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
