from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class RuntimeStartRequest(BaseModel):
    """Request payload to initialize a new conversation runtime session."""
    voice_session_id: Optional[str] = None


class RuntimeStartResponse(BaseModel):
    """Response payload for a newly initialized conversation runtime session."""
    runtime_session_id: str
    conversation_state: str
    current_turn_owner: str
    started_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuntimeInterruptRequest(BaseModel):
    """Request payload to trigger an interruption (barge-in) in an active session."""
    runtime_session_id: str


class RuntimeInterruptResponse(BaseModel):
    """Response payload confirming the interruption state transition."""
    runtime_session_id: str
    conversation_state: str
    current_turn_owner: str


class RuntimeCloseRequest(BaseModel):
    """Request payload to close and clean up a conversation runtime session."""
    runtime_session_id: str


class RuntimeCloseResponse(BaseModel):
    """Response payload confirming session closure."""
    runtime_session_id: str
    conversation_state: str
    current_turn_owner: str
    ended_at: datetime


class RuntimeInfoResponse(BaseModel):
    """Global summary metrics for the conversation runtime layer."""
    active_sessions_count: int
    total_sessions_count: int
    total_listening_ms: int
    total_speaking_ms: int
    total_thinking_ms: int
    total_interruption_count: int


class RuntimeSessionDiagnosticsResponse(BaseModel):
    """Detailed diagnostics and metrics for a specific conversation runtime session."""
    runtime_session_id: str
    voice_session_id: Optional[str]
    current_state: str
    turn_owner: str
    interruption_count: int
    event_count: int
    total_listening_ms: int
    total_speaking_ms: int
    started_at: datetime
    ended_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
