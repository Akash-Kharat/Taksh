import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import desc

from app.core.config import settings
from app.core.logger import workspace_logger
from app.models.database_models import WorkspaceSnapshot, WorkspaceEvent
from app.services.workspace.scanner import RepositoryScanner
from app.services.workspace.git import GitIntelligence

class WorkspaceManager:
    def __init__(self, workspace_dir = None):
        self.scanner = RepositoryScanner(workspace_dir=workspace_dir)
        self.git_intel = GitIntelligence(workspace_dir=workspace_dir)

    def create_snapshot(
        self,
        db: DbSession,
        session_id: Optional[str] = None,
        active_file_path: Optional[str] = None,
        active_file_language: Optional[str] = None,
        cursor_line: Optional[int] = None,
        cursor_column: Optional[int] = None,
        selection_content: Optional[str] = None
    ) -> WorkspaceSnapshot:
        """
        Creates and persists a new WorkspaceSnapshot, subject to rate-limiting and deduplication.
        """
        now = datetime.utcnow()
        
        # 1. Rate Limiting check: MIN_SNAPSHOT_INTERVAL_SECONDS
        query = db.query(WorkspaceSnapshot)
        if session_id:
            query = query.filter(WorkspaceSnapshot.session_id == session_id)
        latest_snapshot = query.order_by(desc(WorkspaceSnapshot.created_at)).first()

        if latest_snapshot:
            elapsed = (now - latest_snapshot.created_at).total_seconds()
            if elapsed < settings.MIN_SNAPSHOT_INTERVAL_SECONDS:
                workspace_logger.info(f"Rate limit hit. Reusing latest snapshot (created {elapsed:.1f}s ago).")
                return latest_snapshot

        # 2. Gather git and directory info
        git_info = self.git_intel.get_git_info()
        languages, frameworks, scan_limit_reached = self.scanner.scan()

        # 3. Handle selection content budgeting and truncation
        selection_truncated = False
        final_selection = selection_content
        if selection_content and len(selection_content) > settings.MAX_SELECTION_CONTENT_CHARS:
            final_selection = selection_content[:settings.MAX_SELECTION_CONTENT_CHARS]
            selection_truncated = True
            workspace_logger.info(f"Selection content truncated from {len(selection_content)} to {settings.MAX_SELECTION_CONTENT_CHARS} chars.")

        # 4. Calculate workspace hash
        # Inputs: active file path, git branch, git status, detected frameworks, detected languages
        hash_payload = {
            "active_file_path": active_file_path or "",
            "git_branch": git_info["branch"],
            "git_status": git_info["status"],
            "detected_frameworks": frameworks,
            "detected_languages": languages
        }
        serialized_payload = json.dumps(hash_payload, sort_keys=True)
        workspace_hash = hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()

        # 5. Deduplication check: Reuse snapshot if hash is identical
        if latest_snapshot and latest_snapshot.workspace_hash == workspace_hash:
            # Check if active file metadata is also identical
            if (latest_snapshot.active_file_path == active_file_path and
                    latest_snapshot.cursor_line == cursor_line and
                    latest_snapshot.cursor_column == cursor_column and
                    latest_snapshot.selection_content == final_selection):
                workspace_logger.info("Workspace state is identical to latest snapshot. Reusing latest snapshot.")
                return latest_snapshot

        # 6. Create and save new snapshot
        repo_path = str(self.scanner.workspace_dir)
        repo_name = Path(self.scanner.workspace_dir).resolve().name

        new_snapshot = WorkspaceSnapshot(
            session_id=session_id,
            repo_name=repo_name,
            repo_path=repo_path,
            active_file_path=active_file_path,
            active_file_language=active_file_language,
            cursor_line=cursor_line,
            cursor_column=cursor_column,
            selection_content=final_selection,
            selection_truncated=selection_truncated,
            git_branch=git_info["branch"],
            git_status=git_info["status"],
            git_recent_commits=git_info["recent_commits"][:settings.MAX_RECENT_COMMITS],
            detected_languages=languages,
            detected_frameworks=frameworks[:settings.MAX_FRAMEWORKS],
            scan_limit_reached=scan_limit_reached,
            workspace_hash=workspace_hash,
            created_at=now
        )

        db.add(new_snapshot)
        try:
            db.commit()
            db.refresh(new_snapshot)
            workspace_logger.info(f"Created new WorkspaceSnapshot {new_snapshot.snapshot_id}")
            return new_snapshot
        except Exception as e:
            db.rollback()
            workspace_logger.error(f"Failed to persist WorkspaceSnapshot: {e}")
            raise e

    def get_latest_snapshot(self, db: DbSession, session_id: Optional[str] = None) -> Optional[WorkspaceSnapshot]:
        query = db.query(WorkspaceSnapshot)
        if session_id:
            query = query.filter(WorkspaceSnapshot.session_id == session_id)
        return query.order_by(desc(WorkspaceSnapshot.created_at)).first()

    def get_active_errors(self, db: DbSession, session_id: Optional[str] = None) -> List[WorkspaceEvent]:
        """
        Retrieves active, unresolved errors within the retention period, limited to budget.
        """
        retention_cutoff = datetime.utcnow() - timedelta(days=settings.ERROR_RETENTION_DAYS)
        query = db.query(WorkspaceEvent).filter(
            WorkspaceEvent.resolved == False,
            WorkspaceEvent.created_at >= retention_cutoff
        )
        if session_id:
            query = query.filter(WorkspaceEvent.session_id == session_id)
        
        # Enforce budget: MAX_WORKSPACE_ERRORS
        return query.order_by(desc(WorkspaceEvent.created_at)).limit(settings.MAX_WORKSPACE_ERRORS).all()

    def log_event(
        self,
        db: DbSession,
        event_type: str,
        source: str,
        severity: str,
        message: str,
        details: Dict[str, Any],
        session_id: Optional[str] = None,
        snapshot_id: Optional[str] = None
    ) -> WorkspaceEvent:
        """
        Creates and persists a workspace event (e.g. build error, test failure).
        """
        new_event = WorkspaceEvent(
            session_id=session_id,
            snapshot_id=snapshot_id,
            event_type=event_type,
            source=source,
            severity=severity,
            message=message,
            details=details,
            resolved=False,
            created_at=datetime.utcnow()
        )
        db.add(new_event)
        try:
            db.commit()
            db.refresh(new_event)
            workspace_logger.info(f"Logged workspace event {new_event.event_id} ({event_type})")
            return new_event
        except Exception as e:
            db.rollback()
            workspace_logger.error(f"Failed to log WorkspaceEvent: {e}")
            raise e

    def resolve_events(self, db: DbSession, event_ids: Optional[List[str]] = None) -> int:
        """
        Resolves events. If event_ids is provided, resolves only those. Otherwise, resolves all unresolved events.
        """
        query = db.query(WorkspaceEvent).filter(WorkspaceEvent.resolved == False)
        if event_ids:
            query = query.filter(WorkspaceEvent.event_id.in_(event_ids))

        unresolved = query.all()
        count = len(unresolved)
        for ev in unresolved:
            ev.resolved = True
        
        try:
            db.commit()
            workspace_logger.info(f"Resolved {count} workspace events.")
            return count
        except Exception as e:
            db.rollback()
            workspace_logger.error(f"Failed to resolve workspace events: {e}")
            raise e
