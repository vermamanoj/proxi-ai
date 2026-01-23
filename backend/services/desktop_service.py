import json
import platform
import time
import subprocess
import os
import tempfile
import base64
import threading
import sys
from datetime import datetime

# Conditional Imports for OS Independence
try:
    import pyautogui
    import cv2
    import numpy as np
    DESKTOP_AVAILABLE = True
except ImportError:
    print("[WARN] Desktop automation libraries (pyautogui/cv2) not found. Desktop tools disabled.", flush=True)
    DESKTOP_AVAILABLE = False
except KeyError:
    # Pyautogui can fail on headless linux if DISPLAY is not set
    print("[WARN] Headless environment detected (No DISPLAY). Desktop tools disabled.", flush=True)
    DESKTOP_AVAILABLE = False

# Windows Accessibility Imports
USE_ACCESSIBILITY = False
if platform.system() == "Windows":
    try:
        import ctypes
        from pywinauto import Desktop, Application
        USE_ACCESSIBILITY = True
    except ImportError:
        print("[WARN] pywinauto not found. Install it for faster automation.", flush=True)

class DesktopService:
    def __init__(self):
        self.os_type = platform.system()
        self.desktop_enabled = DESKTOP_AVAILABLE
        
        # Thread lock to serialize physical inputs
        self._input_lock = threading.Lock()
        
        print(f"[INIT] Desktop Service | OS: {self.os_type} | Desktop Tools: {'ACTIVE' if self.desktop_enabled else 'DISABLED'}", flush=True)

        if self.desktop_enabled:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1 
            self.screen_width, self.screen_height = pyautogui.size()
        
        if USE_ACCESSIBILITY:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _check_availability(self):
        if not self.desktop_enabled:
            return False, "Error: Desktop tools are unavailable. The backend is likely running in a headless Cloud environment (Linux Container). I can only perform Cloud/GitHub tasks here."
        return True, ""

    # --- Headless Capabilities (Works on Linux too, usually) ---
    def run_terminal_command(self, command: str):
        """
        Executes a shell command. Adapts to PowerShell (Windows) or Bash (Linux).
        """
        print(f"[DEBUG] Request to execute: {command}", flush=True)
        
        is_windows = self.os_type == "Windows"
        shell_type = "powershell" if is_windows else "bash"
        
        clean_cmd = command.strip()
        
        # Syntax Normalization
        if is_windows:
            clean_cmd = clean_cmd.replace(" || ", " ; if ($?) { ").replace(" && ", " ; if ($?) { ") 
            if clean_cmd.lower().startswith("powershell"):
                clean_cmd = clean_cmd.replace("powershell -command", "").replace("powershell", "").strip().strip('"').strip("'")
        
        print(f"[DEBUG] Executing via {shell_type}: {clean_cmd}", flush=True)

        try:
            if is_windows:
                # Windows PowerShell Execution
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ps1') as tmp:
                    preamble = "$ProgressPreference = 'SilentlyContinue'; $ConfirmPreference = 'None'; "
                    tmp.write(preamble + clean_cmd)
                    script_path = tmp.name
                
                result = subprocess.run(
                    ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path], 
                    capture_output=True, text=True, timeout=45 
                )
                try: os.remove(script_path)
                except: pass

            else:
                # Linux Bash Execution
                result = subprocess.run(
                    ["/bin/bash", "-c", clean_cmd],
                    capture_output=True, text=True, timeout=45
                )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                out = stdout[:2000] + "\n...[TRUNCATED]" if len(stdout) > 2000 else stdout
                return f"SUCCESS:\n{out}" if out else "SUCCESS (No Output)"
            else:
                return f"ERROR:\n{stderr}"

        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 45 seconds."
        except Exception as e:
            return f"SYSTEM ERROR: {str(e)}"

    # --- GUI Capabilities (Windows/Desktop Only) ---
    def get_screen_map(self, mode: str = "hybrid"):
        ok, msg = self._check_availability()
        if not ok: return msg

        if mode == "visual":
            return "USE_GEMINI_VISION_API"

        if USE_ACCESSIBILITY:
            try:
                ui_elements = self._scan_accessibility_tree()
                if ui_elements:
                    return json.dumps(ui_elements, separators=(',', ':')) 
            except Exception as e:
                print(f"[DEBUG] Accessibility Scan failed: {e}", flush=True)

        # Fallback to simple coordinate hint if vision needed
        return json.dumps([{"text": "ACCESSIBILITY_FAILED_TRY_VISUAL_MODE", "x": 0, "y": 0}])

    def get_screenshot_base64(self):
        ok, _ = self._check_availability()
        if not ok: return None

        try:
            print("[DEBUG] Capturing screenshot...", flush=True)
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            
            # Resize if huge
            height, width = img_np.shape[:2]
            if width > 1920:
                scale = 1920 / width
                img_np = cv2.resize(img_np, (0, 0), fx=scale, fy=scale)

            # RGB -> BGR for OpenCV
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
            if not is_success: return None
            
            return base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}", flush=True)
            return None

    def _scan_accessibility_tree(self):
        elements = []
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return []
            app = Application(backend="uia").connect(handle=hwnd)
            active_window = app.top_window()
            controls = active_window.descendants()
            for ctrl in controls:
                try:
                    rect = ctrl.rectangle()
                    text = ctrl.window_text()
                    if rect.width() == 0 or not text.strip(): continue
                    elements.append({
                        "text": text,
                        "type": ctrl.friendly_class_name(),
                        "x": int((rect.left + rect.right) / 2),
                        "y": int((rect.top + rect.bottom) / 2)
                    })
                    if len(elements) > 60: break 
                except: continue
        except: pass 
        return elements

    def click_at(self, x: int, y: int):
        ok, msg = self._check_availability()
        if not ok: return msg
        
        with self._input_lock:
            try:
                pyautogui.moveTo(int(x), int(y), duration=0.1)
                pyautogui.click()
                return f"Clicked ({x}, {y})"
            except Exception as e:
                return f"Click Failed: {e}"

    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        ok, msg = self._check_availability()
        if not ok: return msg
        
        with self._input_lock:
            try:
                pyautogui.moveTo(start_x, start_y)
                pyautogui.dragTo(end_x, end_y, duration=0.2, button='left')
                return f"Dragged from {start_x},{start_y} to {end_x},{end_y}"
            except Exception as e:
                return f"Drag Failed: {e}"

    def type_text(self, text: str):
        ok, msg = self._check_availability()
        if not ok: return msg

        with self._input_lock:
            try:
                pyautogui.write(text, interval=0.01)
                return f"Typed '{text}'"
            except Exception as e:
                return f"Type Failed: {e}"

    def press_hotkey(self, keys: list):
        ok, msg = self._check_availability()
        if not ok: return msg

        with self._input_lock:
            try:
                pyautogui.hotkey(*keys)
                return f"Pressed {'+'.join(keys)}"
            except Exception as e:
                return f"Hotkey Failed: {e}"
