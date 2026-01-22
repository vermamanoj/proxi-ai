from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    complexity: Optional[str] = "fast"  # Options: "fast", "deep"

class ChatResponse(BaseModel):
    response: str
    status: str
    model_used: str