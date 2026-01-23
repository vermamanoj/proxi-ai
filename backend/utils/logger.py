
import datetime
from pathlib import Path

# Resolve path relative to this file
root_dir = Path(__file__).resolve().parent.parent.parent
DEBUG_LOG_PATH = root_dir / "proxi_debug.log"

def log_system(message: str, category: str = "INFO"):
    """
    Centralized logger that writes to stdout and a debug file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{category}] {message}"
    
    # Print to console for Docker logs
    print(formatted_msg, flush=True)
    
    # Write to file for persistence
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception:
        pass
