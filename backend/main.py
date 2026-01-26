
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
from backend.database import get_missions_list, get_mission_items_list, update_item_status_record
from backend.services.desktop.factory import get_desktop_service

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
    mode = os.getenv("RUNTIME_MODE", "DEMO")
    return {"message": "Proxi Backend is running", "status": "online", "mode": mode}

@app.get("/api/health")
async def health_check():
    mode = os.getenv("RUNTIME_MODE", "DEMO")
    return {"message": "Proxi System Online", "status": "operational", "mode": mode}

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

# --- DEMO / JUDGE TOOLS ---

@app.post("/api/demo/trigger_chaos")
async def trigger_chaos():
    """DEMO: Triggers a simulated high-CPU incident in the Mock Desktop."""
    ds = get_desktop_service()
    if hasattr(ds, 'trigger_incident'):
        ds.trigger_incident()
        return {"status": "chaos_triggered", "message": "Simulated incident started. CPU at 99%."}
    return {"status": "ignored", "message": "Not in DEMO mode."}

@app.post("/api/demo/reset")
async def reset_demo():
    """DEMO: Resets the simulated environment."""
    ds = get_desktop_service()
    if hasattr(ds, 'resolve_incident'):
        ds.resolve_incident()
        return {"status": "reset", "message": "Simulated environment normalized."}
    return {"status": "ignored"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
