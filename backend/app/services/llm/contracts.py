from typing import Optional, Dict, Any
from pydantic import BaseModel

class LLMRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class LLMResponse(BaseModel):
    status: str  # 'success', 'provider_error', 'timeout', 'invalid_response'
    content: Optional[str] = None
    provider: str
    model_name: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: int
    error_message: Optional[str] = None
