import uvicorn
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.models.api_models import ChatRequest, ChatResponse, ActionConfirmation
from backend.services.gemini_service import GeminiService

app = FastAPI(
    title="Proxi Backend",
    description="Backend API for Proxi Headless Operator",
    version="0.1.0"
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

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response_text = ""
        model_used = ""

        if request.complexity == "deep":
            response_text = await gemini_service.generate_deep_thought(request.message)
            model_used = gemini_service.SMART_TEXT_MODEL
        else:
            response_text = await gemini_service.generate_reflex_response(request.message)
            model_used = gemini_service.FAST_TEXT_MODEL

        # Check if the tool execution triggered a pending action
        pending_action = gemini_service.latest_pending_action

        return ChatResponse(
            response=response_text,
            status="success",
            used_model=model_used,
            pending_action=pending_action
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
            used_model=gemini_service.VISION_MODEL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/desktop/execute")
async def execute_desktop_action():
    """
    Executes the action waiting in the HITL buffer.
    """
    try:
        result = gemini_service.execute_pending_action()
        return {"status": "executed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
