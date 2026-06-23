"""
Pydantic schemas for the Conversation Intelligence Layer REST API (MS-12).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ConversationInfoResponse(BaseModel):
    """Diagnostics and statistics summary of conversation continuity data."""
    profiles: int = Field(..., description="Number of conversation profiles tracked")
    preferences: int = Field(..., description="Total count of stored preference memory records")
    projects: int = Field(..., description="Total count of projects registered in database")
    snapshots: int = Field(..., description="Total count of project snapshots captured")
    active_project: Optional[str] = Field(None, description="Name of the currently active project")
    
    active_sessions: int = Field(0)
    total_turns: int = Field(0)
    avg_turn_latency_ms: float = Field(0.0)
    avg_stt_latency_ms: float = Field(0.0)
    avg_llm_latency_ms: float = Field(0.0)
    avg_tts_latency_ms: float = Field(0.0)
    provider_fallbacks: int = Field(0)
    playback_queue_depth: int = Field(0)


from datetime import datetime
from typing import List

class ConversationStartRequest(BaseModel):
    voice_session_id: Optional[str] = None

class ConversationStartResponse(BaseModel):
    runtime_session_id: str
    voice_session_id: str
    conversation_state: str
    conversation_session_state: str

    model_config = ConfigDict(from_attributes=True)

class ConversationMessageRequest(BaseModel):
    runtime_session_id: str
    message: str

class ConversationMessageResponse(BaseModel):
    assistant_text: str
    turn_id: str

class ConversationStopRequest(BaseModel):
    runtime_session_id: str

class ConversationTurnSchema(BaseModel):
    turn_id: str
    runtime_session_id: str
    voice_session_id: Optional[str] = None
    user_text: str
    assistant_text: str
    prompt_hash: Optional[str] = None
    provider_name: Optional[str] = None
    latency_ms: float
    started_at: datetime
    completed_at: datetime
    cognitive_trace_id: Optional[str] = None
    ai_response_id: Optional[str] = None
    segment_count: int
    response_truncated: bool

    model_config = ConfigDict(from_attributes=True)

class ConversationMetricsSchema(BaseModel):
    metrics_id: str
    runtime_session_id: str
    total_turns: int
    average_turn_latency_ms: float
    average_stt_latency_ms: float
    average_llm_latency_ms: float
    average_tts_latency_ms: float
    total_interruptions: int
    playback_dropped_chunks: int

    model_config = ConfigDict(from_attributes=True)

class ConversationSessionDetailResponse(BaseModel):
    turns: List[ConversationTurnSchema]
    metrics: Optional[ConversationMetricsSchema] = None
    provider_info: Optional[dict] = None
    interruptions: int
    session_summary: Optional[str] = None

class ConversationPipelineInfoResponse(BaseModel):
    active_sessions: int
    total_turns: int
    avg_turn_latency_ms: float
    avg_stt_latency_ms: float
    avg_llm_latency_ms: float
    avg_tts_latency_ms: float
    provider_fallbacks: int
    playback_queue_depth: int
