
import uvicorn
import os
import logging
from pathlib import Path
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
    append_session_message, append_session_goal, update_session_goal,
    save_session_image, get_session_images, get_image_by_id
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

# CORS Configuration - restrict to production domain
# In production, only allow requests from your domain
ALLOWED_ORIGINS = [
    "https://proxi.audista.com",
    "http://localhost:4002",      # Local dev
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:4002",
    "http://localhost",           # Capacitor mobile app
    "capacitor://localhost",      # Capacitor Android
    "ionic://localhost",          # Ionic webview
    "http://10.0.2.2",            # Android emulator
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# --- AUTH HELPER ---
async def require_auth(request: Request, require_admin: bool = False) -> dict:
    """Helper to require authentication. Returns user dict or raises 401/403."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = auth_service.get_user_for_session(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if require_admin and user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {"username": user.username, "role": user.role, "display_name": user.display_name}

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
        
        remember_me = data.get("remember_me", False)
        
        user = auth_service.authenticate(username, password)
        if user:
            session = auth_service.create_session(username, remember_me=remember_me)
            response = JSONResponse({
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role
            })
            # Detect if running behind HTTPS (Cloudflare/nginx)
            is_https = request.headers.get("x-forwarded-proto") == "https"
            response.set_cookie(
                key="session_id",
                value=session.session_id,
                httponly=True,
                secure=is_https,  # True when behind HTTPS proxy
                samesite="lax" if is_https else "lax",
                max_age=86400 if remember_me else None  # 24hr if remember_me
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
    # Detect if running behind HTTPS
    is_https = True  # Magic links are typically used in production
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=is_https,
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
async def chat(request: ChatRequest, http_request: Request):
    """Streaming Endpoint for Agent Thoughts. Requires auth."""
    await require_auth(http_request)
    
    # Auto-activate workstation if provided (ensures agent is set even after Core restart)
    if request.workstation_id:
        ws = get_workstation(request.workstation_id)
        if ws:
            agent_url = f"http://{ws['host']}:{ws['port']}"
            set_active_agent(agent_url)
    
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
    request: Request,
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this architecture diagram")
):
    """Vision analysis. Requires auth."""
    await require_auth(request)
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
    request: Request,
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this image"),
    complexity: str = Form("deep")
):
    """Process image with full agent pipeline. Requires auth."""
    await require_auth(request)
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

@app.post("/api/approvals/{approval_id}")
async def handle_approval(
    approval_id: str,
    request: Request,
    action: dict = Body(...)
):
    """Handle command approval or denial. Requires auth."""
    await require_auth(request)
    
    action_type = action.get("action")
    if action_type not in ["approve", "deny"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'deny'")
    
    try:
        if action_type == "approve":
            result = gemini_service.approve_command(approval_id)
        else:
            result = gemini_service.deny_command(approval_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MEMORY / MISSION API ENDPOINTS ---

@app.get("/api/missions")
async def get_missions(request: Request):
    """List all active research missions. Requires auth."""
    await require_auth(request)
    return get_missions_list()

@app.get("/api/missions/{mission_id}/items")
async def get_mission_items(mission_id: str, request: Request):
    """Get all found items. Requires auth."""
    await require_auth(request)
    return get_mission_items_list(mission_id)

@app.post("/api/items/{item_id}/status")
async def update_item_status(item_id: int, request: Request, status_update: dict = Body(...)):
    """Update item status. Requires auth."""
    await require_auth(request)
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status required")
    update_item_status_record(item_id, new_status)
    return {"id": item_id, "status": new_status}

@app.post("/api/desktop/execute")
async def execute_desktop_action(request: Request):
    """Execute desktop action. Requires auth."""
    await require_auth(request)
    return {"status": "executed", "result": "Atomic Mode"}

# --- SESSION MANAGEMENT ---

@app.get("/api/sessions")
async def list_sessions(request: Request, limit: int = 20):
    """Get list of recent sessions. Requires auth."""
    user = await require_auth(request)
    # Only return sessions for this user
    return get_sessions_list(limit, user_id=user["username"])

@app.post("/api/sessions")
async def create_new_session(request: Request):
    """Create a new session. Requires auth."""
    user = await require_auth(request)
    data = await request.json()
    session_id = data.get("session_id")
    title = data.get("title")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    create_session(session_id, title, user_id=user["username"])
    return {"session_id": session_id, "user_id": user["username"], "status": "created"}

@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str, request: Request):
    """Get a session by ID. Requires auth."""
    await require_auth(request)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.put("/api/sessions/{session_id}")
async def update_session_data(session_id: str, request: Request):
    """Update session data. Requires auth."""
    await require_auth(request)
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

@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str, request: Request):
    """Cancel/stop an active session's execution. Requires auth."""
    await require_auth(request)
    gemini_service.cancelled_sessions.add(session_id)
    return {"session_id": session_id, "status": "cancellation_requested"}

@app.post("/api/sessions/{session_id}/messages")
async def add_session_message(session_id: str, request: Request):
    """Append a message to session history. Requires auth."""
    await require_auth(request)
    message = await request.json()
    append_session_message(session_id, message)
    return {"status": "added"}

@app.post("/api/sessions/{session_id}/goals")
async def add_session_goal(session_id: str, request: Request):
    """Append a goal to session. Requires auth."""
    await require_auth(request)
    goal = await request.json()
    append_session_goal(session_id, goal)
    return {"status": "added"}

@app.put("/api/sessions/{session_id}/goals/{goal_id}")
async def update_goal_status(session_id: str, goal_id: str, request: Request):
    """Update a goal's status. Requires auth."""
    await require_auth(request)
    data = await request.json()
    update_session_goal(session_id, goal_id, data.get("status"), data.get("result"))
    return {"status": "updated"}

@app.post("/api/sessions/{session_id}/close")
async def close_session_endpoint(session_id: str, request: Request):
    """Close a session. Requires auth."""
    await require_auth(request)
    close_session(session_id)
    return {"session_id": session_id, "status": "closed"}

# --- IMAGE STORAGE ---

IMAGES_DIR = Path("/app/data/images") if Path("/app/data").exists() else Path("images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/sessions/{session_id}/images")
async def upload_session_image(session_id: str, request: Request):
    """Upload an image for a session. Requires auth."""
    await require_auth(request)
    import base64
    import uuid
    
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # Base64 upload
        data = await request.json()
        image_data = data.get("image")  # base64 string
        filename = data.get("filename", "image.png")
        source = data.get("source", "user")  # user, screenshot, agent
        metadata = data.get("metadata", {})
        
        if not image_data:
            raise HTTPException(status_code=400, detail="image (base64) required")
        
        # Remove data URL prefix if present
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        image_id = f"img_{uuid.uuid4().hex[:12]}"
        file_path = IMAGES_DIR / f"{image_id}.png"
        
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_data))
        
        save_session_image(session_id, image_id, filename, "image/png", source, metadata)
        return {"image_id": image_id, "url": f"/api/images/{image_id}"}
    else:
        raise HTTPException(status_code=400, detail="JSON with base64 image required")

@app.get("/api/sessions/{session_id}/images")
async def list_session_images(session_id: str, request: Request):
    """Get all images for a session. Requires auth."""
    await require_auth(request)
    images = get_session_images(session_id)
    for img in images:
        img["url"] = f"/api/images/{img['image_id']}"
    return {"images": images}

@app.get("/api/images/{image_id}")
async def get_image(image_id: str, request: Request):
    """Get an image by ID. Requires auth."""
    await require_auth(request)
    from fastapi.responses import FileResponse
    
    img_meta = get_image_by_id(image_id)
    if not img_meta:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = IMAGES_DIR / f"{image_id}.png"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(file_path, media_type=img_meta.get("content_type", "image/png"))

# --- WORKSTATION / AGENT MANAGEMENT ---

@app.get("/api/workstations")
async def get_workstations(request: Request):
    """List all registered Proxi Agents (workstations) with live health status."""
    # Require authentication to list workstations
    await require_auth(request)
    
    registry = get_registry()
    # Check health of all workstations before returning
    await registry.check_all_health()
    return {"workstations": list_workstations()}

@app.get("/api/workstations/{workstation_id}")
async def get_workstation_details(workstation_id: str, request: Request):
    """Get details of a specific workstation. Requires auth."""
    await require_auth(request)
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    return ws

@app.get("/api/workstations/{workstation_id}/health")
async def check_workstation_health(workstation_id: str, request: Request):
    """Check health status of a workstation. Requires auth."""
    await require_auth(request)
    status = await get_workstation_status(workstation_id)
    return status

@app.post("/api/workstations")
async def register_workstation(request: Request):
    """Register a new Proxi Agent (workstation). Requires admin."""
    # Only admins can register new workstations
    await require_auth(request, require_admin=True)
    
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
async def remove_workstation(workstation_id: str, request: Request):
    """Remove a registered workstation. Requires admin."""
    # Only admins can delete workstations
    await require_auth(request, require_admin=True)
    
    registry = get_registry()
    if registry.delete_workstation(workstation_id):
        return {"status": "deleted", "workstation_id": workstation_id}
    raise HTTPException(status_code=404, detail="Workstation not found")

@app.post("/api/workstations/{workstation_id}/activate")
async def activate_workstation(workstation_id: str, request: Request):
    """
    Set a workstation as the active agent for tool execution. Requires auth.
    All subsequent tool calls will be proxied to this agent.
    Validates agent is reachable before activating.
    """
    await require_auth(request)
    ws = get_workstation(workstation_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    
    agent_url = f"http://{ws['host']}:{ws['port']}"
    
    # Check if agent is reachable before activating
    import aiohttp
    try:
        # Include X-Agent-Key header for authentication
        headers = {}
        agent_key = os.getenv("PROXI_AGENT_KEY")
        if agent_key:
            headers["X-Agent-Key"] = agent_key
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{agent_url}/health", headers=headers) as response:
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
async def deactivate_workstation(request: Request):
    """Clear the active agent, use local execution. Requires auth."""
    await require_auth(request)
    clear_active_agent()
    return {"status": "deactivated", "message": "Using local execution"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
