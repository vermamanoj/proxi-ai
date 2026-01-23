import pyautogui
import easyocr
import cv2
import numpy as np
import json
import platform
import ctypes
import time

class DesktopService:
    def __init__(self):
        # Initialize EasyOCR reader (loads model into memory)
        print("Initializing Desktop Ghost Operator (EasyOCR)...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        
        # PyAutoGUI safety & reliability settings
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.2  # Optimized for Flash (0.2s interval)
        
        # Windows DPI Scaling Fix
        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                print("Windows DPI Awareness set for accurate coordinate mapping.")
            except Exception as e:
                print(f"Warning: Failed to set DPI awareness: {e}")
        
        # Screen size
        self.screen_width, self.screen_height = pyautogui.size()

    def get_screen_map(self):
        """
        Atomic Tool: See.
        Captures screenshot, runs OCR, and returns a COMPACT JSON string of text elements.
        """
        try:
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
            for (bbox, text, prob) in results:
                if prob < 0.4: continue 
                
                # Descale coordinates
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                center_x = int(((x1 + x2) / 2) * (100 / scale_percent))
                center_y = int(((y1 + y2) / 2) * (100 / scale_percent))
                
                elements.append({
                    "text": text,
                    "x": center_x,
                    "y": center_y
                })
            
            # Return compact JSON string
            return json.dumps(elements, separators=(',', ':'))

        except Exception as e:
            print(f"Screen Map Error: {e}")
            return "[]"

    def click_at(self, x: int, y: int):
        """Atomic Tool: Click."""
        try:
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            return f"Clicked ({x}, {y})"
        except Exception as e:
            return f"Click Failed: {e}"

    def type_text(self, text: str):
        """Atomic Tool: Type."""
        try:
            pyautogui.write(text, interval=0.01)
            return f"Typed '{text}'"
        except Exception as e:
            return f"Type Failed: {e}"

    def press_hotkey(self, keys: list):
        """Atomic Tool: Hotkey."""
        try:
            pyautogui.hotkey(*keys)
            return f"Pressed {'+'.join(keys)}"
        except Exception as e:
            return f"Hotkey Failed: {e}"

    def get_screen_size(self):
        return {"width": self.screen_width, "height": self.screen_height}
