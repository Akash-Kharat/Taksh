from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProviderDiagnosticInfo(BaseModel):
    provider: str
    provider_type: str
    state: str
    healthy: bool
    supports_streaming: bool
    last_successful_operation: Optional[datetime] = None
    average_latency_ms: float
