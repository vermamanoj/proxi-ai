
import datetime
import sys
import logging
from pathlib import Path

# Resolve path relative to this file
root_dir = Path(__file__).resolve().parent.parent.parent
DEBUG_LOG_PATH = root_dir / "proxi_debug.log"

# Configure Python logging to ensure output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("proxi")

def log_system(message: str, category: str = "INFO"):
    """
    Centralized logger that writes to stdout and a debug file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{category}] {message}"
    
    # Use logging module (works better with uvicorn)
    logger.info(formatted_msg)
    
    # Also force to stderr for visibility
    sys.stderr.write(formatted_msg + "\n")
    sys.stderr.flush()
    
    # Write to file for persistence
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception:
        pass
