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


def get_desktop_service(agent_url: str = None, allow_local: bool = False):
    """
    Returns the appropriate DesktopService.
    
    Args:
        agent_url: Optional URL to proxy to a remote agent.
                   If None, uses local execution based on OS.
        allow_local: If True, allows local execution (for agent_server.py).
                     If False, requires agent selection (for Core).
    
    Returns:
        - ProxyDesktopService if agent_url provided or _active_agent_url set
        - LinuxDesktopService on Linux (if allow_local=True)
        - RealDesktopService on Windows (if allow_local=True)
        - NullDesktopService if no agent selected and allow_local=False
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
    
    # Local execution only allowed for agent_server.py
    if allow_local:
        current_os = platform.system().lower()
        if current_os == "linux":
            if _linux_instance is None:
                from .linux import LinuxDesktopService
                _linux_instance = LinuxDesktopService()
            return _linux_instance
        # Windows
        if _windows_instance is None:
            from .real import RealDesktopService
            _windows_instance = RealDesktopService()
        return _windows_instance
    
    # NO LOCAL EXECUTION for Core - require agent selection
    from .null import NullDesktopService
    return NullDesktopService()
