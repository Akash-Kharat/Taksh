from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    memory_events = relationship("MemoryEvent", back_populates="session", cascade="all, delete-orphan")

class MemoryEvent(Base):
    __tablename__ = "memory_events"
    
    event_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    importance_score = Column(Float, default=0.0)
    retrievability = Column(Float, default=1.0)
    primary_modality = Column(String, nullable=False)  # 'text', 'voice', 'workspace'
    summary = Column(Text, nullable=True)

    session = relationship("Session", back_populates="memory_events")
    text_payload = relationship("TextPayload", back_populates="event", uselist=False, cascade="all, delete-orphan")
    audio_payload = relationship("AudioPayload", back_populates="event", uselist=False, cascade="all, delete-orphan")
    workspace_payload = relationship("WorkspacePayload", back_populates="event", uselist=False, cascade="all, delete-orphan")

class TextPayload(Base):
    __tablename__ = "event_payloads_text"
    
    event_id = Column(String, ForeignKey("memory_events.event_id"), primary_key=True)
    transcript = Column(Text, nullable=True)
    system_prompt_injected = Column(Text, nullable=True)

    event = relationship("MemoryEvent", back_populates="text_payload")

class AudioPayload(Base):
    __tablename__ = "event_payloads_audio"
    
    event_id = Column(String, ForeignKey("memory_events.event_id"), primary_key=True)
    audio_file_path = Column(String, nullable=True)
    vocal_tension = Column(Float, nullable=True)
    voiceprint_hash = Column(String, nullable=True)

    event = relationship("MemoryEvent", back_populates="audio_payload")

class WorkspacePayload(Base):
    __tablename__ = "event_payloads_workspace"
    
    event_id = Column(String, ForeignKey("memory_events.event_id"), primary_key=True)
    active_file = Column(String, nullable=True)
    cursor_line = Column(Integer, nullable=True)
    selected_code = Column(Text, nullable=True)
    terminal_stderr = Column(Text, nullable=True)

    event = relationship("MemoryEvent", back_populates="workspace_payload")

class LearningHistory(Base):
    __tablename__ = "learning_history"
    
    concept_id = Column(String, primary_key=True, index=True)
    concept_name = Column(String, nullable=False)
    mastery_score = Column(Integer, default=0)
    last_reviewed = Column(DateTime, default=datetime.utcnow)

class GoalTracker(Base):
    __tablename__ = "goal_tracker"
    
    goal_id = Column(String, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(String, default="active")
    target_date = Column(DateTime, nullable=True)

class ProjectTracker(Base):
    __tablename__ = "project_tracker"
    
    project_id = Column(String, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    tech_stack = Column(Text, nullable=True)
    historical_adr_keys = Column(Text, nullable=True)
