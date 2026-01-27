import os
import platform

_mock_instance = None
_real_instance = None
_linux_instance = None

def get_desktop_service():
    global _mock_instance, _real_instance, _linux_instance
    
    # Default to DEMO mode for safety during Hackathon
    mode = os.getenv("RUNTIME_MODE", "DEMO")
    current_os = platform.system().lower()
    
    # On Linux/container, use LinuxDesktopService regardless of mode
    if current_os == "linux":
        if _linux_instance is None:
            from .linux import LinuxDesktopService
            _linux_instance = LinuxDesktopService()
        return _linux_instance
    
    # On Windows, respect RUNTIME_MODE
    if mode == "REAL":
        if _real_instance is None:
            from .real import RealDesktopService
            _real_instance = RealDesktopService()
        return _real_instance
    else:
        if _mock_instance is None:
            from .mock import MockDesktopService
            _mock_instance = MockDesktopService()
        return _mock_instance
