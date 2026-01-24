import os

_mock_instance = None
_real_instance = None

def get_desktop_service():
    global _mock_instance, _real_instance
    
    # Default to DEMO mode for safety during Hackathon
    mode = os.getenv("RUNTIME_MODE", "DEMO")
    
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
