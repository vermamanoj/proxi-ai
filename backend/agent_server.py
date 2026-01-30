"""
Proxi Agent Server - Lightweight desktop automation endpoint.

This runs SEPARATELY from Proxi Core for security isolation.
- No access to user DB, sessions, or API keys
- Only executes desktop operations
- Receives commands from Proxi Core via HTTP

Run: uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
"""

import uvicorn
import platform
import os

# Load .env file if present (for GEMINI_API_KEY on Windows agents)
# Try multiple locations - load ALL found .env files (later ones override)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Load in order: repo root first, then script dir, then cwd (last wins)
    env_locations = [
        repo_root / ".env",      # E:\data\proxi-win-agent\.env
        script_dir / ".env",     # E:\data\proxi-win-agent\backend\.env
        Path.cwd() / ".env",     # Current working directory
    ]
    
    loaded_from = None
    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            loaded_from = env_path
    
    # Log result
    if os.environ.get("GEMINI_API_KEY"):
        print(f"[AGENT] GEMINI_API_KEY loaded from: {loaded_from or 'environment'}")
    else:
        print(f"[AGENT] WARNING: GEMINI_API_KEY not found - checked: {[str(p) for p in env_locations]}")
except ImportError:
    print("[AGENT] python-dotenv not installed - .env file not loaded")
import json
import time
import uuid
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from backend.services.desktop.factory import get_desktop_service
from backend.tools.ppt_tools import (
    ppt_get_active_presentation,
    ppt_open_presentation,
    ppt_get_slide_info,
    ppt_edit_text,
    ppt_add_slide,
    ppt_duplicate_slide,
    ppt_delete_slide,
    ppt_save_presentation,
    ppt_goto_slide,
    ppt_add_picture,
    ppt_add_shape,
    ppt_move_shape,
    ppt_resize_shape,
    ppt_format_text,
    ppt_get_theme_colors,
    # Advanced PPT tools
    ppt_add_table,
    ppt_add_textbox,
    ppt_set_shape_style,
    ppt_create_business_slide,
)

# Agent API Key for Core <-> Agent authentication
# Set via PROXI_AGENT_KEY env var or pass at startup
AGENT_API_KEY = os.environ.get("PROXI_AGENT_KEY", "")

app = FastAPI(
    title="Proxi Agent",
    description="Isolated desktop automation agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict = {}

class ToolResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None


def _sanitize_params(params: dict, max_value_len: int = 200) -> dict:
    if not isinstance(params, dict):
        return {"_": str(params)[:max_value_len]}
    redacted_keys = {
        "content_base64",
        "screenshot",
        "image",
        "data",
        "file",
        "bytes",
        "api_key",
        "token",
        "password",
        "secret",
        "key",
    }
    out: dict = {}
    for k, v in params.items():
        lk = str(k).lower()
        if lk in redacted_keys or any(rk in lk for rk in ["password", "secret", "token", "api_key", "content_base64"]):
            if isinstance(v, str):
                out[k] = f"<redacted len={len(v)}>"
            else:
                out[k] = "<redacted>"
            continue
        if isinstance(v, str) and len(v) > max_value_len:
            out[k] = v[:max_value_len] + "..."
        else:
            out[k] = v
    return out


def _preview(value: Any, max_len: int = 220) -> str:
    try:
        if value is None:
            return "null"
        if isinstance(value, (bool, int, float)):
            return str(value)
        if isinstance(value, str):
            s = value.replace("\n", "\\n")
            return s if len(s) <= max_len else s[:max_len] + "..."
        if isinstance(value, dict):
            s = json.dumps(_sanitize_params(value, max_value_len=80), ensure_ascii=True)
            return s if len(s) <= max_len else s[:max_len] + "..."
        if isinstance(value, list):
            s = json.dumps(value[:3], ensure_ascii=True)
            if len(value) > 3:
                s = s[:-1] + ', "..." ]'
            return s if len(s) <= max_len else s[:max_len] + "..."
        s = str(value)
        return s if len(s) <= max_len else s[:max_len] + "..."
    except Exception:
        return "<unprintable>"

# --- Health ---

@app.get("/")
async def root():
    return {
        "service": "proxi-agent",
        "status": "online",
        "platform": platform.system(),
        "hostname": platform.node()
    }

# --- Authentication ---

async def verify_agent_key(x_agent_key: Optional[str] = Header(None)):
    """Verify the agent API key if one is configured."""
    if AGENT_API_KEY and x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing agent key")
    return True

# --- Health Check ---

@app.get("/health")
async def health(_: bool = Depends(verify_agent_key)):
    """Health check with system metrics. Requires agent key if configured."""
    ds = get_desktop_service(allow_local=True)
    health_data = ds.get_system_health()
    return {
        "status": "healthy",
        "platform": platform.system(),
        "metrics": health_data
    }

# --- Tool Execution ---


@app.post("/execute", response_model=ToolResult)
async def execute_tool(call: ToolCall, _: bool = Depends(verify_agent_key)):
    """
    Execute a desktop tool. Called by Proxi Core.
    
    Supported tools depend on platform:
    - Linux: run_terminal_command, get_system_health, open_target, wait_seconds
    - Windows: All desktop automation tools
    """
    ds = get_desktop_service(allow_local=True)  # Agent always uses local execution
    tool_name = call.tool_name
    params = call.parameters

    req_id = uuid.uuid4().hex[:8]
    start_time = time.time()
    try:
        params_preview = json.dumps(_sanitize_params(params), ensure_ascii=True)
    except Exception:
        params_preview = "{}"
    print(f"[AGENT_EXEC] START id={req_id} tool={tool_name} params={params_preview}", flush=True)
    
    try:
        # Map tool names to service methods
        if tool_name == "run_terminal_command":
            result = ds.run_terminal_command(params.get("command", ""))
        elif tool_name == "get_system_health":
            result = ds.get_system_health()
        elif tool_name == "open_target":
            result = ds.open_target(params.get("target", ""))
        elif tool_name == "wait_seconds":
            result = ds.wait_seconds(params.get("seconds", 1))
        elif tool_name == "click_at":
            result = ds.click_at(params.get("x", 0), params.get("y", 0))
        elif tool_name == "type_text":
            result = ds.type_text(params.get("text", ""))
        elif tool_name == "press_hotkey":
            result = ds.press_hotkey(params.get("keys", []))
        elif tool_name == "get_screenshot_base64":
            result = ds.get_screenshot_base64()
        elif tool_name == "get_observation":
            result = ds.get_observation(params.get("include_som", True))
        elif tool_name == "scan_ui_tree":
            result = ds.scan_ui_tree()
        elif tool_name == "focus_window":
            result = ds.focus_window(params.get("title", ""))
        elif tool_name == "list_windows":
            result = ds.list_windows()
        elif tool_name == "drag_mouse":
            result = ds.drag_mouse(params.get("start_x", 0), params.get("start_y", 0),
                                   params.get("end_x", 0), params.get("end_y", 0))
        elif tool_name == "get_window_rect":
            result = ds.get_window_rect(params.get("title", ""))
        elif tool_name == "read_page_content":
            result = ds.read_page_content()
        elif tool_name == "scroll_page":
            result = ds.scroll_page(params.get("direction", "down"))
        elif tool_name == "browser_command":
            result = ds.browser_command(params.get("action", ""), params.get("url"))
        # PowerPoint Tools (execute locally on Windows agent)
        elif tool_name == "ppt_get_active_presentation":
            result = ppt_get_active_presentation()
        elif tool_name == "ppt_open_presentation":
            result = ppt_open_presentation(params.get("file_path", ""))
        elif tool_name == "ppt_get_slide_info":
            result = ppt_get_slide_info(int(params.get("slide_number", 0)))
        elif tool_name == "ppt_edit_text":
            result = ppt_edit_text(
                int(params.get("slide_number", 1)),
                params.get("shape_name", ""),
                params.get("new_text", "")
            )
        elif tool_name == "ppt_add_slide":
            result = ppt_add_slide(
                int(params.get("after_slide", 0)),
                params.get("layout", "title_content")
            )
        elif tool_name == "ppt_duplicate_slide":
            result = ppt_duplicate_slide(int(params.get("slide_number", 1)))
        elif tool_name == "ppt_delete_slide":
            result = ppt_delete_slide(int(params.get("slide_number", 1)))
        elif tool_name == "ppt_save_presentation":
            result = ppt_save_presentation(params.get("save_as_path"))
        elif tool_name == "ppt_goto_slide":
            result = ppt_goto_slide(int(params.get("slide_number", 1)))
        elif tool_name == "ppt_add_picture":
            result = ppt_add_picture(
                int(params.get("slide_number", 1)),
                params.get("image_path", ""),
                int(params.get("left", 100)),
                int(params.get("top", 100)),
                int(params.get("width", 400))
            )
        elif tool_name == "ppt_add_shape":
            result = ppt_add_shape(
                int(params.get("slide_number", 1)),
                params.get("shape_type", "rectangle"),
                int(params.get("left", 100)),
                int(params.get("top", 100)),
                int(params.get("width", 100)),
                int(params.get("height", 100)),
                params.get("text", "")
            )
        elif tool_name == "ppt_move_shape":
            result = ppt_move_shape(
                int(params.get("slide_number", 1)),
                params.get("shape_name", ""),
                int(params.get("left", 0)),
                int(params.get("top", 0))
            )
        elif tool_name == "ppt_resize_shape":
            result = ppt_resize_shape(
                int(params.get("slide_number", 1)),
                params.get("shape_name", ""),
                int(params.get("width", 100)),
                int(params.get("height", 100))
            )
        elif tool_name == "ppt_format_text":
            result = ppt_format_text(
                int(params.get("slide_number", 1)),
                params.get("shape_name", ""),
                params.get("bold"),
                params.get("italic"),
                params.get("font_size"),
                params.get("font_color")
            )
        elif tool_name == "ppt_get_theme_colors":
            result = ppt_get_theme_colors(int(params.get("slide_number", 1)))
        # Advanced PPT tools
        elif tool_name == "ppt_add_table":
            result = ppt_add_table(
                int(params.get("slide_number", 1)),
                int(params.get("rows", 3)),
                int(params.get("cols", 3)),
                params.get("data", []),
                int(params.get("left", 50)),
                int(params.get("top", 150)),
                int(params.get("width", 600))
            )
        elif tool_name == "ppt_add_textbox":
            result = ppt_add_textbox(
                int(params.get("slide_number", 1)),
                params.get("text", ""),
                int(params.get("left", 100)),
                int(params.get("top", 100)),
                int(params.get("width", 300)),
                int(params.get("height", 50)),
                params.get("font_size"),
                params.get("font_color"),
                params.get("bold", False),
                params.get("align", "left")
            )
        elif tool_name == "ppt_set_shape_style":
            result = ppt_set_shape_style(
                int(params.get("slide_number", 1)),
                params.get("shape_name", ""),
                params.get("fill_color"),
                params.get("line_color"),
                params.get("line_weight"),
                params.get("transparency")
            )
        elif tool_name == "ppt_create_business_slide":
            result = ppt_create_business_slide(
                int(params.get("slide_number", 1)),
                params.get("title", ""),
                params.get("points", []),
                params.get("highlight_point")
            )
        else:
            elapsed_ms = int((time.time() - start_time) * 1000)
            err = f"Unknown tool: {tool_name}"
            print(f"[AGENT_EXEC] END id={req_id} tool={tool_name} ok=0 ms={elapsed_ms} error={_preview(err)}", flush=True)
            return ToolResult(success=False, error=err)

        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"[AGENT_EXEC] END id={req_id} tool={tool_name} ok=1 ms={elapsed_ms} result={_preview(result)}", flush=True)
        return ToolResult(success=True, result=result)

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"[AGENT_EXEC] END id={req_id} tool={tool_name} ok=0 ms={elapsed_ms} error={_preview(str(e))}", flush=True)
        return ToolResult(success=False, error=str(e))

class FileDownloadRequest(BaseModel):
    file_path: str

class FileDownloadResponse(BaseModel):
    success: bool
    filename: str = ""
    content_base64: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    error: str = ""

class FileUploadRequest(BaseModel):
    file_path: str
    content_base64: str
    filename: str = ""

@app.post("/files/download", response_model=FileDownloadResponse)
async def download_file(request: FileDownloadRequest, _: bool = Depends(verify_agent_key)):
    """Download a file from the agent's filesystem as Base64."""
    import base64
    import mimetypes
    
    file_path = os.path.expanduser(request.file_path)
    file_path = os.path.expandvars(file_path)
    
    if not os.path.exists(file_path):
        return FileDownloadResponse(success=False, error=f"File not found: {file_path}")
    
    if not os.path.isfile(file_path):
        return FileDownloadResponse(success=False, error=f"Not a file: {file_path}")
    
    # Limit file size to 50MB for base64 transfer
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        return FileDownloadResponse(success=False, error=f"File too large: {file_size} bytes (max 50MB)")
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        content_b64 = base64.b64encode(content).decode('utf-8')
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return FileDownloadResponse(
            success=True,
            filename=os.path.basename(file_path),
            content_base64=content_b64,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=file_size
        )
    except Exception as e:
        return FileDownloadResponse(success=False, error=str(e))

@app.post("/files/upload")
async def upload_file(request: FileUploadRequest, _: bool = Depends(verify_agent_key)):
    """Upload a file to the agent's filesystem from Base64."""
    import base64
    
    file_path = os.path.expanduser(request.file_path)
    file_path = os.path.expandvars(file_path)
    
    # Security: prevent writing outside user directories
    home = os.path.expanduser("~")
    if not file_path.startswith(home) and not file_path.startswith("/tmp"):
        return {"success": False, "error": "Can only write to home directory or /tmp"}
    
    try:
        content = base64.b64decode(request.content_base64)
        
        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {"success": True, "path": file_path, "size_bytes": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- Visual Grounding with Local Gemini ---

class GroundRequest(BaseModel):
    """Request for visual grounding - find element coordinates from description."""
    query: str  # e.g., "Find the Submit button" or "Click element 5"
    include_som: bool = True  # Include Set-of-Mark overlay
    
class GroundResponse(BaseModel):
    success: bool
    action: Optional[str] = None  # "click", "type", "scroll", etc.
    x: Optional[int] = None
    y: Optional[int] = None
    element_id: Optional[int] = None
    element_text: Optional[str] = None
    confidence: Optional[str] = None  # "high", "medium", "low"
    reasoning: Optional[str] = None
    error: Optional[str] = None

@app.post("/ground", response_model=GroundResponse)
async def visual_ground(request: GroundRequest, _: bool = Depends(verify_agent_key)):
    """
    Visual grounding endpoint - uses local Gemini to find UI elements.
    
    This allows the agent to interpret screenshots locally without
    round-tripping to Core, significantly improving performance.
    
    Requires GEMINI_API_KEY environment variable on the agent.
    """
    import base64
    
    # Check for Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return GroundResponse(
            success=False,
            error="GEMINI_API_KEY not configured on agent. Visual grounding unavailable."
        )
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except ImportError:
        return GroundResponse(
            success=False,
            error="google-generativeai not installed on agent"
        )
    
    ds = get_desktop_service(allow_local=True)
    
    # Get observation with SoM
    obs = ds.get_observation(include_som=request.include_som)
    if "error" in obs:
        return GroundResponse(success=False, error=obs["error"])
    
    # Build element list for context
    elements_desc = ""
    if obs.get("ui_elements"):
        elements_desc = "Available UI elements:\n"
        for elem in obs["ui_elements"][:50]:  # Limit to 50
            elements_desc += f"[{elem['id']}] {elem['type']}: \"{elem['text']}\" at ({elem['x']}, {elem['y']})\n"
    
    # Use the SoM screenshot if available, otherwise raw
    img_b64 = obs.get("som_screenshot_base64") or obs.get("screenshot_base64")
    if not img_b64:
        return GroundResponse(success=False, error="Failed to capture screenshot")
    
    # Build prompt for Gemini
    prompt = f"""You are a visual grounding assistant. Analyze the screenshot and find the UI element matching this query:

QUERY: {request.query}

{elements_desc}

The screenshot has numbered green boxes around interactive elements (Set-of-Mark).

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "action": "click",  // or "type", "scroll_down", "scroll_up", "none"
    "element_id": 5,    // The [N] number from the green box, or null
    "x": 500,           // Center X coordinate to click
    "y": 300,           // Center Y coordinate to click  
    "element_text": "Submit",  // Text of the element
    "confidence": "high",      // "high", "medium", or "low"
    "reasoning": "Found Submit button labeled [5] in the form"
}}

If you cannot find the element, set action to "none" and explain in reasoning.
ONLY output the JSON, no other text."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': base64.b64decode(img_b64)}
        ])
        
        # Parse response
        import json
        import re
        
        text = response.text.strip()
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            
            return GroundResponse(
                success=True,
                action=result.get("action"),
                x=result.get("x"),
                y=result.get("y"),
                element_id=result.get("element_id"),
                element_text=result.get("element_text"),
                confidence=result.get("confidence"),
                reasoning=result.get("reasoning")
            )
        else:
            return GroundResponse(
                success=False,
                error=f"Could not parse Gemini response: {text[:200]}"
            )
            
    except Exception as e:
        return GroundResponse(success=False, error=f"Gemini error: {str(e)}")


@app.get("/capabilities")
async def get_capabilities():
    """List available tools on this agent."""
    ds = get_desktop_service(allow_local=True)
    
    # Check what's available
    capabilities = []
    test_methods = [
        ("run_terminal_command", "terminal"),
        ("get_system_health", "system_health"),
        ("click_at", "mouse"),
        ("type_text", "keyboard"),
        ("get_screenshot_base64", "screenshot"),
        ("scan_ui_tree", "ui_automation"),
    ]
    
    for method, cap in test_methods:
        if hasattr(ds, method):
            # For Linux, check if method returns "not_available"
            if platform.system().lower() == "linux" and cap in ["mouse", "keyboard", "screenshot", "ui_automation"]:
                continue
            capabilities.append(cap)
    
    return {
        "platform": platform.system(),
        "capabilities": capabilities
    }

# --- Demo Tools (for simulating incidents) ---

@app.post("/demo/trigger_incident")
async def trigger_incident():
    """Simulate a high-CPU incident for demo purposes."""
    ds = get_desktop_service(allow_local=True)
    if hasattr(ds, 'trigger_incident'):
        ds.trigger_incident()
        return {"status": "triggered", "message": "Simulated incident started"}
    return {"status": "not_supported"}

@app.post("/demo/resolve_incident")
async def resolve_incident():
    """Resolve simulated incident."""
    ds = get_desktop_service(allow_local=True)
    if hasattr(ds, 'resolve_incident'):
        ds.resolve_incident()
        return {"status": "resolved"}
    return {"status": "not_supported"}

if __name__ == "__main__":
    uvicorn.run("backend.agent_server:app", host="0.0.0.0", port=8081, reload=True)
