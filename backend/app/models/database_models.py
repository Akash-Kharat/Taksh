import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Integer, Boolean
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
