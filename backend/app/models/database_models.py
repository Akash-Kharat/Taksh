import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Session(Base):
    __tablename__ = "sessions"
    
    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    memory_events: Mapped[List["MemoryEvent"]] = relationship(
        "MemoryEvent", back_populates="session", cascade="all, delete-orphan"
    )

class MemoryEvent(Base):
    __tablename__ = "memory_events"
    
    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    primary_modality: Mapped[str] = mapped_column(String)  # 'text', 'voice', 'workspace'
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="memory_events")
    text_payload: Mapped[Optional["TextPayload"]] = relationship(
        "TextPayload", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    audio_payload: Mapped[Optional["AudioPayload"]] = relationship(
        "AudioPayload", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    workspace_payload: Mapped[Optional["WorkspacePayload"]] = relationship(
        "WorkspacePayload", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )

class TextPayload(Base):
    __tablename__ = "event_payloads_text"
    
    event_id: Mapped[str] = mapped_column(ForeignKey("memory_events.event_id"), primary_key=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt_injected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event: Mapped["MemoryEvent"] = relationship("MemoryEvent", back_populates="text_payload")

class AudioPayload(Base):
    __tablename__ = "event_payloads_audio"
    
    event_id: Mapped[str] = mapped_column(ForeignKey("memory_events.event_id"), primary_key=True)
    audio_file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    event: Mapped["MemoryEvent"] = relationship("MemoryEvent", back_populates="audio_payload")

class WorkspacePayload(Base):
    __tablename__ = "event_payloads_workspace"
    
    event_id: Mapped[str] = mapped_column(ForeignKey("memory_events.event_id"), primary_key=True)
    active_file: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cursor_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    selected_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terminal_stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event: Mapped["MemoryEvent"] = relationship("MemoryEvent", back_populates="workspace_payload")

class ProjectTracker(Base):
    __tablename__ = "project_tracker"
    
    project_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    tech_stack: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    historical_adr_keys: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

class GoalTracker(Base):
    __tablename__ = "goal_tracker"
    
    goal_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")  # 'active', 'completed', 'paused', 'cancelled'
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class LearningHistory(Base):
    __tablename__ = "learning_history"
    
    concept_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    concept_name: Mapped[str] = mapped_column(String, nullable=False)
    mastery_score: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    
    document_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    filepath: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    chunk_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.document_id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    heading_hierarchy: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")

class KnowledgeIngestionMetrics(Base):
    __tablename__ = "knowledge_ingestion_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    indexed_documents: Mapped[int] = mapped_column(Integer, default=0)
    skipped_documents: Mapped[int] = mapped_column(Integer, default=0)
    reindexed_documents: Mapped[int] = mapped_column(Integer, default=0)
    deleted_documents: Mapped[int] = mapped_column(Integer, default=0)
    last_ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CognitiveTrace(Base):
    __tablename__ = "cognitive_traces"
    
    trace_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    selected_skills: Mapped[List[dict]] = mapped_column(JSON, nullable=False)  # stores list of dicts: [{"skill": name, "score": score}]
    knowledge_chunks: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # list of chunk_ids
    memory_items: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"active_goals": [...], "recent_events": [...]}
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=False)
    final_prompt_preview: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_snapshot_id: Mapped[Optional[str]] = mapped_column(ForeignKey("workspace_snapshots.snapshot_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

class AIResponse(Base):
    __tablename__ = "ai_responses"
    
    response_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    trace_id: Mapped[str] = mapped_column(ForeignKey("cognitive_traces.trace_id", ondelete="CASCADE"), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    
    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'system', 'user', 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cognitive_traces.trace_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkspaceSnapshot(Base):
    __tablename__ = "workspace_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    repo_name: Mapped[str] = mapped_column(String, nullable=False)
    repo_path: Mapped[str] = mapped_column(String, nullable=False)
    active_file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active_file_language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cursor_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cursor_column: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    selection_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selection_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    git_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    git_status: Mapped[dict] = mapped_column(JSON, nullable=False)
    git_recent_commits: Mapped[list] = mapped_column(JSON, nullable=False)
    detected_languages: Mapped[list] = mapped_column(JSON, nullable=False)
    detected_frameworks: Mapped[list] = mapped_column(JSON, nullable=False)
    scan_limit_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    workspace_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkspaceEvent(Base):
    __tablename__ = "workspace_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    snapshot_id: Mapped[Optional[str]] = mapped_column(ForeignKey("workspace_snapshots.snapshot_id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    execution_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cognitive_traces.trace_id", ondelete="SET NULL"), nullable=True, index=True
    )
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    capability_level: Mapped[str] = mapped_column(String, nullable=False)  # read | analyze | modify | execute
    category: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # success | error | rejected | pending_approval
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Controlled Execution Layer (MS-11) extensions
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stdout_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    stderr_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    approval_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("tool_executions.execution_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    capability_level: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | approved | denied | expired
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConversationProfile(Base):
    __tablename__ = "conversation_profiles"

    profile_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active_project_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("project_memories.project_memory_id", ondelete="SET NULL"), nullable=True
    )
    current_focus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PreferenceMemory(Base):
    __tablename__ = "preference_memories"

    preference_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    source_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True
    )
    source_trace_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cognitive_traces.trace_id", ondelete="SET NULL"), nullable=True
    )
    last_confirmed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectMemory(Base):
    __tablename__ = "project_memories"

    project_memory_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    project_name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="inactive")  # 'active', 'inactive', 'completed', 'paused'
    current_milestone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    active_goals: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectSnapshot(Base):
    __tablename__ = "project_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    project_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    milestone: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    voice_session_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True
    )
    websocket_client_id: Mapped[str] = mapped_column(String, nullable=False)
    transport_instance_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reconnect_count: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String, nullable=False, default="connected")
    frames_received: Mapped[int] = mapped_column(Integer, default=0)
    frames_sent: Mapped[int] = mapped_column(Integer, default=0)
    bytes_received: Mapped[int] = mapped_column(Integer, default=0)
    bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    dropped_frames: Mapped[int] = mapped_column(Integer, default=0)
    missing_frames: Mapped[int] = mapped_column(Integer, default=0)
    out_of_order_frames: Mapped[int] = mapped_column(Integer, default=0)
    average_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    disconnect_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ConversationRuntimeSession(Base):
    __tablename__ = "conversation_runtime_sessions"

    runtime_session_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    voice_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("voice_sessions.voice_session_id", ondelete="SET NULL"), nullable=True
    )
    conversation_state: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    current_turn_owner: Mapped[str] = mapped_column(String, nullable=False, default="none")
    interruption_count: Mapped[int] = mapped_column(Integer, default=0)
    total_listening_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_thinking_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_speaking_ms: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    conversation_session_state: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active, recovering, closed, failed
    session_summary_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # completed, failed
    # MS-19: Audit trail — root of the correlation chain for this session
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    conversation_title: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    memory_episode: Mapped[Optional["MemoryEpisode"]] = relationship(
        "MemoryEpisode", back_populates="runtime_session", uselist=False, cascade="all, delete-orphan"
    )


class ConversationRuntimeTrace(Base):
    __tablename__ = "conversation_runtime_traces"

    trace_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    runtime_session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ProviderHealthRecord(Base):
    __tablename__ = "provider_health_records"

    record_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    healthy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timeout_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    runtime_session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    voice_session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderSession(Base):
    __tablename__ = "provider_sessions"

    provider_session_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    runtime_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="SET NULL"), nullable=True, index=True
    )
    voice_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("voice_sessions.voice_session_id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider_state: Mapped[str] = mapped_column(String, nullable=False, default="initializing")
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disconnect_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    messages_received: Mapped[int] = mapped_column(Integer, default=0)
    audio_frames_sent: Mapped[int] = mapped_column(Integer, default=0)
    audio_frames_received: Mapped[int] = mapped_column(Integer, default=0)
    interruptions: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_response_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_response_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class ProviderConversationMessage(Base):
    __tablename__ = "provider_conversation_messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    provider_session_id: Mapped[str] = mapped_column(
        ForeignKey("provider_sessions.provider_session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    turn_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    runtime_session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    voice_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("voice_sessions.voice_session_id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cognitive_trace_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cognitive_traces.trace_id", ondelete="SET NULL"), nullable=True, index=True
    )
    ai_response_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ai_responses.response_id", ondelete="SET NULL"), nullable=True, index=True
    )
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    response_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    message_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    cognitive_trace: Mapped[Optional["CognitiveTrace"]] = relationship("CognitiveTrace", foreign_keys=[cognitive_trace_id])
    ai_response: Mapped[Optional["AIResponse"]] = relationship("AIResponse", foreign_keys=[ai_response_id])


class ConversationMetrics(Base):
    __tablename__ = "conversation_metrics"

    metrics_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    runtime_session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    average_turn_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    average_stt_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    average_llm_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    average_tts_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_interruptions: Mapped[int] = mapped_column(Integer, default=0)
    playback_dropped_chunks: Mapped[int] = mapped_column(Integer, default=0)


class MemoryEpisode(Base):
    __tablename__ = "memory_episodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("project_memories.project_memory_id", ondelete="SET NULL"), nullable=True, index=True
    )
    memory_type: Mapped[str] = mapped_column(String, nullable=False, default="episodic")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recall_count: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_decisions: Mapped[list] = mapped_column(JSON, default=list)
    important_facts: Mapped[list] = mapped_column(JSON, default=list)
    open_tasks: Mapped[list] = mapped_column(JSON, default=list)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    embedding_vector: Mapped[list] = mapped_column(JSON, nullable=False)
    # MS-19: Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    runtime_session: Mapped["ConversationRuntimeSession"] = relationship(
        "ConversationRuntimeSession", back_populates="memory_episode"
    )
    project: Mapped[Optional["ProjectMemory"]] = relationship("ProjectMemory")
    recalls: Mapped[List["MemoryRecall"]] = relationship(
        "MemoryRecall", back_populates="episode", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["OpenTask"]] = relationship(
        "OpenTask", back_populates="episode", cascade="all, delete-orphan"
    )


class MemoryRecall(Base):
    __tablename__ = "memory_recalls"

    recall_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_runtime_sessions.runtime_session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    episode_id: Mapped[str] = mapped_column(
        ForeignKey("memory_episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recalled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    retrieval_reason: Mapped[str] = mapped_column(String, nullable=False)

    episode: Mapped["MemoryEpisode"] = relationship("MemoryEpisode", back_populates="recalls")


class OpenTask(Base):
    __tablename__ = "open_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    episode_id: Mapped[str] = mapped_column(
        ForeignKey("memory_episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")  # OPEN, IN_PROGRESS, DONE, CANCELLED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    episode: Mapped["MemoryEpisode"] = relationship("MemoryEpisode", back_populates="tasks")


# ---------------------------------------------------------------------------
# MS-19: MetricsSnapshot — persisted metrics for restart recovery
# ---------------------------------------------------------------------------

class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    conversation_count: Mapped[int] = mapped_column(Integer, default=0)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_requests: Mapped[int] = mapped_column(Integer, default=0)
    provider_failures: Mapped[int] = mapped_column(Integer, default=0)
    tool_executions: Mapped[int] = mapped_column(Integer, default=0)
    memory_recalls: Mapped[int] = mapped_column(Integer, default=0)
    knowledge_searches: Mapped[int] = mapped_column(Integer, default=0)
    average_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

