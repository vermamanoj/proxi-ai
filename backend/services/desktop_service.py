import pyautogui
import cv2
import numpy as np
import json
import platform
import ctypes
import time
import subprocess
import os
import tempfile
import base64
import io
from datetime import datetime

# Windows Accessibility Imports
if platform.system() == "Windows":
    try:
        from pywinauto import Desktop, Application
        from pywinauto.controls.hwndwrapper import HwndWrapper
    except ImportError:
        print("[WARN] pywinauto not found. Install it for faster automation.")

class DesktopService:
    def __init__(self):
        print("[INIT] Desktop Service instantiated (Hybrid: Shell + UIAutomation + Vision API).", flush=True)
        self.use_accessibility = platform.system() == "Windows"
        
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        if self.use_accessibility:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                print("[INIT] Windows Accessibility Hook Ready.", flush=True)
            except Exception as e:
                print(f"[WARN] Failed to set DPI awareness: {e}", flush=True)
        
        self.screen_width, self.screen_height = pyautogui.size()

    # --- NEW: Headless Capabilities ---
    def run_terminal_command(self, command: str):
        """
        Executes a shell command via a temporary PowerShell script.
        """
        print(f"[DEBUG] Request to execute: {command}", flush=True)
        
        clean_cmd = command.strip()
        # Fix common LLM syntax errors for PowerShell 5.1
        clean_cmd = clean_cmd.replace(" || ", " ; if ($?) { ").replace(" && ", " ; if ($?) { ") 

        if clean_cmd.lower().startswith("powershell -command"):
            clean_cmd = clean_cmd[19:].strip().strip('"').strip("'")
        elif clean_cmd.lower().startswith("powershell"):
            clean_cmd = clean_cmd[10:].strip()

        print(f"[DEBUG] Sanitized Shell Command: {clean_cmd}", flush=True)

        script_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ps1') as tmp:
                # Add preferences to suppress interactive prompts
                preamble = "$ProgressPreference = 'SilentlyContinue'; $ConfirmPreference = 'None'; "
                tmp.write(preamble + clean_cmd)
                script_path = tmp.name
            
            # Added -NonInteractive to prevent hanging on prompts
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path], 
                capture_output=True, 
                text=True, 
                timeout=45 
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                if len(stdout) > 2000:
                    stdout = stdout[:2000] + "\n...[TRUNCATED]"
                return f"SUCCESS:\n{stdout}" if stdout else "SUCCESS (No Output)"
            else:
                return f"ERROR:\n{stderr}"

        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 45 seconds."
        except Exception as e:
            return f"SYSTEM ERROR: {str(e)}"
        finally:
            if script_path and os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except:
                    pass

    # --- Existing GUI Capabilities ---
    def get_screen_map(self, mode: str = "hybrid"):
        """
        Smart Scan.
        mode="hybrid" (Default): Tries Accessibility first (Fast).
        mode="visual": Returns a special signal to use Gemini Vision API.
        """
        if mode == "visual":
            return "USE_GEMINI_VISION_API"

        # Hybrid attempts Accessibility First
        if self.use_accessibility:
            try:
                ui_elements = self._scan_accessibility_tree()
                if len(ui_elements) > 3: 
                    print(f"[DEBUG] Accessibility Scan: Found {len(ui_elements)} elements (Fast).", flush=True)
                    if ui_elements:
                        ui_elements[0]["_meta_source"] = "WINDOWS_UIA"
                    return json.dumps(ui_elements, separators=(',', ':')) 
            except Exception as e:
                print(f"[DEBUG] Accessibility Scan skipped/failed: {e}.", flush=True)

        return json.dumps([{"text": "ACCESSIBILITY_FAILED_TRY_VISUAL_MODE", "x": 0, "y": 0}])

    def get_screenshot_base64(self):
        """Captures screen and returns base64 encoded string for Vision API."""
        try:
            print("[DEBUG] Capturing screenshot for Vision API...", flush=True)
            screenshot = pyautogui.screenshot()
            
            # Convert to RGB (pyautogui is RGB)
            img_np = np.array(screenshot)
            
            # Resize for bandwidth efficiency if 4K
            height, width = img_np.shape[:2]
            if width > 1920:
                scale = 1920 / width
                img_np = cv2.resize(img_np, (0, 0), fx=scale, fy=scale)

            # Convert to BGR for OpenCV encoding (if needed) or just use PIL
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
            if not is_success:
                return None
            
            base64_str = base64.b64encode(buffer).decode("utf-8")
            return base64_str
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}", flush=True)
            return None

    def _scan_accessibility_tree(self):
        elements = []
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                raise Exception("No active window handle found")

            app = Application(backend="uia").connect(handle=hwnd)
            active_window = app.top_window()
            
            window_title = active_window.window_text()
            print(f"[DEBUG] Active Window: {window_title}", flush=True)

            controls = active_window.descendants()
            for ctrl in controls:
                try:
                    rect = ctrl.rectangle()
                    text = ctrl.window_text()
                    if rect.width() == 0 or rect.height() == 0: continue
                    if not text.strip(): continue
                    center_x = int((rect.left + rect.right) / 2)
                    center_y = int((rect.top + rect.bottom) / 2)
                    if center_x < 0 or center_y < 0: continue

                    elements.append({
                        "text": text,
                        "type": ctrl.friendly_class_name(),
                        "x": center_x,
                        "y": center_y,
                        "w": rect.width(),
                        "h": rect.height()
                    })
                    if len(elements) > 60: break 
                except Exception:
                    continue
        except Exception as e:
            raise e 
        return elements

    def click_at(self, x: int, y: int):
        try:
            ix, iy = int(x), int(y)
            print(f"[DEBUG] Clicking at {ix}, {iy}", flush=True)
            pyautogui.moveTo(ix, iy, duration=0.2)
            pyautogui.click()
            return f"Clicked ({ix}, {iy})"
        except Exception as e:
            return f"Click Failed: {e}"

    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Drags mouse from point A to point B. Useful for drawing."""
        try:
            print(f"[DEBUG] Dragging from ({start_x},{start_y}) to ({end_x},{end_y})", flush=True)
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.5, button='left')
            return f"Dragged from {start_x},{start_y} to {end_x},{end_y}"
        except Exception as e:
            return f"Drag Failed: {e}"

    def type_text(self, text: str):
        try:
            print(f"[DEBUG] Typing: {text}", flush=True)
            pyautogui.write(text, interval=0.01)
            return f"Typed '{text}'"
        except Exception as e:
            return f"Type Failed: {e}"

    def press_hotkey(self, keys: list):
        try:
            print(f"[DEBUG] Hotkey: {keys}", flush=True)
            pyautogui.hotkey(*keys)
            return f"Pressed {'+'.join(keys)}"
        except Exception as e:
            return f"Hotkey Failed: {e}"
