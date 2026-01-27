"""
Proxy Adapter - DesktopService that routes calls to remote agents.

This implements the same interface as other DesktopServices but proxies
all calls to a remote Proxi Agent via HTTP. Used by Core when a remote
agent is selected.
"""

import aiohttp
import asyncio
from typing import Any, Optional
from backend.services.desktop.interface import DesktopInterface
from backend.utils.logger import log_system


class ProxyDesktopService(DesktopInterface):
    """
    DesktopService implementation that proxies all calls to a remote agent.
    """
    
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
            
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(url, json=payload) as response:
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
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _call())
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
    
    def focus_window(self, title: str) -> dict:
        return self._execute_sync("focus_window", {"title": title})
    
    def get_window_rect(self, title: str) -> dict:
        return self._execute_sync("get_window_rect", {"title": title})
    
    def list_windows(self) -> list:
        result = self._execute_sync("list_windows")
        if isinstance(result, dict) and "error" in result:
            return []
        return result if isinstance(result, list) else []
