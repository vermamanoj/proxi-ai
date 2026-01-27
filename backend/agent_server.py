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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from backend.services.desktop.factory import get_desktop_service

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

# --- Health ---

@app.get("/")
async def root():
    return {
        "service": "proxi-agent",
        "status": "online",
        "platform": platform.system(),
        "hostname": platform.node()
    }

@app.get("/health")
async def health():
    """Health check with system metrics."""
    ds = get_desktop_service(allow_local=True)
    health_data = ds.get_system_health()
    return {
        "status": "healthy",
        "platform": platform.system(),
        "metrics": health_data
    }

# --- Tool Execution ---

@app.post("/execute", response_model=ToolResult)
async def execute_tool(call: ToolCall):
    """
    Execute a desktop tool. Called by Proxi Core.
    
    Supported tools depend on platform:
    - Linux: run_terminal_command, get_system_health, open_target, wait_seconds
    - Windows: All desktop automation tools
    """
    ds = get_desktop_service(allow_local=True)  # Agent always uses local execution
    tool_name = call.tool_name
    params = call.parameters
    
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
        elif tool_name == "scan_ui_tree":
            result = ds.scan_ui_tree()
        elif tool_name == "focus_window":
            result = ds.focus_window(params.get("title", ""))
        elif tool_name == "list_windows":
            result = ds.list_windows()
        else:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        
        return ToolResult(success=True, result=result)
    
    except Exception as e:
        return ToolResult(success=False, error=str(e))

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
