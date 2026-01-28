"""
Agent Proxy Service - Routes tool calls from Core to selected Agent.

Core (this server) orchestrates LLM interactions and proxies desktop tool
execution to isolated Proxi Agents via HTTP. This provides security isolation.
"""

import aiohttp
import asyncio
import os
from typing import Optional, Any
from backend.registry.workstation_registry import get_registry, get_workstation
from backend.utils.logger import log_system

# Agent API Key for Core <-> Agent authentication
AGENT_API_KEY = os.environ.get("PROXI_AGENT_KEY", "")


class AgentProxy:
    """
    Proxies desktop tool calls to the selected Proxi Agent.
    
    Usage:
        proxy = AgentProxy()
        result = await proxy.execute_tool("run_terminal_command", {"command": "ls"}, agent_id="linux-container")
    """
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self._active_agent_id: Optional[str] = None
    
    def set_active_agent(self, agent_id: str):
        """Set the currently active agent for tool execution."""
        self._active_agent_id = agent_id
        log_system(f"Active agent set to: {agent_id}", "PROXY")
    
    def get_active_agent(self) -> Optional[str]:
        """Get the currently active agent ID."""
        return self._active_agent_id
    
    def _get_agent_url(self, agent_id: Optional[str] = None) -> Optional[str]:
        """Get the base URL for an agent."""
        aid = agent_id or self._active_agent_id
        if not aid:
            log_system("No agent selected for tool execution", "WARN")
            return None
        
        ws = get_workstation(aid)
        if not ws:
            log_system(f"Agent not found: {aid}", "ERR")
            return None
        
        return f"http://{ws['host']}:{ws['port']}"
    
    async def execute_tool(self, tool_name: str, parameters: dict = None, agent_id: str = None) -> dict:
        """
        Execute a tool on the specified (or active) agent.
        
        Args:
            tool_name: Name of the tool to execute (e.g., "run_terminal_command")
            parameters: Tool parameters as dict
            agent_id: Optional agent ID (uses active agent if not specified)
        
        Returns:
            {"success": bool, "result": Any, "error": str or None}
        """
        base_url = self._get_agent_url(agent_id)
        if not base_url:
            return {"success": False, "result": None, "error": "No agent available"}
        
        url = f"{base_url}/execute"
        payload = {
            "tool_name": tool_name,
            "parameters": parameters or {}
        }
        
        headers = {}
        if AGENT_API_KEY:
            headers["X-Agent-Key"] = AGENT_API_KEY
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        log_system(f"Tool executed via agent: {tool_name}", "PROXY")
                        return data
                    else:
                        error_text = await response.text()
                        log_system(f"Agent error: {response.status} - {error_text}", "ERR")
                        return {"success": False, "result": None, "error": f"Agent returned {response.status}"}
        
        except aiohttp.ClientConnectorError:
            log_system(f"Agent unreachable: {base_url}", "ERR")
            return {"success": False, "result": None, "error": "Agent unreachable"}
        except asyncio.TimeoutError:
            log_system(f"Agent timeout: {base_url}", "ERR")
            return {"success": False, "result": None, "error": "Agent timeout"}
        except Exception as e:
            log_system(f"Proxy error: {e}", "ERR")
            return {"success": False, "result": None, "error": str(e)}
    
    async def get_agent_health(self, agent_id: str = None) -> dict:
        """Get health status from an agent."""
        base_url = self._get_agent_url(agent_id)
        if not base_url:
            return {"status": "error", "error": "No agent available"}
        
        headers = {"X-Agent-Key": AGENT_API_KEY} if AGENT_API_KEY else {}
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{base_url}/health", headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"status": "error", "error": f"Agent returned {response.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_agent_capabilities(self, agent_id: str = None) -> dict:
        """Get capabilities from an agent."""
        base_url = self._get_agent_url(agent_id)
        if not base_url:
            return {"capabilities": [], "error": "No agent available"}
        
        headers = {"X-Agent-Key": AGENT_API_KEY} if AGENT_API_KEY else {}
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{base_url}/capabilities", headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"capabilities": [], "error": f"Agent returned {response.status}"}
        except Exception as e:
            return {"capabilities": [], "error": str(e)}
    
    # --- Synchronous wrappers for GeminiService compatibility ---
    
    def execute_tool_sync(self, tool_name: str, parameters: dict = None, agent_id: str = None) -> Any:
        """Synchronous wrapper for execute_tool."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.execute_tool(tool_name, parameters, agent_id))
                result = future.result()
        else:
            result = loop.run_until_complete(self.execute_tool(tool_name, parameters, agent_id))
        
        if result.get("success"):
            return result.get("result")
        else:
            return {"error": result.get("error", "Unknown error")}


# Singleton instance
_proxy_instance: Optional[AgentProxy] = None

def get_agent_proxy() -> AgentProxy:
    """Get the singleton AgentProxy instance."""
    global _proxy_instance
    if _proxy_instance is None:
        _proxy_instance = AgentProxy()
    return _proxy_instance
