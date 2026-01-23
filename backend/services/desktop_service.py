import pyautogui
import easyocr
import cv2
import numpy as np
import json
import platform
import ctypes
import time
import subprocess
from datetime import datetime
import psutil

# Windows Accessibility Imports
if platform.system() == "Windows":
    try:
        from pywinauto import Desktop, Application
        from pywinauto.controls.hwndwrapper import HwndWrapper
    except ImportError:
        print("[WARN] pywinauto not found. Install it for faster automation.")

class DesktopService:
    def __init__(self):
        print("[INIT] Desktop Service instantiated (Hybrid: Shell + UIAutomation + Vision).", flush=True)
        self._reader = None  # Lazy load placeholder for OCR
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

    @property
    def reader(self):
        """Lazy loader for EasyOCR (Fallback only)."""
        if self._reader is None:
            print("[INFO] 🐢 Loading EasyOCR Model (Fallback)...", flush=True)
            self._reader = easyocr.Reader(['en'], gpu=False)
        return self._reader

    # --- NEW: Headless Capabilities ---
    def run_terminal_command(self, command: str):
        """
        Executes a shell command (PowerShell on Windows) and returns the output.
        This works even if the screen is locked or RDP is disconnected.
        """
        print(f"[DEBUG] Executing Shell Command: {command}", flush=True)
        try:
            # Use PowerShell for more capability on Windows
            full_command = f"powershell -Command \"{command}\""
            
            result = subprocess.run(
                full_command, 
                capture_output=True, 
                text=True, 
                shell=True,
                timeout=30 # Prevent hanging indefinitely
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                # Truncate overly long logs
                if len(stdout) > 2000:
                    stdout = stdout[:2000] + "\n...[TRUNCATED]"
                return f"SUCCESS:\n{stdout}" if stdout else "SUCCESS (No Output)"
            else:
                return f"ERROR:\n{stderr}"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 30 seconds."
        except Exception as e:
            return f"SYSTEM ERROR: {str(e)}"

    # --- Existing GUI Capabilities ---
    def get_screen_map(self):
        """
        Smart Scan:
        1. Try to get the Active Window via OS API (Fast, structured).
        2. If that fails or yields few results, fallback to OCR (Slow, visual).
        """
        scan_source = "UNKNOWN"
        result_json = "[]"

        if self.use_accessibility:
            try:
                # Attempt Accessibility Scan first
                ui_elements = self._scan_accessibility_tree()
                
                # Heuristic: If we found > 3 elements, we assume the UIA tree is valid.
                if len(ui_elements) > 3: 
                    print(f"[DEBUG] Accessibility Scan: Found {len(ui_elements)} elements (Fast).", flush=True)
                    scan_source = "ACCESSIBILITY_API"
                    # Inject metadata into the first element
                    if ui_elements:
                        ui_elements[0]["_meta_source"] = "WINDOWS_UIA"
                    result_json = json.dumps(ui_elements, separators=(',', ':'))
                    return result_json 
            except Exception as e:
                print(f"[WARN] Accessibility Scan Failed: {e}. Fallback to OCR.", flush=True)

        # Fallback to Visual Scan
        scan_source = "COMPUTER_VISION"
        result_json = self._scan_visual_ocr()
        return result_json

    def _scan_accessibility_tree(self):
        elements = []
        try:
            desktop = Desktop(backend="uia")
            active_window = desktop.active()
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
            print(f"[ERROR] UIAutomation Tree Walk Error: {e}")
        return elements

    def _scan_visual_ocr(self):
        try:
            print("[DEBUG] Running Visual OCR Scan...", flush=True)
            start_time = time.time()
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            if img_cv is None or img_cv.size == 0:
                print("[ERROR] Screenshot failed (Empty Image). RDP might be minimized.", flush=True)
                return json.dumps([{"text": "ERROR_SCREEN_BLANK", "x": 0, "y": 0}])

            scale_percent = 50
            width = int(img_cv.shape[1] * scale_percent / 100)
            height = int(img_cv.shape[0] * scale_percent / 100)
            resized_img = cv2.resize(img_cv, (width, height), interpolation=cv2.INTER_AREA)
            
            results = self.reader.readtext(resized_img, detail=1)
            elements = []
            elements.append({"text": "Metadata:Source=VISION_OCR", "x": 0, "y": 0, "type": "meta"})

            for (bbox, text, prob) in results:
                if prob < 0.4: continue 
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                center_x = int(((x1 + x2) / 2) * (100 / scale_percent))
                center_y = int(((y1 + y2) / 2) * (100 / scale_percent))
                elements.append({
                    "text": text,
                    "type": "VisualText",
                    "x": center_x,
                    "y": center_y
                })
            
            duration = round(time.time() - start_time, 2)
            print(f"[DEBUG] OCR Scan Complete: {len(elements)} items in {duration}s", flush=True)
            return json.dumps(elements, separators=(',', ':'))
        except Exception as e:
            print(f"[ERROR] OCR Failed: {e}", flush=True)
            return "[]"

    def click_at(self, x: int, y: int):
        try:
            print(f"[DEBUG] Clicking at {x}, {y}", flush=True)
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            return f"Clicked ({x}, {y})"
        except Exception as e:
            return f"Click Failed: {e}"

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
