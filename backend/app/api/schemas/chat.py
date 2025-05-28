from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Chat schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

# Rag Response schema
class RagResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float 