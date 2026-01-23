import pyautogui
import easyocr
import cv2
import numpy as np
import json
import platform
import ctypes
import time
from datetime import datetime

class DesktopService:
    def __init__(self):
        print("[INIT] Initializing Desktop Ghost Operator (EasyOCR)...")
        # gpu=False is safer for compatibility, though slower
        self.reader = easyocr.Reader(['en'], gpu=False)
        
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5  # Increased slightly for reliability
        
        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                print("[INIT] Windows DPI Awareness set.")
            except Exception as e:
                print(f"[WARN] Failed to set DPI awareness: {e}")
        
        self.screen_width, self.screen_height = pyautogui.size()

    def get_screen_map(self):
        """
        Atomic Tool: See.
        """
        try:
            start_time = time.time()
            
            # 1. Capture Screenshot
            screenshot = pyautogui.screenshot()
            
            # 2. Convert to CV2 format
            img_np = np.array(screenshot)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # 3. Downscale for speed (50% scale)
            scale_percent = 50
            width = int(img_cv.shape[1] * scale_percent / 100)
            height = int(img_cv.shape[0] * scale_percent / 100)
            dim = (width, height)
            resized_img = cv2.resize(img_cv, dim, interpolation=cv2.INTER_AREA)
            
            # 4. Run OCR
            results = self.reader.readtext(resized_img, detail=1)
            
            elements = []
            log_elements = [] # Plain text for debug file

            for (bbox, text, prob) in results:
                if prob < 0.4: continue 
                
                # Descale coordinates
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                center_x = int(((x1 + x2) / 2) * (100 / scale_percent))
                center_y = int(((y1 + y2) / 2) * (100 / scale_percent))
                
                # Sanity check bounds
                if center_x > self.screen_width or center_y > self.screen_height:
                    continue

                elements.append({
                    "text": text,
                    "x": center_x,
                    "y": center_y
                })
                log_elements.append(f"{text} ({center_x},{center_y})")
            
            duration = round(time.time() - start_time, 2)
            
            # Write what we saw to the debug file manually here as well
            # This helps debug OCR failures specifically
            try:
                with open("proxi_vision_debug.txt", "w", encoding="utf-8") as f:
                    f.write(f"Last Scan: {datetime.now()}\n")
                    f.write(f"Duration: {duration}s\n")
                    f.write(f"Elements Found: {len(elements)}\n")
                    f.write("\n".join(log_elements))
            except: 
                pass

            print(f"[DEBUG] Screen OCR: Found {len(elements)} elements in {duration}s")
            
            return json.dumps(elements, separators=(',', ':'))

        except Exception as e:
            print(f"[ERROR] Screen Map Error: {e}")
            return "[]"

    def click_at(self, x: int, y: int):
        try:
            pyautogui.moveTo(x, y, duration=0.3)
            pyautogui.click()
            return f"Clicked ({x}, {y})"
        except Exception as e:
            return f"Click Failed: {e}"

    def type_text(self, text: str):
        try:
            pyautogui.write(text, interval=0.05)
            return f"Typed '{text}'"
        except Exception as e:
            return f"Type Failed: {e}"

    def press_hotkey(self, keys: list):
        try:
            pyautogui.hotkey(*keys)
            return f"Pressed {'+'.join(keys)}"
        except Exception as e:
            return f"Hotkey Failed: {e}"

    def get_screen_size(self):
        return {"width": self.screen_width, "height": self.screen_height}
