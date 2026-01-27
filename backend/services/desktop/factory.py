import platform
from typing import Optional

_windows_instance = None
_linux_instance = None
_proxy_instances = {}  # {agent_url: ProxyDesktopService}
_active_agent_url: Optional[str] = None


def set_active_agent(agent_url: str):
    """Set the active agent URL for proxied tool execution."""
    global _active_agent_url
    _active_agent_url = agent_url


def clear_active_agent():
    """Clear the active agent, use local execution."""
    global _active_agent_url
    _active_agent_url = None


def get_desktop_service(agent_url: str = None):
    """
    Returns the appropriate DesktopService.
    
    Args:
        agent_url: Optional URL to proxy to a remote agent.
                   If None, uses local execution based on OS.
    
    Returns:
        - ProxyDesktopService if agent_url provided or _active_agent_url set
        - LinuxDesktopService on Linux
        - RealDesktopService on Windows
    """
    global _windows_instance, _linux_instance, _proxy_instances, _active_agent_url
    
    # Use provided URL or active agent URL
    url = agent_url or _active_agent_url
    
    # If agent URL is set, use proxy to remote agent
    if url:
        if url not in _proxy_instances:
            from .proxy_adapter import ProxyDesktopService
            _proxy_instances[url] = ProxyDesktopService(url)
        return _proxy_instances[url]
    
    # NO LOCAL EXECUTION - Core should not act as an agent
    # User must select a registered agent before executing tools
    from .null import NullDesktopService
    return NullDesktopService()
