"""
Taksh Backup Validator — MS-20

Validates that a backup export can be successfully restored.

Process:
  1. Export current DB via BackupManager.export_json()
  2. Create a temporary in-memory SQLite database with the same schema
  3. Restore all exported records into the temp DB
  4. Verify record counts match the export

A backup is only considered valid if it can be restored successfully.
"""
import logging
from dataclasses import dataclass

from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("backup_validator")


@dataclass
class BackupValidationResult:
    valid:            bool
    export_valid:     bool
    restore_valid:    bool
    counts_match:     bool
    records_restored: int
    detail:           str


class BackupValidator:
    """Validates a backup by exporting and then restoring into a temp DB."""

    def validate(self, db: Session) -> BackupValidationResult:
        """
        Full export → restore → verify cycle.
        Returns a BackupValidationResult with all intermediate statuses.
        """
        # ----------------------------------------------------------------
        # Step 1: Export
        # ----------------------------------------------------------------
        try:
            from app.core.backup import backup_manager
            export_data = backup_manager.export_json(db)
            export_valid = True
        except Exception as exc:
            logger.error(f"[backup_validator] Export failed: {exc}")
            return BackupValidationResult(
                valid=False, export_valid=False,
                restore_valid=False, counts_match=False,
                records_restored=0, detail=f"Export failed: {exc}",
            )

        # ----------------------------------------------------------------
        # Step 2: Create temp DB and restore
        # ----------------------------------------------------------------
        records_restored = 0
        try:
            from app.models.database_models import Base
            temp_engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
            )
            Base.metadata.create_all(bind=temp_engine)
            TempSession = sessionmaker(bind=temp_engine)
            temp_db = TempSession()

            records_restored = self._restore(export_data["data"], temp_db)
            temp_db.commit()
            restore_valid = True
        except Exception as exc:
            logger.error(f"[backup_validator] Restore failed: {exc}")
            return BackupValidationResult(
                valid=False, export_valid=True,
                restore_valid=False, counts_match=False,
                records_restored=records_restored,
                detail=f"Restore failed: {exc}",
            )
        finally:
            try:
                temp_db.close()
                temp_engine.dispose()
            except Exception:
                pass

        # ----------------------------------------------------------------
        # Step 3: Verify counts
        # ----------------------------------------------------------------
        counts_match = self._verify_counts(export_data["data"], records_restored)
        valid = export_valid and restore_valid and counts_match

        detail = (
            f"Restored {records_restored} records from export. "
            f"Counts {'match' if counts_match else 'mismatch'}."
        )

        logger.info(
            f"[backup_validator] valid={valid} restored={records_restored} "
            f"counts_match={counts_match}"
        )

        return BackupValidationResult(
            valid            = valid,
            export_valid     = export_valid,
            restore_valid    = restore_valid,
            counts_match     = counts_match,
            records_restored = records_restored,
            detail           = detail,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _restore(self, data: dict, temp_db: Session) -> int:
        """
        Restores exported data into the temp DB.
        Returns the total number of records inserted.
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
        from datetime import datetime

        def _dt(val):
            if val is None:
                return None
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return val

        count = 0

        # Conversations + turns
        for conv in data.get("conversations", []):
            session = ConversationRuntimeSession(
                runtime_session_id         = conv["runtime_session_id"],
                voice_session_id           = conv.get("voice_session_id"),
                conversation_state         = conv.get("conversation_state", "idle"),
                conversation_session_state = conv.get("conversation_session_state", "closed"),
                current_turn_owner         = conv.get("current_turn_owner", "none"),
                started_at                 = _dt(conv.get("started_at")),
                ended_at                   = _dt(conv.get("ended_at")),
                correlation_id             = conv.get("correlation_id"),
            )
            temp_db.add(session)
            count += 1
            for turn in conv.get("turns", []):
                t = ConversationTurn(
                    turn_id            = turn["turn_id"],
                    runtime_session_id = conv["runtime_session_id"],
                    user_text          = turn.get("user_text"),
                    assistant_text     = turn.get("assistant_text"),
                    provider_name      = turn.get("provider_name"),
                    latency_ms         = turn.get("latency_ms"),
                    started_at         = _dt(turn.get("started_at")),
                    correlation_id     = turn.get("correlation_id"),
                )
                temp_db.add(t)
                count += 1

        # Memory episodes
        for ep in data.get("memory_episodes", []):
            episode = MemoryEpisode(
                id               = ep["id"],
                session_id       = ep.get("session_id", ""),
                memory_type      = ep.get("memory_type", "episodic"),
                title            = ep.get("title", ""),
                summary          = ep.get("summary", ""),
                key_decisions    = ep.get("key_decisions", []),
                important_facts  = ep.get("important_facts", []),
                open_tasks       = ep.get("open_tasks", []),
                importance_score = ep.get("importance_score", 0.5),
                created_at       = _dt(ep.get("created_at")),
                correlation_id   = ep.get("correlation_id"),
            )
            temp_db.add(episode)
            count += 1

        # Projects + snapshots
        for proj in data.get("projects", []):
            pm = ProjectMemory(
                project_memory_id = proj["project_memory_id"],
                project_name      = proj.get("project_name", ""),
                status            = proj.get("status", "active"),
                summary           = proj.get("summary", ""),
                current_milestone = proj.get("current_milestone"),
            )
            temp_db.add(pm)
            count += 1
            for snap in proj.get("snapshots", []):
                ps = ProjectSnapshot(
                    snapshot_id  = snap["snapshot_id"],
                    project_name = proj["project_name"],
                    milestone    = snap.get("milestone", ""),
                    summary      = snap.get("summary", ""),
                    created_at   = _dt(snap.get("created_at")),
                )
                temp_db.add(ps)
                count += 1

        # Preferences
        for pref in data.get("preferences", []):
            p = PreferenceMemory(
                preference_id    = pref["preference_id"],
                category         = pref.get("category", ""),
                value            = pref.get("value", ""),
                confidence_score = pref.get("confidence_score", 0.5),
            )
            temp_db.add(p)
            count += 1

        # Open tasks
        for task in data.get("open_tasks", []):
            t = OpenTask(
                id          = task["id"],
                episode_id  = task.get("episode_id"),
                description = task.get("description", ""),
                status      = task.get("status", "OPEN"),
                created_at  = _dt(task.get("created_at")),
            )
            temp_db.add(t)
            count += 1

        temp_db.flush()
        return count

    def _verify_counts(self, data: dict, records_restored: int) -> bool:
        """Verify the restored record count matches the export totals."""
        expected = 0
        expected += len(data.get("conversations", []))
        expected += sum(len(c.get("turns", [])) for c in data.get("conversations", []))
        expected += len(data.get("memory_episodes", []))
        expected += len(data.get("projects", []))
        expected += sum(len(p.get("snapshots", [])) for p in data.get("projects", []))
        expected += len(data.get("preferences", []))
        expected += len(data.get("open_tasks", []))
        return records_restored == expected


# Module-level singleton
backup_validator = BackupValidator()
