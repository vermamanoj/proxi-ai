import platform

_windows_instance = None
_linux_instance = None

def get_desktop_service():
    """
    Returns the appropriate DesktopService based on OS.
    - Linux: LinuxDesktopService (terminal/file ops, no GUI)
    - Windows: RealDesktopService (full desktop automation)
    """
    global _windows_instance, _linux_instance
    
    current_os = platform.system().lower()
    
    if current_os == "linux":
        if _linux_instance is None:
            from .linux import LinuxDesktopService
            _linux_instance = LinuxDesktopService()
        return _linux_instance
    
    # Windows - always use real desktop service
    if _windows_instance is None:
        from .real import RealDesktopService
        _windows_instance = RealDesktopService()
    return _windows_instance
