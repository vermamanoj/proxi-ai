"""
Linux Desktop Service for Proxi Agents

Provides terminal and file operations for Linux containers/servers.
Does NOT provide GUI operations (no mouse, keyboard, screenshots).
"""

import subprocess
import os
import psutil
from pathlib import Path
from .interface import DesktopInterface


class LinuxDesktopService(DesktopInterface):
    """
    Desktop service for Linux environments (containers, servers).
    Supports terminal commands and file operations only.
    """
    
    def __init__(self):
        self.working_dir = os.getcwd()
    
    def get_system_health(self):
        """Returns system metrics (CPU, Memory, etc)."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "platform": "linux",
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "container"
        }
    
    def run_terminal_command(self, command: str):
        """Execute a terminal command and return output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.working_dir
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return {
                "success": result.returncode == 0,
                "output": output.strip(),
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "Command timed out (60s)", "return_code": -1}
        except Exception as e:
            return {"success": False, "output": str(e), "return_code": -1}
    
    def open_target(self, resource: str):
        """Open a file or URL - limited on headless Linux."""
        if resource.startswith(('http://', 'https://')):
            return {"status": "info", "message": f"URL noted: {resource} (no browser in container)"}
        
        path = Path(resource)
        if path.exists():
            if path.is_file():
                with open(path, 'r') as f:
                    content = f.read(4000)  # First 4KB
                return {"status": "success", "content": content, "path": str(path)}
            else:
                return {"status": "success", "message": f"Directory exists: {path}"}
        return {"status": "error", "message": f"Path not found: {resource}"}
    
    def read_page_content(self):
        """Not applicable for headless Linux."""
        return {"status": "not_available", "message": "No browser in container"}
    
    def scroll_page(self, direction: str):
        """Not applicable for headless Linux."""
        return {"status": "not_available", "message": "No GUI in container"}
    
    def scan_ui_tree(self):
        """Not applicable for headless Linux."""
        return {"status": "not_available", "message": "No GUI in container"}
    
    def get_screenshot_base64(self):
        """Not applicable for headless Linux."""
        return {"status": "not_available", "message": "No display in container"}
    
    def get_observation(self, include_som: bool = True):
        """Not applicable for headless Linux."""
        return {"status": "not_available", "message": "No GUI in container"}
    
    # GUI operations - not available on headless Linux
    def click_at(self, x: int, y: int):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def type_text(self, text: str):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def press_hotkey(self, keys: list[str]):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def wait_seconds(self, seconds: int):
        """Wait for specified seconds."""
        import time
        time.sleep(seconds)
        return {"status": "success", "message": f"Waited {seconds} seconds"}
    
    def browser_command(self, action: str, url: str = None):
        return {"status": "not_available", "message": "No browser in container"}
    
    def focus_window(self, title: str):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def get_window_rect(self, title: str):
        return {"status": "not_available", "message": "No GUI in container"}
    
    def list_windows(self):
        return {"status": "not_available", "message": "No GUI in container"}

    # --- PowerPoint Tools (not available on Linux) ---
    def ppt_get_active_presentation(self):
        return "Error: PowerPoint not available on Linux"

    def ppt_open_presentation(self, file_path: str):
        return "Error: PowerPoint not available on Linux"

    def ppt_get_slide_info(self, slide_number: int = 0):
        return "Error: PowerPoint not available on Linux"

    def ppt_edit_text(self, slide_number: int, shape_name: str, new_text: str):
        return "Error: PowerPoint not available on Linux"

    def ppt_add_slide(self, after_slide: int = 0, layout: str = "title_content"):
        return "Error: PowerPoint not available on Linux"

    def ppt_duplicate_slide(self, slide_number: int):
        return "Error: PowerPoint not available on Linux"

    def ppt_delete_slide(self, slide_number: int):
        return "Error: PowerPoint not available on Linux"

    def ppt_save_presentation(self, save_as_path: str = None):
        return "Error: PowerPoint not available on Linux"

    def ppt_goto_slide(self, slide_number: int):
        return "Error: PowerPoint not available on Linux"

    def ppt_add_picture(self, slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400):
        return "Error: PowerPoint not available on Linux"

    def ppt_add_shape(self, slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = ""):
        return "Error: PowerPoint not available on Linux"

    def ppt_move_shape(self, slide_number: int, shape_name: str, left: int, top: int):
        return "Error: PowerPoint not available on Linux"

    def ppt_resize_shape(self, slide_number: int, shape_name: str, width: int, height: int):
        return "Error: PowerPoint not available on Linux"

    def ppt_format_text(self, slide_number: int, shape_name: str, bold: bool = None, italic: bool = None, font_size: int = None, font_color: str = None):
        return "Error: PowerPoint not available on Linux"

    def ppt_get_theme_colors(self, slide_number: int = 1):
        return "Error: PowerPoint not available on Linux"
