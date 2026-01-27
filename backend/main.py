
import uvicorn
import os
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response
from backend.auth import AuthService, get_auth_service

# Filter out noisy health check logs
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /api/health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
from backend.models.api_models import ChatRequest, ChatResponse, ActionConfirmation
from backend.services.gemini_service import GeminiService
from backend.database import (
    init_db,
    get_missions_list, get_mission_items_list, update_item_status_record,
    create_session, get_session, update_session, get_sessions_list, close_session,
    append_session_message, append_session_goal, update_session_goal
)

# Initialize database on startup
init_db()
from backend.services.desktop.factory import get_desktop_service, set_active_agent, clear_active_agent
from backend.registry.workstation_registry import (
    get_registry, list_workstations, get_workstation, get_workstation_status
)

app = FastAPI(
    title="Proxi Backend",
    description="Backend API for Proxi Headless Operator",
    version="0.3.0"
)

# Initialize Services
gemini_service = GeminiService()
auth_service = get_auth_service()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    import platform
    return {"message": "Proxi Backend is running", "status": "online", "platform": platform.system()}

@app.get("/api/health")
async def health_check():
    import platform
    return {"message": "Proxi System Online", "status": "operational", "platform": platform.system()}

# Authentication endpoints
@app.post("/api/auth/login")
async def login(request: Request):
    """Login endpoint"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JSONResponse(
                {"error": "Username and password required"}, 
                status_code=400
            )
        
        user = auth_service.authenticate(username, password)
        if user:
            session = auth_service.create_session(username)
            response = JSONResponse({
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role
            })
            response.set_cookie(
                key="session_id",
                value=session.session_id,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            return response
        else:
            return JSONResponse(
                {"error": "Invalid credentials"}, 
                status_code=401
            )
    except Exception as e:
        return JSONResponse(
            {"error": f"Login failed: {str(e)}"}, 
            status_code=500
        )

@app.get("/api/auth/session")
async def check_session(request: Request):
    """Check if session is valid"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({"error": "No session"}, status_code=401)
        
        user = auth_service.get_user_for_session(session_id)
        if user:
            return JSONResponse({
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role
            })
        
        return JSONResponse({"error": "Invalid session"}, status_code=401)
    except Exception as e:
        return JSONResponse(
            {"error": f"Session check failed: {str(e)}"}, 
            status_code=500
        )

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout endpoint"""
    try:
        session_id = request.cookies.get("session_id")
        if session_id:
            auth_service.invalidate_session(session_id)
        
        response = JSONResponse({"message": "Logged out successfully"})
        response.delete_cookie("session_id")
        return response
    except Exception as e:
        return JSONResponse(
            {"error": f"Logout failed: {str(e)}"}, 
            status_code=500
        )

# --- Magic Link Endpoints ---

@app.post("/api/auth/magic-link")
async def create_magic_link(request: Request):
    """Create a magic link for passwordless access (admin only)."""
    try:
        # Check if user is admin
        session_id = request.cookies.get("session_id")
        if session_id:
            user = auth_service.get_user_for_session(session_id)
            if not user or user.role != "admin":
                return JSONResponse({"error": "Admin access required"}, status_code=403)
        else:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        data = await request.json()
        link = auth_service.create_magic_link(
            role=data.get("role", "judge"),
            label=data.get("label", ""),
            expires_hours=data.get("expires_hours", 72),
            uses=data.get("uses", 10)
        )
        
        return JSONResponse({
            "token": link.token,
            "label": link.label,
            "role": link.role,
            "expires_at": link.expires_at.isoformat(),
            "uses_remaining": link.uses_remaining,
            "url": f"/magic/{link.token}"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/auth/magic-link/{token}")
async def validate_magic_link(token: str):
    """Validate a magic link without redeeming it."""
    link = auth_service.validate_magic_link(token)
    if not link:
        return JSONResponse({"error": "Invalid or expired link"}, status_code=401)
    
    return JSONResponse({
        "valid": True,
        "label": link.label,
        "role": link.role,
        "uses_remaining": link.uses_remaining
    })

@app.post("/api/auth/magic-link/{token}/redeem")
async def redeem_magic_link(token: str):
    """Redeem a magic link and get a session."""
    session = auth_service.redeem_magic_link(token)
    if not session:
        return JSONResponse({"error": "Invalid or expired link"}, status_code=401)
    
    # Get the user info
    user = auth_service.get_user_for_session(session.session_id)
    
    response = JSONResponse({
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role
    })
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    return response

@app.get("/api/auth/magic-links")
async def list_magic_links(request: Request):
    """List all magic links (admin only)."""
    session_id = request.cookies.get("session_id")
    if session_id:
        user = auth_service.get_user_for_session(session_id)
        if not user or user.role != "admin":
            return JSONResponse({"error": "Admin access required"}, status_code=403)
    else:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    
    return JSONResponse({"links": auth_service.list_magic_links()})

@app.delete("/api/auth/magic-link/{token}")
async def revoke_magic_link(token: str, request: Request):
    """Revoke a magic link (admin only)."""
    session_id = request.cookies.get("session_id")
    if session_id:
        user = auth_service.get_user_for_session(session_id)
        if not user or user.role != "admin":
            return JSONResponse({"error": "Admin access required"}, status_code=403)
    else:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    
    if auth_service.revoke_magic_link(token):
        return JSONResponse({"status": "revoked"})
    return JSONResponse({"error": "Link not found"}, status_code=404)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Streaming Endpoint for Agent Thoughts"""
    try:
        return StreamingResponse(
            gemini_service.route_and_execute_stream(
                request.message, 
                request.complexity,
                request.session_id
            ),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision", response_model=ChatResponse)
async def vision_analysis(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this architecture diagram")
):
    try:
        contents = await file.read()
        response_text = await gemini_service.process_vision_command(contents, prompt)
        return ChatResponse(
            response=response_text,
            status="success",
            used_model=gemini_service.VISION_MODEL,
            reasoning_path="vision_direct",
            trace_logs=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision-action")
async def vision_with_action(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this image"),
    complexity: str = Form("deep")
):
    """Process image with full agent pipeline - can execute actions based on image content"""
    import base64
    try:
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode('utf-8')
        mime_type = file.content_type or 'image/png'
        
        # Create a message that includes the image context for the agent
        enhanced_prompt = f"""The user has uploaded an image and wants you to: {prompt}

The image is provided as base64 data. Use look_at_uploaded_image() to analyze it, then execute the requested actions.
IMAGE_DATA:{mime_type};base64,{image_base64}"""
        
        return StreamingResponse(
            gemini_service.route_and_execute_stream(enhanced_prompt, complexity),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MEMORY / MISSION API ENDPOINTS ---

@app.get("/api/missions")
async def get_missions():
    """List all active research missions"""
    return get_missions_list()

@app.get("/api/missions/{mission_id}/items")
async def get_mission_items(mission_id: str):
    """Get all found items (leads, bugs) for a mission"""
    return get_mission_items_list(mission_id)

@app.post("/api/items/{item_id}/status")
async def update_item_status(item_id: int, status_update: dict = Body(...)):
    """Update item status (e.g. APPROVED, REJECTED)"""
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status required")
    update_item_status_record(item_id, new_status)
    return {"id": item_id, "status": new_status}

@app.post("/api/desktop/execute")
async def execute_desktop_action():
    return {"status": "executed", "result": "Atomic Mode"}

# --- SESSION MANAGEMENT ---

@app.get("/api/sessions")
async def list_sessions(request: Request, limit: int = 20):
    """Get list of recent sessions, filtered by user if logged in."""
    user_id = None
    session_cookie = request.cookies.get("session_id")
    if session_cookie:
        user = auth_service.get_user_for_session(session_cookie)
        if user:
            user_id = user.username
    return get_sessions_list(limit, user_id=user_id)

@app.post("/api/sessions")
async def create_new_session(request: Request):
    """Create a new session with user association if logged in."""
    data = await request.json()
    session_id = data.get("session_id")
    title = data.get("title")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Get user_id from auth cookie if present
    user_id = None
    session_cookie = request.cookies.get("session_id")
    if session_cookie:
        user = auth_service.get_user_for_session(session_cookie)
        if user:
            user_id = user.username
    
    create_session(session_id, title, user_id=user_id)
    return {"session_id": session_id, "user_id": user_id, "status": "created"}

@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Get a session by ID with full history."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.put("/api/sessions/{session_id}")
async def update_session_data(session_id: str, request: Request):
    """Update session data (title, goals, messages)."""
    data = await request.json()
    update_session(
        session_id,
        title=data.get("title"),
        requirements=data.get("requirements"),
        goals=data.get("goals"),
        messages=data.get("messages"),
        status=data.get("status")
    )
    return {"session_id": session_id, "status": "updated"}

@app.post("/api/sessions/{session_id}/messages")
async def add_session_message(session_id: str, request: Request):
    """Append a message to session history."""
    message = await request.json()
    append_session_message(session_id, message)
    return {"status": "added"}

@app.post("/api/sessions/{session_id}/goals")
async def add_session_goal(session_id: str, request: Request):
    """Append a goal to session."""
    goal = await request.json()
    append_session_goal(session_id, goal)
    return {"status": "added"}

@app.put("/api/sessions/{session_id}/goals/{goal_id}")
async def update_goal_status(session_id: str, goal_id: str, request: Request):
    """Update a goal's status."""
    data = await request.json()
    update_session_goal(session_id, goal_id, data.get("status"), data.get("result"))
    return {"status": "updated"}

@app.post("/api/sessions/{session_id}/close")
async def close_session_endpoint(session_id: str):
    """Close a session (archive it)."""
    close_session(session_id)
    return {"session_id": session_id, "status": "closed"}

# --- WORKSTATION / AGENT MANAGEMENT ---

@app.get("/api/workstations")
async def get_workstations():
    """List all registered Proxi Agents (workstations)."""
    return {"workstations": list_workstations()}

@app.get("/api/workstations/{workstation_id}")
async def get_workstation_details(workstation_id: str):
    """Get details of a specific workstation."""
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    return ws

@app.get("/api/workstations/{workstation_id}/health")
async def check_workstation_health(workstation_id: str):
    """Check health status of a workstation."""
    status = await get_workstation_status(workstation_id)
    return status

@app.post("/api/workstations")
async def register_workstation(request: Request):
    """Register a new Proxi Agent (workstation)."""
    from backend.registry.workstation_registry import Workstation
    data = await request.json()
    
    required = ["id", "name", "host", "workstation_type"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"{field} required")
    
    ws = Workstation(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        workstation_type=data["workstation_type"],
        host=data["host"],
        port=data.get("port", 8080),
        capabilities=data.get("capabilities", []),
        owner=data.get("owner", ""),
        tags=data.get("tags", [])
    )
    
    registry = get_registry()
    registry.register_workstation(ws)
    return {"status": "registered", "workstation": ws.to_dict()}

@app.delete("/api/workstations/{workstation_id}")
async def remove_workstation(workstation_id: str):
    """Remove a registered workstation."""
    registry = get_registry()
    if registry.delete_workstation(workstation_id):
        return {"status": "deleted", "workstation_id": workstation_id}
    raise HTTPException(status_code=404, detail="Workstation not found")

@app.post("/api/workstations/{workstation_id}/activate")
async def activate_workstation(workstation_id: str):
    """
    Set a workstation as the active agent for tool execution.
    All subsequent tool calls will be proxied to this agent.
    Validates agent is reachable before activating.
    """
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    
    agent_url = f"http://{ws['host']}:{ws['port']}"
    
    # Check if agent is reachable before activating
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{agent_url}/health") as response:
                if response.status != 200:
                    raise HTTPException(status_code=503, detail=f"Agent '{ws['name']}' is not responding (status {response.status})")
    except aiohttp.ClientConnectorError:
        raise HTTPException(status_code=503, detail=f"Agent '{ws['name']}' is offline - cannot connect to {agent_url}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent '{ws['name']}' health check failed: {str(e)}")
    
    set_active_agent(agent_url)
    return {
        "status": "activated",
        "workstation_id": workstation_id,
        "agent_url": agent_url
    }

@app.post("/api/workstations/deactivate")
async def deactivate_workstation():
    """Clear the active agent, use local execution."""
    clear_active_agent()
    return {"status": "deactivated", "message": "Using local execution"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
