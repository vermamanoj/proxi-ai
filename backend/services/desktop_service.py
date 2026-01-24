import json
import platform
import time
import subprocess
import os
import tempfile
import base64
import threading
import sys
import webbrowser
from datetime import datetime

# Conditional Imports for OS Independence
try:
    import pyautogui
    import cv2
    import numpy as np
    import pyperclip
    DESKTOP_AVAILABLE = True
except ImportError:
    print("[WARN] Desktop automation libraries (pyautogui/cv2/pyperclip) not found. Desktop tools disabled.", flush=True)
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

    # --- Headless Capabilities ---
    def run_terminal_command(self, command: str):
        """Executes a shell command."""
        print(f"[DEBUG] Request to execute: {command}", flush=True)
        is_windows = self.os_type == "Windows"
        
        clean_cmd = command.strip()
        if is_windows:
            clean_cmd = clean_cmd.replace(" || ", " ; if ($?) { ").replace(" && ", " ; if ($?) { ") 
            if clean_cmd.lower().startswith("powershell"):
                clean_cmd = clean_cmd.replace("powershell -command", "").replace("powershell", "").strip().strip('"').strip("'")
        
        try:
            if is_windows:
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

    # --- NEW: High-Speed Navigation & Sensing ---

    def open_target(self, resource: str):
        """
        Opens a URL in the default browser or a local file.
        """
        ok, msg = self._check_availability()
        # Even if desktop automation is off, we might be able to open a URL in some envs, 
        # but generally this is a desktop action.
        if not ok: return msg
        
        print(f"[DEBUG] Opening target: {resource}", flush=True)
        try:
            if resource.startswith("http") or resource.startswith("www"):
                webbrowser.open(resource)
                # Give browser time to launch/render
                time.sleep(3) 
                return f"Opened URL: {resource}"
            else:
                # Local file
                if self.os_type == "Windows":
                    os.startfile(resource)
                else:
                    subprocess.call(('xdg-open', resource))
                time.sleep(1)
                return f"Opened File: {resource}"
        except Exception as e:
            return f"Failed to open target: {e}"

    def read_page_content(self):
        """
        Simulates Ctrl+A -> Ctrl+C to copy page content and returns the clipboard text.
        This allows high-speed reading of web pages or documents.
        """
        ok, msg = self._check_availability()
        if not ok: return msg

        with self._input_lock:
            try:
                # 1. Clear Clipboard first to ensure we don't read stale data
                pyperclip.copy("") 
                
                # 2. Select All
                ctrl_key = 'ctrl' if self.os_type == "Windows" else 'command'
                pyautogui.hotkey(ctrl_key, 'a')
                time.sleep(0.3)
                
                # 3. Copy
                pyautogui.hotkey(ctrl_key, 'c')
                time.sleep(0.5) # Wait for OS clipboard update
                
                # 4. Read
                content = pyperclip.paste()
                
                # 5. Cleanup (Click somewhere neutral to deselect, optional but good UX)
                # We won't click to avoid accidental interactions, just return data.
                
                if not content:
                    return "Clipboard is empty. Failed to copy content."
                
                # Truncate for LLM sanity if MASSIVE (limit to ~20k chars)
                snippet = content[:20000]
                truncated = len(content) > 20000
                return f"PAGE CONTENT ({len(content)} chars):\n{snippet}" + ("\n...[TRUNCATED]" if truncated else "")

            except Exception as e:
                return f"Failed to read page content: {e}"

    def scroll_page(self, direction: str = 'down'):
        """Scrolls the active window."""
        ok, msg = self._check_availability()
        if not ok: return msg

        with self._input_lock:
            try:
                clicks = -500 if direction == 'down' else 500
                pyautogui.scroll(clicks)
                return f"Scrolled {direction}"
            except Exception as e:
                return f"Scroll failed: {e}"

    # --- Existing GUI Capabilities ---
    def scan_ui_tree(self):
        """Explicitly scans accessibility tree without ambiguity"""
        ok, msg = self._check_availability()
        if not ok: return msg

        if USE_ACCESSIBILITY:
            try:
                ui_elements = self._scan_accessibility_tree()
                if ui_elements:
                    return json.dumps(ui_elements, separators=(',', ':')) 
                return "Scanning UI Tree returned no elements. Try 'look_at_screen' for visual analysis."
            except Exception as e:
                print(f"[DEBUG] Accessibility Scan failed: {e}", flush=True)
                return f"Error scanning UI tree: {e}"

        return "Accessibility API unavailable. Use 'look_at_screen' instead."

    def get_screenshot_base64(self):
        ok, _ = self._check_availability()
        if not ok: return None

        try:
            print("[DEBUG] Capturing screenshot...", flush=True)
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            height, width = img_np.shape[:2]
            if width > 1920:
                scale = 1920 / width
                img_np = cv2.resize(img_np, (0, 0), fx=scale, fy=scale)

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
                time.sleep(0.2)
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
