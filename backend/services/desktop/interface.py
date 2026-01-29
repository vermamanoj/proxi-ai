
from abc import ABC, abstractmethod

class DesktopInterface(ABC):
    @abstractmethod
    def get_system_health(self):
        """Returns system metrics (CPU, Memory, etc)."""
        pass

    @abstractmethod
    def click_at(self, x: int, y: int):
        pass

    @abstractmethod
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        pass

    @abstractmethod
    def type_text(self, text: str):
        pass

    @abstractmethod
    def press_hotkey(self, keys: list[str]):
        pass

    @abstractmethod
    def wait_seconds(self, seconds: int):
        pass

    @abstractmethod
    def run_terminal_command(self, command: str):
        pass

    @abstractmethod
    def open_target(self, resource: str):
        pass

    @abstractmethod
    def read_page_content(self):
        pass

    @abstractmethod
    def scroll_page(self, direction: str):
        pass

    @abstractmethod
    def scan_ui_tree(self):
        pass

    @abstractmethod
    def get_screenshot_base64(self):
        pass

    @abstractmethod
    def browser_command(self, action: str, url: str = None):
        """
        Executes a semantic browser action using hotkeys.
        action: NEW_TAB, CLOSE_TAB, REFRESH, NAVIGATE, SEARCH
        url: Optional URL or Query string
        """
        pass

    @abstractmethod
    def focus_window(self, title: str):
        """Bring a window to foreground by title (partial match)."""
        pass

    @abstractmethod
    def get_window_rect(self, title: str):
        """Get window position and size: {x, y, width, height}."""
        pass

    @abstractmethod
    def list_windows(self):
        """List all visible windows with their titles."""
        pass

    # --- PowerPoint Tools ---
    @abstractmethod
    def ppt_get_active_presentation(self):
        """Gets info about the currently active PowerPoint presentation."""
        pass

    @abstractmethod
    def ppt_open_presentation(self, file_path: str):
        """Opens a PowerPoint presentation file."""
        pass

    @abstractmethod
    def ppt_get_slide_info(self, slide_number: int = 0):
        """Gets information about a specific slide or all slides."""
        pass

    @abstractmethod
    def ppt_edit_text(self, slide_number: int, shape_name: str, new_text: str):
        """Edits text in a specific shape on a slide."""
        pass

    @abstractmethod
    def ppt_add_slide(self, after_slide: int = 0, layout: str = "title_content"):
        """Adds a new slide to the presentation."""
        pass

    @abstractmethod
    def ppt_duplicate_slide(self, slide_number: int):
        """Duplicates an existing slide."""
        pass

    @abstractmethod
    def ppt_delete_slide(self, slide_number: int):
        """Deletes a slide from the presentation."""
        pass

    @abstractmethod
    def ppt_save_presentation(self, save_as_path: str = None):
        """Saves the current presentation."""
        pass

    @abstractmethod
    def ppt_goto_slide(self, slide_number: int):
        """Navigates to a specific slide."""
        pass

    @abstractmethod
    def ppt_add_picture(self, slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400):
        """Adds a picture to a slide."""
        pass

    @abstractmethod
    def ppt_add_shape(self, slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = ""):
        """Adds a shape to a slide."""
        pass

    @abstractmethod
    def ppt_move_shape(self, slide_number: int, shape_name: str, left: int, top: int):
        """Moves a shape on a slide."""
        pass

    @abstractmethod
    def ppt_resize_shape(self, slide_number: int, shape_name: str, width: int, height: int):
        """Resizes a shape on a slide."""
        pass

    @abstractmethod
    def ppt_format_text(self, slide_number: int, shape_name: str, bold: bool = None, italic: bool = None, font_size: int = None, font_color: str = None):
        """Formats text in a shape."""
        pass

    @abstractmethod
    def ppt_get_theme_colors(self, slide_number: int = 1):
        """Extracts theme colors from the presentation."""
        pass
