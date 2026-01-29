#!/usr/bin/env python3
"""
Proxi Agent for Forensic Investigation Container
Minimal agent server for Gemini to execute commands in the forensic environment
"""
import os
import platform
import subprocess
import psutil
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
    output: str
    error: Optional[str] = None

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
            }
        ]
    }

@app.post("/execute", response_model=ToolResult)
async def execute_tool(call: ToolCall, _: bool = Depends(verify_agent_key)):
    """Execute a forensic investigation tool."""
    try:
        if call.tool_name == "run_terminal_command":
            return execute_command(call.parameters)
        elif call.tool_name == "read_file":
            return read_file(call.parameters)
        elif call.tool_name == "search_logs":
            return search_logs(call.parameters)
        elif call.tool_name == "list_processes":
            return list_processes()
        elif call.tool_name == "network_connections":
            return network_connections()
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {call.tool_name}"
            )
    except Exception as e:
        return ToolResult(
            success=False,
            output="",
            error=f"Tool execution failed: {str(e)}"
        )

# --- Tool Implementations ---

def execute_command(params: dict) -> ToolResult:
    """Execute a shell command."""
    command = params.get("command", "")
    timeout = params.get("timeout", 30)
    
    if not command:
        return ToolResult(success=False, output="", error="No command provided")
    
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
            output=result.stdout + result.stderr,
            error=None if result.returncode == 0 else f"Exit code: {result.returncode}"
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error="Command timeout")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))

def read_file(params: dict) -> ToolResult:
    """Read file contents."""
    file_path = params.get("file_path", "")
    max_lines = params.get("max_lines", 100)
    
    if not file_path:
        return ToolResult(success=False, output="", error="No file path provided")
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()[:max_lines]
            content = ''.join(lines)
        
        return ToolResult(
            success=True,
            output=f"File: {file_path}\n{content}",
            error=None
        )
    except FileNotFoundError:
        return ToolResult(success=False, output="", error=f"File not found: {file_path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))

def search_logs(params: dict) -> ToolResult:
    """Search log files with grep."""
    pattern = params.get("pattern", "")
    log_path = params.get("log_path", "/var/log/messages")
    
    if not pattern:
        return ToolResult(success=False, output="", error="No search pattern provided")
    
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
        
        return ToolResult(success=True, output=output, error=None)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))

def network_connections() -> ToolResult:
    """Show active network connections."""
    command = "ss -tunap 2>/dev/null || netstat -tunap 2>/dev/null"
    return execute_command({"command": command, "timeout": 10})

if __name__ == "__main__":
    import uvicorn
    print("[FORENSIC AGENT] Starting Proxi Forensic Agent on port 8081...")
    print(f"[FORENSIC AGENT] Agent key configured: {bool(AGENT_API_KEY)}")
    uvicorn.run(app, host="0.0.0.0", port=8081)
