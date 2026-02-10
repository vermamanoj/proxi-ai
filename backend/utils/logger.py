
import datetime
import sys
import os
from pathlib import Path

# Resolve path - use /app/data in Docker for persistence
DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parent.parent.parent
DEBUG_LOG_PATH = DATA_DIR / "proxi_debug.log"

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

def log_system(message: str, category: str = "INFO"):
    """
    Centralized logger that writes to stdout and a debug file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{category}] {message}"
    
    # Print directly - uvicorn captures stdout
    print(formatted_msg, file=sys.stdout, flush=True)
    
    # Write to file for persistence (with size-based rotation)
    try:
        # Rotate if log exceeds 10MB
        if DEBUG_LOG_PATH.exists() and DEBUG_LOG_PATH.stat().st_size > 10 * 1024 * 1024:
            for i in range(2, 0, -1):
                src = DEBUG_LOG_PATH.with_suffix(f".log.{i}")
                dst = DEBUG_LOG_PATH.with_suffix(f".log.{i+1}")
                if src.exists():
                    src.rename(dst)
            DEBUG_LOG_PATH.rename(DEBUG_LOG_PATH.with_suffix(".log.1"))
        
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception:
        pass
