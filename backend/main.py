import uvicorn
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.models.api_models import ChatRequest, ChatResponse, ActionConfirmation
from backend.services.gemini_service import GeminiService

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
    """
    Streaming Endpoint. Returns a stream of JSON lines (NDJSON).
    Each line contains a step of the agent's thought process or the final response.
    """
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

@app.post("/api/desktop/execute")
async def execute_desktop_action():
    # Deprecated/Atomic
    return {"status": "executed", "result": "Atomic Mode"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
