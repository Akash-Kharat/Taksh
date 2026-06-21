from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ChatGenerateRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    provider: Optional[str] = None

class ChatGenerateResponse(BaseModel):
    response_id: str
    trace_id: str
    content: Optional[str] = None
    provider: str
    model_name: str
    status: str
    latency_ms: int

class LLMDiagnosticsResponse(BaseModel):
    configured: bool
    reachable: bool
    last_successful_request: Optional[datetime] = None
    provider: str
    model: str
