"""
Taksh Backup & Export Framework — MS-19

Exports conversation history, episodes, projects, preferences, and tasks
to JSON or ZIP format with mandatory versioning metadata.

No secrets or API keys are ever included in exports.
No import support is required in this milestone.
"""
import io
import json
import zipfile
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

logger = logging.getLogger("backup")

BACKUP_VERSION = "1"
TAKSH_VERSION  = "0.1"


def _get_schema_version() -> str:
    """Return the current Alembic migration head revision."""
    try:
        from alembic.runtime.migration import MigrationContext
        from app.core.database import engine
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            heads = ctx.get_current_heads()
            return ",".join(sorted(heads)) if heads else "unknown"
    except Exception as exc:
        logger.warning(f"[backup] Could not determine schema version: {exc}")
        return "unknown"


class BackupManager:
    """Creates full data exports with versioning metadata."""

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_json(self, db: Session) -> Dict[str, Any]:
        """
        Build and return a fully serialisable export dict.

        Structure:
          {
            "backup_version": "1",
            "taksh_version": "0.1",
            "created_at": "<ISO-8601>",
            "schema_version": "<alembic_head>",
            "data": { ... }
          }
        """
        from app.models.database_models import (
            ConversationRuntimeSession,
            ConversationTurn,
            MemoryEpisode,
            ProjectMemory,
            ProjectSnapshot,
            PreferenceMemory,
            OpenTask,
        )

        # Conversations + their turns
        sessions = db.query(ConversationRuntimeSession).all()
        conversations = []
        for s in sessions:
            turns = (
                db.query(ConversationTurn)
                .filter(ConversationTurn.runtime_session_id == s.runtime_session_id)
                .all()
            )
            conversations.append({
                "runtime_session_id": s.runtime_session_id,
                "voice_session_id": s.voice_session_id,
                "conversation_state": s.conversation_state,
                "conversation_session_state": s.conversation_session_state,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "correlation_id": s.correlation_id,
                "turns": [
                    {
                        "turn_id": t.turn_id,
                        "user_text": t.user_text,
                        "assistant_text": t.assistant_text,
                        "provider_name": t.provider_name,
                        "latency_ms": t.latency_ms,
                        "started_at": t.started_at.isoformat() if t.started_at else None,
                        "correlation_id": t.correlation_id,
                    }
                    for t in turns
                ],
            })

        # Episodes
        episodes = db.query(MemoryEpisode).all()
        episodes_data = [
            {
                "id": e.id,
                "session_id": e.session_id,
                "memory_type": e.memory_type,
                "title": e.title,
                "summary": e.summary,
                "key_decisions": e.key_decisions,
                "important_facts": e.important_facts,
                "open_tasks": e.open_tasks,
                "importance_score": e.importance_score,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "correlation_id": e.correlation_id,
            }
            for e in episodes
        ]

        # Projects + snapshots
        projects = db.query(ProjectMemory).all()
        projects_data = []
        for p in projects:
            snapshots = (
                db.query(ProjectSnapshot)
                .filter(ProjectSnapshot.project_name == p.project_name)
                .all()
            )
            projects_data.append({
                "project_memory_id": p.project_memory_id,
                "project_name": p.project_name,
                "status": p.status,
                "summary": p.summary,
                "current_milestone": p.current_milestone,
                "snapshots": [
                    {
                        "snapshot_id": s.snapshot_id,
                        "milestone": s.milestone,
                        "summary": s.summary,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in snapshots
                ],
            })

        # Preferences
        preferences = db.query(PreferenceMemory).all()
        preferences_data = [
            {
                "preference_id": p.preference_id,
                "category": p.category,
                "value": p.value,
                "confidence_score": p.confidence_score,
            }
            for p in preferences
        ]

        # Open tasks
        tasks = db.query(OpenTask).all()
        tasks_data = [
            {
                "id": t.id,
                "episode_id": t.episode_id,
                "description": t.description,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]

        return {
            "backup_version": BACKUP_VERSION,
            "taksh_version": TAKSH_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "schema_version": _get_schema_version(),
            "data": {
                "conversations": conversations,
                "memory_episodes": episodes_data,
                "projects": projects_data,
                "preferences": preferences_data,
                "open_tasks": tasks_data,
            },
        }

    # ------------------------------------------------------------------
    # ZIP export
    # ------------------------------------------------------------------

    def export_zip(self, db: Session) -> bytes:
        """Wrap the JSON export inside a ZIP archive and return raw bytes."""
        data = self.export_json(db)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"taksh_backup_{timestamp}.json"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, json.dumps(data, indent=2, ensure_ascii=False))
        return buf.getvalue()


# Module-level singleton
backup_manager = BackupManager()
