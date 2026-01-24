
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
    def press_hotkey(self, keys: list):
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
        pass
