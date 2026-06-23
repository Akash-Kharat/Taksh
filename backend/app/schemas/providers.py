from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ProviderInfoResponse(BaseModel):
    """Schema for general active provider diagnostics payload."""
    active_provider: str
    provider_state: str
    healthy: bool
    fallback_active: bool
    active_sessions: int
    reconnect_count: int
    failure_count: int


class ProviderSessionSchema(BaseModel):
    """Schema for individual provider sessions data."""
    provider_session_id: str
    provider_name: str
    runtime_session_id: Optional[str] = None
    voice_session_id: Optional[str] = None
    provider_state: str
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    disconnect_reason: Optional[str] = None
    messages_sent: int
    messages_received: int
    audio_frames_sent: int
    audio_frames_received: int
    interruptions: int
    total_tokens_in: Optional[int] = None
    total_tokens_out: Optional[int] = None
    average_response_latency_ms: Optional[float] = None
    max_response_latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderSessionsResponse(BaseModel):
    """Schema for aggregated provider session histories."""
    sessions: List[ProviderSessionSchema]
    total_sessions: int
    average_latency_ms: float
    total_interruptions: int
    total_audio_frames_sent: int
    total_audio_frames_received: int
