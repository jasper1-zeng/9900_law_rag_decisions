from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Build Arguments schemas
class BuildArgumentsRequest(BaseModel):
    case_content: str
    case_title: Optional[str] = None
    case_topic: Optional[str] = None
    llm_model: Optional[str] = None
    conversation_id: Optional[str] = None
    use_single_call: Optional[bool] = False  # Default to multi-step approach

class RelatedCase(BaseModel):
    title: str
    url: str
    summary: str
    similarity_score: float
    citation_number: Optional[str] = ""

class BuildArgumentsResponse(BaseModel):
    """
    Response model for building arguments.
    """
    disclaimer: str
    related_cases: List[RelatedCase]
    raw_content: str  # Raw LLM output as markdown/structured text
    conversation_id: str 