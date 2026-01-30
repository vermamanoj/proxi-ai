#!/usr/bin/env python3
"""
Proxi Agent for Forensic Investigation Container
Minimal agent server for Gemini to execute commands in the forensic environment
"""
import os
import platform
import subprocess
import psutil
import json
import time
import uuid
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI(title="Proxi Forensic Agent")

# Agent authentication
AGENT_API_KEY = os.getenv("PROXI_AGENT_KEY", "")

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict

class ToolResult(BaseModel):
    success: bool
    result: str  # Must be 'result' to match ProxyDesktopService expectation
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


def _preview(value: object, max_len: int = 220) -> str:
    try:
        if value is None:
            return "null"
        if isinstance(value, (bool, int, float)):
            return str(value)
        if isinstance(value, str):
            s = value.replace("\n", "\\n")
            s = s.encode("ascii", "backslashreplace").decode("ascii")
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
        s = s.encode("ascii", "backslashreplace").decode("ascii")
        return s if len(s) <= max_len else s[:max_len] + "..."
    except Exception:
        return "<unprintable>"

# --- Authentication ---

async def verify_agent_key(x_agent_key: Optional[str] = Header(None)):
    """Verify the agent API key if one is configured."""
    if AGENT_API_KEY and x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing agent key")
    return True

# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "service": "proxi-forensic-agent",
        "status": "online",
        "platform": platform.system(),
        "hostname": platform.node(),
        "purpose": "SOC Forensic Investigation Training"
    }

@app.get("/health")
async def health(_: bool = Depends(verify_agent_key)):
    """Health check with system metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "status": "healthy",
        "platform": platform.system(),
        "hostname": platform.node(),
        "metrics": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "uptime_seconds": int(psutil.boot_time())
        }
    }

@app.get("/capabilities")
async def capabilities(_: bool = Depends(verify_agent_key)):
    """Return available tools for this agent."""
    return {
        "tools": [
            {
                "name": "run_terminal_command",
                "description": "Execute shell commands for forensic investigation",
                "parameters": ["command", "timeout"]
            },
            {
                "name": "read_file",
                "description": "Read file contents (logs, configs, artifacts)",
                "parameters": ["file_path", "max_lines"]
            },
            {
                "name": "search_logs",
                "description": "Search log files with grep",
                "parameters": ["pattern", "log_path"]
            },
            {
                "name": "list_processes",
                "description": "List running processes",
                "parameters": []
            },
            {
                "name": "network_connections",
                "description": "Show active network connections",
                "parameters": []
            },
            {
                "name": "get_system_health",
                "description": "Get system health metrics (CPU, memory, disk, uptime)",
                "parameters": []
            }
        ]
    }

@app.post("/execute", response_model=ToolResult)
async def execute_tool(call: ToolCall, _: bool = Depends(verify_agent_key)):
    """Execute a forensic investigation tool."""
    req_id = uuid.uuid4().hex[:8]
    start_time = time.time()
    try:
        params_preview = json.dumps(_sanitize_params(call.parameters), ensure_ascii=True)
    except Exception:
        params_preview = "{}"
    print(f"[AGENT_EXEC] START id={req_id} tool={call.tool_name} params={params_preview}", flush=True)

    try:
        if call.tool_name == "run_terminal_command":
            result = execute_command(call.parameters)
        elif call.tool_name == "read_file":
            result = read_file(call.parameters)
        elif call.tool_name == "search_logs":
            result = search_logs(call.parameters)
        elif call.tool_name == "list_processes":
            result = list_processes()
        elif call.tool_name == "network_connections":
            result = network_connections()
        elif call.tool_name == "get_system_health":
            result = get_system_health()
        else:
            result = ToolResult(
                success=False,
                result="",
                error=f"Unknown tool: {call.tool_name}"
            )
        elapsed_ms = int((time.time() - start_time) * 1000)
        ok = 1 if getattr(result, "success", False) else 0
        print(
            f"[AGENT_EXEC] END id={req_id} tool={call.tool_name} ok={ok} ms={elapsed_ms} "
            f"result={_preview(getattr(result, 'result', ''))} error={_preview(getattr(result, 'error', None))}",
            flush=True
        )
        return result
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"[AGENT_EXEC] END id={req_id} tool={call.tool_name} ok=0 ms={elapsed_ms} error={_preview(str(e))}", flush=True)
        return ToolResult(
            success=False,
            result="",
            error=f"Tool execution failed: {str(e)}"
        )

# --- Security: Blocked paths and patterns ---
BLOCKED_PATHS = [
    '/etc/passwd', '/etc/shadow', '/etc/sudoers', '/etc/gshadow',
    '/root/.ssh', '/root/.bash_history', '/root/.bashrc',
    '/proc/1/environ', '/proc/self/environ',
]

BLOCKED_PATTERNS = [
    'passwd', 'shadow', 'sudoers',  # Direct file access
    '/root/', '~root',  # Root home directory
    'chmod 777', 'chmod +s',  # Dangerous permissions
    'curl|bash', 'wget|sh',  # Download and execute
]

def is_command_blocked(command: str) -> tuple[bool, str]:
    """Check if command accesses restricted paths or patterns."""
    cmd_lower = command.lower().strip()
    
    # Check for blocked paths
    for blocked in BLOCKED_PATHS:
        if blocked in cmd_lower:
            return True, f"Access to {blocked} is restricted for security training"
    
    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            return True, f"Command pattern '{pattern}' is restricted"
    
    return False, ""

# --- Tool Implementations ---

def execute_command(params: dict) -> ToolResult:
    """Execute a shell command."""
    command = params.get("command", "")
    timeout = params.get("timeout", 30)
    
    if not command:
        return ToolResult(success=False, result="", error="No command provided")
    
    # Security check
    blocked, reason = is_command_blocked(command)
    if blocked:
        return ToolResult(success=False, result="", error=f"🔒 BLOCKED: {reason}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return ToolResult(
            success=result.returncode == 0,
            result=result.stdout + result.stderr,
            error=None if result.returncode == 0 else f"Exit code: {result.returncode}"
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, result="", error="Command timeout")
    except Exception as e:
        return ToolResult(success=False, result="", error=str(e))

def read_file(params: dict) -> ToolResult:
    """Read file contents."""
    file_path = params.get("file_path", "")
    max_lines = params.get("max_lines", 100)
    
    if not file_path:
        return ToolResult(success=False, result="", error="No file path provided")
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()[:max_lines]
            content = ''.join(lines)
        
        return ToolResult(
            success=True,
            result=f"File: {file_path}\n{content}",
            error=None
        )
    except FileNotFoundError:
        return ToolResult(success=False, result="", error=f"File not found: {file_path}")
    except Exception as e:
        return ToolResult(success=False, result="", error=str(e))

def search_logs(params: dict) -> ToolResult:
    """Search log files with grep."""
    pattern = params.get("pattern", "")
    log_path = params.get("log_path", "/var/log/messages")
    
    if not pattern:
        return ToolResult(success=False, result="", error="No search pattern provided")
    
    command = f"grep -i '{pattern}' {log_path}"
    return execute_command({"command": command, "timeout": 10})

def list_processes() -> ToolResult:
    """List running processes."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu': proc.info['cpu_percent'],
                    'memory': proc.info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu'] or 0, reverse=True)
        
        output = "PID\tNAME\t\tCPU%\tMEM%\n"
        output += "-" * 50 + "\n"
        for p in processes[:20]:  # Top 20 processes
            output += f"{p['pid']}\t{p['name'][:15]}\t{p['cpu']:.1f}\t{p['memory']:.1f}\n"
        
        return ToolResult(success=True, result=output, error=None)
    except Exception as e:
        return ToolResult(success=False, result="", error=str(e))

def network_connections() -> ToolResult:
    """Show active network connections."""
    command = "ss -tunap 2>/dev/null || netstat -tunap 2>/dev/null"
    return execute_command({"command": command, "timeout": 10})


def get_system_health() -> ToolResult:
    """Get system health metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        
        output = f"""=== System Health Report ===
Hostname: {platform.node()}
Platform: {platform.system()} {platform.release()}

CPU Usage: {cpu_percent}%
Load Average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}

Memory:
  Total: {memory.total // (1024**3)} GB
  Used: {memory.used // (1024**3)} GB ({memory.percent}%)
  Available: {memory.available // (1024**3)} GB

Disk (/):
  Total: {disk.total // (1024**3)} GB
  Used: {disk.used // (1024**3)} GB ({disk.percent}%)
  Free: {disk.free // (1024**3)} GB
"""
        return ToolResult(success=True, result=output, error=None)
    except Exception as e:
        return ToolResult(success=False, result="", error=str(e))


if __name__ == "__main__":
    import uvicorn
    print("[FORENSIC AGENT] Starting Proxi Forensic Agent on port 8081...")
    print(f"[FORENSIC AGENT] Agent key configured: {bool(AGENT_API_KEY)}")
    uvicorn.run(app, host="0.0.0.0", port=8081)
