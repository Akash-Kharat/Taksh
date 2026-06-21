from datetime import datetime
import threading
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session as DbSession
from app.models.database_models import Session, MemoryEvent, TextPayload, AudioPayload, WorkspacePayload
from app.repositories.session import session_repo
from app.repositories.memory import memory_repo
from app.repositories.goal import goal_repo
from app.repositories.learning import learning_repo
from app.repositories.project import project_repo
from app.services.memory.session_summary import session_summary_builder
from app.core.logger import memory_logger
from app.schemas.telemetry import TelemetryPayload

class MemoryManager:
    """Coordinates memory persistence across SQLite and in-memory caches."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MemoryManager, cls).__new__(cls)
                    cls._instance._sensory_cache = {}
                    cls._instance.sensory_memory = {}
                    cls._instance.max_sensory_events = 100
        return cls._instance

    def __init__(self):
        # Initialized in __new__
        pass

    def store_event(
        self,
        db: DbSession,
        session_id: str,
        primary_modality: str,
        summary: Optional[str] = None,
        text_payload: Optional[dict] = None,
        audio_payload: Optional[dict] = None,
        workspace_payload: Optional[dict] = None
    ) -> MemoryEvent:
        """Stores event in SQLite database and caches it in sensory memory with FIFO limits."""
        # SQLite storage
        db_event = MemoryEvent(
            session_id=session_id,
            primary_modality=primary_modality,
            summary=summary
        )
        if text_payload:
            db_event.text_payload = TextPayload(**text_payload)
        if audio_payload:
            db_event.audio_payload = AudioPayload(**audio_payload)
        if workspace_payload:
            db_event.workspace_payload = WorkspacePayload(**workspace_payload)

        created_event = memory_repo.create(db, db_event)

        # In-Memory Cache (Sensory Memory)
        if session_id not in self._sensory_cache:
            self._sensory_cache[session_id] = []
            
        event_dict = {
            "event_id": created_event.event_id,
            "primary_modality": primary_modality,
            "summary": summary,
            "created_at": created_event.created_at.isoformat(),
            "text_payload": text_payload,
            "audio_payload": audio_payload,
            "workspace_payload": workspace_payload
        }
        
        # Apply cache capacity limit (FIFO)
        self._sensory_cache[session_id].append(event_dict)
        if len(self._sensory_cache[session_id]) > self.max_sensory_events:
            self._sensory_cache[session_id].pop(0)
            memory_logger.debug(f"Evicted oldest sensory event for session {session_id} (limit={self.max_sensory_events})")

        memory_logger.info(f"Recorded sensory event {created_event.event_id} for session {session_id}")
        return created_event

    def get_recent_context(self, session_id: str, limit: int = 5) -> List[dict]:
        """Retrieves recent sensory events from in-memory cache."""
        events = self._sensory_cache.get(session_id, [])
        return events[-limit:]

    def get_working_memory(self, db: DbSession, session_id: Optional[str] = None) -> dict:
        """Retrieves active goals and recent sensory workspace telemetry."""
        # Query active goals from repository
        active_goals = goal_repo.get_active(db)
        goals_data = [
            {"goal_id": g.goal_id, "description": g.description, "target_date": g.target_date.isoformat() if g.target_date else None, "status": g.status}
            for g in active_goals
        ]
        
        # Pull recent workspace metadata
        recent_telemetry = None
        if session_id and session_id in self._sensory_cache:
            for event in reversed(self._sensory_cache[session_id]):
                if event.get("workspace_payload"):
                    recent_telemetry = event["workspace_payload"]
                    break

        return {
            "active_goals": goals_data,
            "active_context": recent_telemetry
        }

    def store_longterm_memory(
        self,
        db: DbSession,
        learning_history_in: Optional[dict] = None,
        project_tracker_in: Optional[dict] = None
    ) -> dict:
        """Persists lessons or project info directly into SQLite."""
        results = {}
        if learning_history_in:
            history_obj = LearningHistory(**learning_history_in)
            created_history = learning_repo.create(db, history_obj)
            results["learning_history"] = created_history
            
        if project_tracker_in:
            project_obj = ProjectTracker(**project_tracker_in)
            created_project = project_repo.create(db, project_obj)
            results["project_tracker"] = created_project
            
        return results

    def close_session(self, db: Optional[DbSession] = None, session_id: Optional[str] = None) -> Optional[Session]:
        """Closes a session, generates a deterministic summary, and evicts sensory cache."""
        if not db or not session_id:
            memory_logger.warning("close_session() called without db or session_id context. Skipping database updates.")
            return None

        db_session = session_repo.get(db, session_id)
        if not db_session:
            raise ValueError(f"Session {session_id} not found")

        cached_events = self._sensory_cache.get(session_id, [])
        
        # Delegate summary generation to builder
        generated_summary = session_summary_builder.build_summary(cached_events)

        # Update DB session
        db_session.closed_at = datetime.utcnow()
        db_session.summary = generated_summary
        
        db.commit()
        db.refresh(db_session)

        # Evict in-memory sensory cache
        if session_id in self._sensory_cache:
            del self._sensory_cache[session_id]

        memory_logger.info(f"Session {session_id} closed. Sensory cache evicted.")
        return db_session

    def get_cache_size(self, session_id: str) -> int:
        return len(self._sensory_cache.get(session_id, []))

    def get_active_sessions_count(self) -> int:
        return len(self._sensory_cache)
        
    # Maintain compatibility with existing code/tests
    def update_sensory_memory(self, payload: TelemetryPayload) -> None:
        """Saves transient active workspace selection, cursor index, and compiler diagnostics in-memory."""
        memory_logger.debug(f"Updating sensory memory: active_file={payload.active_file}")
        self.sensory_memory = {
            "active_file": payload.active_file,
            "cursor_line": payload.cursor_line,
            "compiler_error": payload.compiler_error,
            "selection_empty": payload.selection_empty
        }

    def get_active_context(self) -> str:
        """Retrieves formatted workspace telemetry and short-term dialogue context."""
        memory_logger.debug("Retrieving active memory context card.")
        active_file = self.sensory_memory.get("active_file", "None")
        cursor_line = self.sensory_memory.get("cursor_line", 0)
        compiler_err = self.sensory_memory.get("compiler_error") or "None"
        
        context_card = (
            f"- Active File: {active_file}\n"
            f"- Cursor Line: {cursor_line}\n"
            f"- Last Compiler Diagnostics: {compiler_err}\n"
        )
        return context_card

    def record_interruption(self) -> None:
        pass

memory_manager = MemoryManager()
