"""
Null Desktop Service - Returns error when no agent is selected.

Used by Core when no remote agent is active. Prevents Core from
executing tools locally (security isolation).
"""

from backend.services.desktop.interface import DesktopInterface


class NullDesktopService(DesktopInterface):
    """
    DesktopService that rejects all operations.
    Used when no agent is selected.
    """
    
    ERROR_MSG = "No agent selected. Please select a Proxi Agent from the dropdown before executing commands."
    
    def get_system_health(self) -> dict:
        return {"error": self.ERROR_MSG, "status": "no_agent"}
    
    def click_at(self, x: int, y: int) -> dict:
        return {"error": self.ERROR_MSG}
    
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
        return {"error": self.ERROR_MSG}
    
    def type_text(self, text: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def press_hotkey(self, keys: list) -> dict:
        return {"error": self.ERROR_MSG}
    
    def wait_seconds(self, seconds: int) -> dict:
        return {"error": self.ERROR_MSG}
    
    def run_terminal_command(self, command: str) -> str:
        return f"ERROR: {self.ERROR_MSG}"
    
    def open_target(self, resource: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def read_page_content(self) -> dict:
        return {"error": self.ERROR_MSG}
    
    def scroll_page(self, direction: str = "down") -> dict:
        return {"error": self.ERROR_MSG}
    
    def browser_command(self, action: str, url: str = None) -> dict:
        return {"error": self.ERROR_MSG}
    
    def scan_ui_tree(self) -> dict:
        return {"error": self.ERROR_MSG}
    
    def get_screenshot_base64(self) -> str:
        return None
    
    def focus_window(self, title: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def get_window_rect(self, title: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def list_windows(self) -> list:
        return []
