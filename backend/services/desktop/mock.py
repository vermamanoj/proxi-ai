
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
        
        # Process listing commands
        if any(x in cmd for x in ["top", "htop", "ps aux", "ps -aux", "ps -ef"]):
            if self.incident_active:
                return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root      1337 99.8 45.2 10485760 8388608 ?   R    09:15  45:23 ffmpeg -i /data/uploads/wedding_video.mp4 -c:v libx264 -preset slow -crf 18 -c:a aac -o /data/output/wedding_4k.mp4
  └─ Process Info: Video transcoding job converting wedding_video.mp4 to 4K H.264 format
  └─ Started: 45 minutes ago | Owner: media-service | Priority: Low (batch job)
  └─ Impact: Non-critical batch processing, safe to terminate and restart later

root       882  1.2  2.1 2097152 1048576 ?   Ss   08:00   0:45 /usr/bin/dockerd --containerd=/run/containerd/containerd.sock
user       443  0.5  4.2 4194304 2097152 ?   Sl   08:05   0:12 /opt/google/chrome/chrome --type=renderer"""
            return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root       882  1.2  2.1 2097152 1048576 ?   Ss   08:00   0:45 /usr/bin/dockerd
user       443  0.5  4.2 4194304 2097152 ?   Sl   08:05   0:12 /opt/google/chrome/chrome
user       512  0.1  1.0 1048576  524288 ?   Sl   08:10   0:02 /usr/bin/code"""

        # Kill commands - require the right PID
        if "kill" in cmd:
            if "1337" in cmd:
                if self.incident_active:
                    self.resolve_incident()
                    return "Process 1337 terminated successfully."
                return "kill: (1337): No such process"
            # Wrong PID
            return "Process terminated."
            
        # Service restart
        if "systemctl" in cmd and "restart" in cmd:
            if self.incident_active:
                self.resolve_incident()
                return "Service restarted successfully. CPU load normalizing."
            return "Service restarted."

        # Other common diagnostic commands
        if "free" in cmd or "memory" in cmd:
            return "              total        used        free      shared  buff/cache   available\nMem:       16384000    14000000     1000000      500000     1384000     1500000"
        
        if "df" in cmd:
            return "Filesystem     1K-blocks      Used Available Use% Mounted on\n/dev/sda1      500000000 450000000  50000000  90% /"
        
        if "uptime" in cmd:
            return " 14:30:00 up 45 days,  3:22,  2 users,  load average: 4.50, 3.20, 2.10" if self.incident_active else " 14:30:00 up 45 days,  3:22,  2 users,  load average: 0.15, 0.10, 0.05"

        return f"Command executed: {command}"

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
    def press_hotkey(self, keys: list[str]): return f"Simulated Keys: {keys}"
    def wait_seconds(self, seconds): return f"Waited {seconds}s"
    def open_target(self, resource): return f"Simulated Open: {resource}"
    def scroll_page(self, direction): return f"Simulated Scroll {direction}"

    def browser_command(self, action: str, url: str = None):
        act = action.upper()
        if act == "NAVIGATE" and url:
            self.current_url = url
            return f"Simulated Navigation to {url}"
        elif act == "NEW_TAB":
            return "Simulated New Tab"
        elif act == "CLOSE_TAB":
            return "Simulated Close Tab"
        return f"Simulated Browser Action: {act}"

    def read_page_content(self):
        if "github" in self.current_url:
            return "Simulated GitHub PR Page: [Open] Fix memory leak..."
        return f"Simulated Page Content for {self.current_url}..."
