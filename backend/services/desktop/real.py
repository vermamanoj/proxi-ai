
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
import psutil
from datetime import datetime
from .interface import DesktopInterface

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
    print("[WARN] Headless environment detected (No DISPLAY). Desktop tools disabled.", flush=True)
    DESKTOP_AVAILABLE = False

USE_ACCESSIBILITY = False
if platform.system() == "Windows":
    try:
        import ctypes
        from pywinauto import Desktop, Application
        USE_ACCESSIBILITY = True
    except ImportError:
        pass

class RealDesktopService(DesktopInterface):
    def __init__(self):
        self.os_type = platform.system()
        self.desktop_enabled = DESKTOP_AVAILABLE
        self._input_lock = threading.Lock()
        
        print(f"[INIT] Real Desktop Service | OS: {self.os_type} | Desktop Tools: {'ACTIVE' if self.desktop_enabled else 'DISABLED'}", flush=True)

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
            return False, "Error: Desktop tools are unavailable. The backend is likely running in a headless Cloud environment (Linux Container)."
        return True, ""

    def get_system_health(self):
        return { 
            "status": "online", 
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        }

    def run_terminal_command(self, command: str):
        print(f"[DEBUG] Request to execute: {command}", flush=True)
        is_windows = self.os_type == "Windows"
        
        clean_cmd = command.strip()
        
        # Detect GUI apps that should be launched non-blocking
        GUI_APPS = ['mspaint', 'notepad', 'calc', 'explorer', 'code', 'chrome', 'firefox', 'edge', 'word', 'excel', 'powerpoint']
        is_gui_launch = any(clean_cmd.lower().startswith(app) or clean_cmd.lower() == app for app in GUI_APPS)
        
        if is_windows:
            clean_cmd = clean_cmd.replace(" || ", " ; if ($?) { ").replace(" && ", " ; if ($?) { ") 
            if clean_cmd.lower().startswith("powershell"):
                clean_cmd = clean_cmd.replace("powershell -command", "").replace("powershell", "").strip().strip('"').strip("'")
            
            # Launch GUI apps non-blocking with Start-Process
            if is_gui_launch:
                clean_cmd = f"Start-Process {clean_cmd}"
                print(f"[DEBUG] GUI app detected, using: {clean_cmd}", flush=True)
        
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

    def open_target(self, resource: str):
        ok, msg = self._check_availability()
        if not ok: return msg
        try:
            if resource.startswith("http") or resource.startswith("www"):
                webbrowser.open(resource)
                time.sleep(3) 
                return f"Opened URL: {resource}"
            else:
                if self.os_type == "Windows":
                    os.startfile(resource)
                else:
                    subprocess.call(('xdg-open', resource))
                time.sleep(1)
                return f"Opened File: {resource}"
        except Exception as e:
            return f"Failed to open target: {e}"

    def read_page_content(self):
        ok, msg = self._check_availability()
        if not ok: return msg
        with self._input_lock:
            try:
                pyperclip.copy("") 
                ctrl_key = 'ctrl' if self.os_type == "Windows" else 'command'
                pyautogui.hotkey(ctrl_key, 'a')
                time.sleep(0.3)
                pyautogui.hotkey(ctrl_key, 'c')
                time.sleep(0.5)
                content = pyperclip.paste()
                if not content: return "Clipboard is empty."
                snippet = content[:20000]
                truncated = len(content) > 20000
                return f"PAGE CONTENT ({len(content)} chars):\n{snippet}" + ("\n...[TRUNCATED]" if truncated else "")
            except Exception as e:
                return f"Failed to read page content: {e}"

    def scroll_page(self, direction: str = 'down'):
        ok, msg = self._check_availability()
        if not ok: return msg
        with self._input_lock:
            try:
                clicks = -500 if direction == 'down' else 500
                pyautogui.scroll(clicks)
                return f"Scrolled {direction}"
            except Exception as e:
                return f"Scroll failed: {e}"

    def scan_ui_tree(self):
        ok, msg = self._check_availability()
        if not ok: return msg
        if USE_ACCESSIBILITY:
            try:
                ui_elements = self._scan_accessibility_tree()
                if ui_elements:
                    return json.dumps(ui_elements, separators=(',', ':')) 
                return "Scanning UI Tree returned no elements."
            except Exception as e:
                return f"Error scanning UI tree: {e}"
        return "Accessibility API unavailable."

    def get_screenshot_base64(self):
        ok, _ = self._check_availability()
        if not ok: return None
        try:
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            height, width = img_np.shape[:2]
            if width > 1920:
                scale = 1920 / width
                img_np = cv2.resize(img_np, (0, 0), fx=scale, fy=scale)
            # Reduce quality to keep base64 size manageable for streaming
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 50])
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

    def press_hotkey(self, keys: list[str]):
        ok, msg = self._check_availability()
        if not ok: return msg
        with self._input_lock:
            try:
                pyautogui.hotkey(*keys)
                return f"Pressed {'+'.join(keys)}"
            except Exception as e:
                return f"Hotkey Failed: {e}"

    def wait_seconds(self, seconds: int):
        time.sleep(seconds)
        return f"Waited {seconds}s"
    
    # --- NEW SEMANTIC BROWSER CONTROLS ---

    def _focus_browser(self):
        """Attempts to bring a known browser window to the foreground."""
        if not (self.os_type == "Windows" and USE_ACCESSIBILITY):
             return False

        try:
            desktop = Desktop(backend="uia")
            # Common browser names in title
            for name in ["Chrome", "Edge", "Firefox", "Brave"]:
                try:
                    windows = desktop.windows(title_re=f".*{name}.*")
                    if windows:
                        w = windows[0]
                        if w.is_minimized(): w.restore()
                        w.set_focus()
                        time.sleep(0.5) 
                        return True
                except: continue
        except Exception as e:
            print(f"[DEBUG] Focus failed: {e}", flush=True)
        return False

    def browser_command(self, action: str, url: str = None):
        """Executes browser hotkeys."""
        ok, msg = self._check_availability()
        if not ok: return msg

        # Platform specific modifier
        mod = 'command' if self.os_type == 'Darwin' else 'ctrl'

        with self._input_lock:
            # 1. Attempt Focus
            self._focus_browser()
            
            # 2. Execute Action
            try:
                act = action.upper()
                
                if act == "NEW_TAB":
                    pyautogui.hotkey(mod, 't')
                    return "Opened New Tab (Ctrl+T)"
                
                elif act == "CLOSE_TAB":
                    pyautogui.hotkey(mod, 'w')
                    return "Closed Tab (Ctrl+W)"
                
                elif act == "REFRESH":
                    if self.os_type == "Darwin":
                        pyautogui.hotkey(mod, 'r')
                    else:
                        pyautogui.press('f5')
                    return "Refreshed Page"
                
                elif act == "NAVIGATE":
                    if not url: return "Error: URL required for NAVIGATE"
                    pyautogui.hotkey(mod, 'l')
                    time.sleep(0.2)
                    pyautogui.write(url, interval=0.01)
                    pyautogui.press('enter')
                    return f"Navigated to {url}"
                
                elif act == "SEARCH":
                    if not url: return "Error: Query text required for SEARCH"
                    pyautogui.hotkey(mod, 'f')
                    time.sleep(0.2)
                    pyautogui.write(url, interval=0.02)
                    pyautogui.press('enter')
                    return f"Searched page for '{url}'"
                
                else:
                    return f"Unknown browser action: {action}"

            except Exception as e:
                return f"Browser Command Failed: {e}"

    def focus_window(self, title: str):
        """Bring a window to foreground by title (partial match)."""
        ok, msg = self._check_availability()
        if not ok: return msg
        
        if not (self.os_type == "Windows" and USE_ACCESSIBILITY):
            return "Error: Window focus requires Windows with pywinauto"
        
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=f".*{title}.*", visible_only=True)
            if not windows:
                return f"Error: No window found matching '{title}'"
            
            w = windows[0]
            if w.is_minimized():
                w.restore()
            w.set_focus()
            time.sleep(0.3)
            return f"Focused window: {w.window_text()}"
        except Exception as e:
            return f"Focus window failed: {e}"

    def get_window_rect(self, title: str):
        """Get window position and size."""
        ok, msg = self._check_availability()
        if not ok: return {"error": msg}
        
        if not (self.os_type == "Windows" and USE_ACCESSIBILITY):
            return {"error": "Window rect requires Windows with pywinauto"}
        
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=f".*{title}.*", visible_only=True)
            if not windows:
                return {"error": f"No window found matching '{title}'"}
            
            w = windows[0]
            rect = w.rectangle()
            return {
                "title": w.window_text(),
                "x": rect.left,
                "y": rect.top,
                "width": rect.width(),
                "height": rect.height(),
                "right": rect.right,
                "bottom": rect.bottom
            }
        except Exception as e:
            return {"error": f"Get window rect failed: {e}"}

    def list_windows(self):
        """List all visible windows."""
        ok, msg = self._check_availability()
        if not ok: return {"error": msg}
        
        if not (self.os_type == "Windows" and USE_ACCESSIBILITY):
            return {"error": "List windows requires Windows with pywinauto"}
        
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(visible_only=True)
            result = []
            for w in windows[:20]:  # Limit to 20
                try:
                    title = w.window_text()
                    if title and len(title.strip()) > 0:
                        rect = w.rectangle()
                        result.append({
                            "title": title,
                            "x": rect.left,
                            "y": rect.top,
                            "width": rect.width(),
                            "height": rect.height()
                        })
                except:
                    continue
            return {"windows": result}
        except Exception as e:
            return {"error": f"List windows failed: {e}"}
