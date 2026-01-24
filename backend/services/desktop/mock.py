
import json
import time
from datetime import datetime
from .interface import DesktopInterface

class MockDesktopService(DesktopInterface):
    def __init__(self):
        self.incident_active = False
        self.cpu_load = 15.4
        self.memory_load = 32.1
        self.current_url = "about:blank"
        print("[INIT] Mock Desktop Service | Mode: DEMO", flush=True)

    def trigger_incident(self):
        print("[DEMO] Incident Triggered: High CPU", flush=True)
        self.incident_active = True
        self.cpu_load = 99.8
        self.memory_load = 85.5

    def resolve_incident(self):
        print("[DEMO] Incident Resolved", flush=True)
        self.incident_active = False
        self.cpu_load = 15.4
        self.memory_load = 32.1

    def get_system_health(self):
        return {
            "status": "critical" if self.incident_active else "online",
            "cpu_percent": self.cpu_load,
            "memory_percent": self.memory_load,
            "boot_time": "2024-01-01 08:00:00"
        }

    def run_terminal_command(self, command: str):
        cmd = command.lower()
        print(f"[DEMO CMD] {command}", flush=True)
        
        if "top" in cmd or "htop" in cmd:
            if self.incident_active:
                return "PID  USER      PR  NI  VIRT  RES  %CPU  COMMAND\n1337 root      20   0  10g   8g    99.8  ffmpeg_transcode\n882  sys       20   0  2g    1g    1.2   dockerd"
            return "PID  USER      PR  NI  VIRT  RES  %CPU  COMMAND\n882  sys       20   0  2g    1g    1.2   dockerd\n443  user      20   0  4g    2g    0.5   chrome"
        
        if "kill" in cmd and "1337" in cmd:
            if self.incident_active:
                self.resolve_incident()
                return "Process 1337 (ffmpeg_transcode) terminated. System load normalizing."
            return "Process 1337 not found."
            
        if "systemctl" in cmd and "restart" in cmd:
            if self.incident_active:
                self.resolve_incident()
                return "Service restarted successfully. CPU load normalizing."
            return "Service restarted."

        return f"Mock Output for: {command}"

    def get_screenshot_base64(self):
        # Returns a 1x1 pixel base64 image string to satisfy the API
        # Red if incident, Green if normal (simulated)
        if self.incident_active:
            # Red Pixel
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        # Green Pixel
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWMrwHwAC+AGk1kFw2AAAAABJRU5ErkJggg=="

    def scan_ui_tree(self):
        if self.incident_active:
            return json.dumps([{"text": "CRITICAL ALERT: HIGH CPU LOAD", "type": "Window", "x": 500, "y": 300}, {"text": "Process Monitor", "type": "Window", "x": 0, "y": 0}])
        return json.dumps([{"text": "Desktop", "type": "Pane", "x": 0, "y": 0}])

    # Boilerplate simulations
    def click_at(self, x, y): return f"Simulated Click at {x},{y}"
    def drag_mouse(self, sx, sy, ex, ey): return f"Simulated Drag from {sx},{sy} to {ex},{ey}"
    def type_text(self, text): return f"Simulated Typing: {text}"
    def press_hotkey(self, keys): return f"Simulated Keys: {keys}"
    def wait_seconds(self, seconds): return f"Waited {seconds}s"
    def open_target(self, resource): return f"Simulated Open: {resource}"
    def scroll_page(self, direction): return f"Simulated Scroll {direction}"

    def browser_command(self, action: str, url: str = None):
        act = action.upper()
        if act == "NAVIGATE" and url:
            self.current_url = url
            return f"Simulated Navigation to {url}"
        return f"Simulated Browser Action: {act}"

    def read_page_content(self):
        if "github" in self.current_url:
            return "Simulated GitHub PR Page: [Open] Fix memory leak..."
        return f"Simulated Page Content for {self.current_url}..."
