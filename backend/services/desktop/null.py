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
    
    def get_observation(self, include_som: bool = True) -> dict:
        return {"error": self.ERROR_MSG}
    
    def focus_window(self, title: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def get_window_rect(self, title: str) -> dict:
        return {"error": self.ERROR_MSG}
    
    def list_windows(self) -> list:
        return []

    # --- PowerPoint Tools ---
    def ppt_get_active_presentation(self) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_open_presentation(self, file_path: str) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_get_slide_info(self, slide_number: int = 0) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_edit_text(self, slide_number: int, shape_name: str, new_text: str) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_add_slide(self, after_slide: int = 0, layout: str = "title_content") -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_duplicate_slide(self, slide_number: int) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_delete_slide(self, slide_number: int) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_save_presentation(self, save_as_path: str = None) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_goto_slide(self, slide_number: int) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_add_picture(self, slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_add_shape(self, slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = "") -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_move_shape(self, slide_number: int, shape_name: str, left: int, top: int) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_resize_shape(self, slide_number: int, shape_name: str, width: int, height: int) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_format_text(self, slide_number: int, shape_name: str, bold: bool = None, italic: bool = None, font_size: int = None, font_color: str = None) -> str:
        return f"Error: {self.ERROR_MSG}"

    def ppt_get_theme_colors(self, slide_number: int = 1) -> str:
        return f"Error: {self.ERROR_MSG}"
    
    def ppt_add_table(self, slide_number: int, rows: int, cols: int, data: list, left: int = 50, top: int = 150, width: int = 600) -> str:
        return f"Error: {self.ERROR_MSG}"
    
    def ppt_set_shape_style(self, slide_number: int, shape_name: str, fill_color: str = None, line_color: str = None, line_weight: float = None, transparency: float = None) -> str:
        return f"Error: {self.ERROR_MSG}"
    
    def ppt_add_textbox(self, slide_number: int, text: str, left: int, top: int, width: int = 300, height: int = 50, font_size: int = None, font_color: str = None, bold: bool = False, align: str = "left") -> str:
        return f"Error: {self.ERROR_MSG}"
    
    def ppt_create_business_slide(self, slide_number: int, title: str, points: list, highlight_point: int = None) -> str:
        return f"Error: {self.ERROR_MSG}"
