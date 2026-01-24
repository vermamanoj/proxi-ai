import uvicorn
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.models.api_models import ChatRequest, ChatResponse, ActionConfirmation
from backend.services.gemini_service import GeminiService
from backend.database import get_missions_list, get_mission_items_list, update_item_status_record

app = FastAPI(
    title="Proxi Backend",
    description="Backend API for Proxi Headless Operator",
    version="0.3.0"
)

# Initialize Service
gemini_service = GeminiService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Proxi Backend is running", "status": "online"}

@app.get("/api/health")
async def health_check():
    return {"message": "Proxi System Online", "status": "operational"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Streaming Endpoint for Agent Thoughts"""
    try:
        return StreamingResponse(
            gemini_service.route_and_execute_stream(request.message, request.complexity),
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

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
