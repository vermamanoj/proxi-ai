from pydantic import BaseModel
from typing import Optional, Dict, Any

class PendingAction(BaseModel):
    type: str  # e.g., "click", "type", "hotkey"
    description: str
    data: Dict[str, Any]  # e.g., {"x": 100, "y": 200}

class ChatRequest(BaseModel):
    message: str
    complexity: Optional[str] = "fast"  # Options: "fast", "deep"

class ActionConfirmation(BaseModel):
    action_token: str # Simple security or state validation

class ChatResponse(BaseModel):
    response: str
    status: str
    used_model: str
    pending_action: Optional[PendingAction] = None
