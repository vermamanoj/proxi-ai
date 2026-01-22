import pyautogui
import easyocr
import cv2
import numpy as np
import io
from PIL import Image
import os
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
        pyautogui.PAUSE = 0.5  # Add 0.5s cooldown after each PyAutoGUI call
        
        # Windows DPI Scaling Fix
        # This ensures that coordinates from screenshots match mouse coordinates
        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                print("Windows DPI Awareness set for accurate coordinate mapping.")
            except Exception as e:
                print(f"Warning: Failed to set DPI awareness: {e}")
        
        # Screen size
        self.screen_width, self.screen_height = pyautogui.size()

    def get_ui_manifest(self):
        """
        Captures screenshot, runs OCR, and returns a list of UI elements with coordinates.
        Optimization: Resizes image for faster OCR processing.
        """
        try:
            # 1. Capture Screenshot
            screenshot = pyautogui.screenshot()
            
            # 2. Convert to CV2 format for processing
            img_np = np.array(screenshot)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # 3. Downscale for speed (50% scale)
            scale_percent = 50
            width = int(img_cv.shape[1] * scale_percent / 100)
            height = int(img_cv.shape[0] * scale_percent / 100)
            dim = (width, height)
            
            # Resize image
            resized_img = cv2.resize(img_cv, dim, interpolation=cv2.INTER_AREA)
            
            # 4. Run OCR
            # detail=1 returns bounding box, text, and confidence
            results = self.reader.readtext(resized_img, detail=1)
            
            elements = []
            for (bbox, text, prob) in results:
                if prob < 0.4: continue # Filter low confidence
                
                # Map coordinates back to original screen size
                # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                
                # Descale
                center_x = int(((x1 + x2) / 2) * (100 / scale_percent))
                center_y = int(((y1 + y2) / 2) * (100 / scale_percent))
                
                elements.append({
                    "text": text,
                    "center": {"x": center_x, "y": center_y},
                    "confidence": float(prob)
                })
                
            return elements

        except Exception as e:
            print(f"UI Manifest Error: {e}")
            return []

    def execute_action(self, action_type: str, data: dict):
        """
        Executes the physical action on the desktop.
        """
        try:
            if action_type == "click":
                x = data.get("x")
                y = data.get("y")
                if x is not None and y is not None:
                    # Move duration allows visual tracking
                    pyautogui.moveTo(x, y, duration=0.5)
                    pyautogui.click()
                    return f"Clicked at ({x}, {y})"
            
            elif action_type == "type":
                text = data.get("text")
                if text:
                    # Interval mimics human typing speed
                    pyautogui.write(text, interval=0.05)
                    return f"Typed: '{text}'"
            
            elif action_type == "hotkey":
                keys = data.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)
                    return f"Pressed hotkey: {'+'.join(keys)}"
            
            return "Unknown action type"
        except Exception as e:
            return f"Action Execution Failed: {str(e)}"

    def get_screen_size(self):
        return {"width": self.screen_width, "height": self.screen_height}
