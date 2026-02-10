"""
Proxy Adapter - DesktopService that routes calls to remote agents.

This implements the same interface as other DesktopServices but proxies
all calls to a remote Proxi Agent via HTTP. Used by Core when a remote
agent is selected.
"""

import aiohttp
import asyncio
import concurrent.futures
import os
from typing import Any, Optional
from backend.services.desktop.interface import DesktopInterface
from backend.utils.logger import log_system

# Agent API Key for Core <-> Agent authentication
AGENT_API_KEY = os.environ.get("PROXI_AGENT_KEY", "")


class ProxyDesktopService(DesktopInterface):
    """
    DesktopService implementation that proxies all calls to a remote agent.
    """
    
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def __init__(self, agent_url: str):
        """
        Args:
            agent_url: Base URL of the agent (e.g., "http://localhost:8081")
        """
        self.agent_url = agent_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=30)
        log_system(f"ProxyDesktopService initialized for: {agent_url}", "PROXY")
    
    def _execute_sync(self, tool_name: str, parameters: dict = None) -> Any:
        """Execute a tool call synchronously via the agent."""
        async def _call():
            url = f"{self.agent_url}/execute"
            payload = {"tool_name": tool_name, "parameters": parameters or {}}
            headers = {"X-Agent-Key": AGENT_API_KEY} if AGENT_API_KEY else {}
            
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("success"):
                                return data.get("result")
                            return {"error": data.get("error", "Unknown error")}
                        return {"error": f"Agent returned {response.status}"}
            except aiohttp.ClientConnectorError:
                return {"error": f"Agent unreachable: {self.agent_url}"}
            except asyncio.TimeoutError:
                return {"error": "Agent timeout"}
            except Exception as e:
                return {"error": str(e)}
        
        # Run async code synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = self._executor.submit(asyncio.run, _call())
                return future.result()
            else:
                return loop.run_until_complete(_call())
        except RuntimeError:
            return asyncio.run(_call())
    
    # --- DesktopInterface Implementation ---
    
    def get_system_health(self) -> dict:
        return self._execute_sync("get_system_health")
    
    def click_at(self, x: int, y: int) -> dict:
        return self._execute_sync("click_at", {"x": x, "y": y})
    
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
        return self._execute_sync("drag_mouse", {
            "start_x": start_x, "start_y": start_y,
            "end_x": end_x, "end_y": end_y
        })
    
    def type_text(self, text: str) -> dict:
        return self._execute_sync("type_text", {"text": text})
    
    def press_hotkey(self, keys: list) -> dict:
        return self._execute_sync("press_hotkey", {"keys": keys})
    
    def wait_seconds(self, seconds: int) -> dict:
        return self._execute_sync("wait_seconds", {"seconds": seconds})
    
    def run_terminal_command(self, command: str) -> dict:
        return self._execute_sync("run_terminal_command", {"command": command})
    
    def open_target(self, resource: str) -> dict:
        return self._execute_sync("open_target", {"target": resource})
    
    def read_page_content(self) -> dict:
        return self._execute_sync("read_page_content")
    
    def scroll_page(self, direction: str = "down") -> dict:
        return self._execute_sync("scroll_page", {"direction": direction})
    
    def browser_command(self, action: str, url: str = None) -> dict:
        return self._execute_sync("browser_command", {"action": action, "url": url})
    
    def scan_ui_tree(self) -> dict:
        return self._execute_sync("scan_ui_tree")
    
    def get_screenshot_base64(self) -> str:
        result = self._execute_sync("get_screenshot_base64")
        if isinstance(result, dict) and "error" in result:
            return None
        return result
    
    def get_observation(self, include_som: bool = True) -> dict:
        """Get combined observation from remote agent."""
        return self._execute_sync("get_observation", {"include_som": include_som})
    
    def focus_window(self, title: str) -> dict:
        return self._execute_sync("focus_window", {"title": title})
    
    def get_window_rect(self, title: str) -> dict:
        return self._execute_sync("get_window_rect", {"title": title})
    
    def list_windows(self) -> list:
        result = self._execute_sync("list_windows")
        if isinstance(result, dict):
            if "error" in result:
                return []
            # Agent returns {"windows": [...]} format
            if "windows" in result:
                return result["windows"]
        return result if isinstance(result, list) else []

    # --- PowerPoint Tools (proxied to Windows agent) ---
    
    def ppt_get_active_presentation(self) -> str:
        return self._execute_sync("ppt_get_active_presentation")
    
    def ppt_open_presentation(self, file_path: str) -> str:
        return self._execute_sync("ppt_open_presentation", {"file_path": file_path})
    
    def ppt_get_slide_info(self, slide_number: int = 0) -> str:
        return self._execute_sync("ppt_get_slide_info", {"slide_number": slide_number})
    
    def ppt_edit_text(self, slide_number: int, shape_name: str, new_text: str) -> str:
        return self._execute_sync("ppt_edit_text", {
            "slide_number": slide_number,
            "shape_name": shape_name,
            "new_text": new_text
        })
    
    def ppt_add_slide(self, after_slide: int = 0, layout: str = "title_content") -> str:
        return self._execute_sync("ppt_add_slide", {"after_slide": after_slide, "layout": layout})
    
    def ppt_duplicate_slide(self, slide_number: int) -> str:
        return self._execute_sync("ppt_duplicate_slide", {"slide_number": slide_number})
    
    def ppt_delete_slide(self, slide_number: int) -> str:
        return self._execute_sync("ppt_delete_slide", {"slide_number": slide_number})
    
    def ppt_save_presentation(self, save_as_path: str = None) -> str:
        return self._execute_sync("ppt_save_presentation", {"save_as_path": save_as_path})
    
    def ppt_goto_slide(self, slide_number: int) -> str:
        return self._execute_sync("ppt_goto_slide", {"slide_number": slide_number})
    
    def ppt_add_picture(self, slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400) -> str:
        return self._execute_sync("ppt_add_picture", {
            "slide_number": slide_number,
            "image_path": image_path,
            "left": left,
            "top": top,
            "width": width
        })
    
    def ppt_add_shape(self, slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = "") -> str:
        return self._execute_sync("ppt_add_shape", {
            "slide_number": slide_number,
            "shape_type": shape_type,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "text": text
        })
    
    def ppt_move_shape(self, slide_number: int, shape_name: str, left: int, top: int) -> str:
        return self._execute_sync("ppt_move_shape", {
            "slide_number": slide_number,
            "shape_name": shape_name,
            "left": left,
            "top": top
        })
    
    def ppt_resize_shape(self, slide_number: int, shape_name: str, width: int, height: int) -> str:
        return self._execute_sync("ppt_resize_shape", {
            "slide_number": slide_number,
            "shape_name": shape_name,
            "width": width,
            "height": height
        })
    
    def ppt_format_text(self, slide_number: int, shape_name: str, bold: bool = None, italic: bool = None,
                        font_size: int = None, font_color: str = None) -> str:
        return self._execute_sync("ppt_format_text", {
            "slide_number": slide_number,
            "shape_name": shape_name,
            "bold": bold,
            "italic": italic,
            "font_size": font_size,
            "font_color": font_color
        })
    
    def ppt_get_theme_colors(self, slide_number: int = 1) -> str:
        return self._execute_sync("ppt_get_theme_colors", {"slide_number": slide_number})
    
    def ppt_add_table(self, slide_number: int, rows: int, cols: int, data: list,
                      left: int = 50, top: int = 150, width: int = 600) -> str:
        return self._execute_sync("ppt_add_table", {
            "slide_number": slide_number, "rows": rows, "cols": cols,
            "data": data, "left": left, "top": top, "width": width
        })
    
    def ppt_set_shape_style(self, slide_number: int, shape_name: str, fill_color: str = None,
                            line_color: str = None, line_weight: float = None, transparency: float = None) -> str:
        return self._execute_sync("ppt_set_shape_style", {
            "slide_number": slide_number, "shape_name": shape_name,
            "fill_color": fill_color, "line_color": line_color,
            "line_weight": line_weight, "transparency": transparency
        })
    
    def ppt_add_textbox(self, slide_number: int, text: str, left: int, top: int,
                        width: int = 300, height: int = 50, font_size: int = None,
                        font_color: str = None, bold: bool = False, align: str = "left") -> str:
        return self._execute_sync("ppt_add_textbox", {
            "slide_number": slide_number, "text": text, "left": left, "top": top,
            "width": width, "height": height, "font_size": font_size,
            "font_color": font_color, "bold": bold, "align": align
        })
    
    def ppt_create_business_slide(self, slide_number: int, title: str, points: list, highlight_point: int = None) -> str:
        return self._execute_sync("ppt_create_business_slide", {
            "slide_number": slide_number, "title": title, "points": points, "highlight_point": highlight_point
        })
    
    # Visual elements - charts, images, icons, smartart
    def ppt_add_chart(self, slide_number: int, chart_type: str, data: list,
                      left: int = 100, top: int = 150, width: int = 500, height: int = 350, title: str = None) -> str:
        return self._execute_sync("ppt_add_chart", {
            "slide_number": slide_number, "chart_type": chart_type, "data": data,
            "left": left, "top": top, "width": width, "height": height, "title": title
        })
    
    def ppt_add_image_from_url(self, slide_number: int, image_url: str,
                               left: int = 100, top: int = 100, width: int = 400, alt_text: str = None) -> str:
        return self._execute_sync("ppt_add_image_from_url", {
            "slide_number": slide_number, "image_url": image_url,
            "left": left, "top": top, "width": width, "alt_text": alt_text
        })
    
    def ppt_add_icon(self, slide_number: int, icon_name: str,
                     left: int = 100, top: int = 100, size: int = 64, color: str = None) -> str:
        return self._execute_sync("ppt_add_icon", {
            "slide_number": slide_number, "icon_name": icon_name,
            "left": left, "top": top, "size": size, "color": color
        })
    
    def ppt_insert_smartart(self, slide_number: int, layout_type: str, items: list,
                            left: int = 100, top: int = 150, width: int = 600, height: int = 400) -> str:
        return self._execute_sync("ppt_insert_smartart", {
            "slide_number": slide_number, "layout_type": layout_type, "items": items,
            "left": left, "top": top, "width": width, "height": height
        })
