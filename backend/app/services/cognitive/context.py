from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.logger import system_logger
from app.services.memory.identity import CoreIdentityManager
from app.services.memory.manager import MemoryManager
from app.services.knowledge.search import HybridSearchEngine
from app.repositories.learning import learning_repo
from app.repositories.project import project_repo

class ContextBuilder:
    """Aggregates multi-source information into structured, budget-bounded context blocks."""
    
    def __init__(self, chroma_client = None):
        self.identity_manager = CoreIdentityManager()
        self.memory_manager = MemoryManager()
        self.search_engine = HybridSearchEngine(chroma_client=chroma_client)
        from app.services.workspace.manager import WorkspaceManager
        self.workspace_manager = WorkspaceManager()

    def build_context(
        self,
        db: DbSession,
        query: str,
        selected_skills: List[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        system_logger.info("Assembling context package in ContextBuilder")
        
        # 1. Identity Context
        identity_text = self.identity_manager.get_identity()

        # 2. Skill Context (Overlays of selected skills)
        skills_overlays = []
        for s in selected_skills:
            manifest = s["manifest"]
            overlay = manifest.prompt_overlay
            constraints = "\n".join([f"- {c}" for c in overlay.technical_constraints])
            skills_overlays.append({
                "name": manifest.name,
                "role": overlay.role,
                "pedagogical_instructions": overlay.pedagogical_instructions,
                "technical_constraints": constraints
            })

        # 3. Knowledge Context (RRF search limited to budget)
        search_results = self.search_engine.search(db, query, limit=settings.MAX_KNOWLEDGE_CHUNKS)
        
        # 4. Working & Long-Term Memory Context
        working_mem = self.memory_manager.get_working_memory(db, session_id=session_id)
        
        # Fetch long-term items from repositories
        lessons = learning_repo.get_multi(db)
        projects = project_repo.get_multi(db)

        # 5. Sensory Memory Context (Recent events limited to budget)
        recent_events = []
        if session_id:
            # get all recent events from sensory cache
            events = self.memory_manager.get_recent_context(session_id, limit=settings.MAX_RECENT_EVENTS)
            recent_events = events

        # 6. Workspace Context (Enforcing budgets)
        latest_snap = self.workspace_manager.get_latest_snapshot(db, session_id=session_id)
        active_errors = self.workspace_manager.get_active_errors(db, session_id=session_id)

        workspace_data = None
        if latest_snap:
            workspace_data = {
                "repo_name": latest_snap.repo_name,
                "repo_path": latest_snap.repo_path,
                "active_file_path": latest_snap.active_file_path,
                "active_file_language": latest_snap.active_file_language,
                "cursor_line": latest_snap.cursor_line,
                "cursor_column": latest_snap.cursor_column,
                "selection_content": latest_snap.selection_content,
                "selection_truncated": latest_snap.selection_truncated,
                "git_branch": latest_snap.git_branch,
                "git_status": latest_snap.git_status,
                "git_recent_commits": latest_snap.git_recent_commits[:settings.MAX_RECENT_COMMITS],
                "detected_languages": latest_snap.detected_languages,
                "detected_frameworks": latest_snap.detected_frameworks[:settings.MAX_FRAMEWORKS],
                "scan_limit_reached": latest_snap.scan_limit_reached,
                "workspace_hash": latest_snap.workspace_hash,
                "errors": [
                    {
                        "event_id": err.event_id,
                        "event_type": err.event_type,
                        "source": err.source,
                        "severity": err.severity,
                        "message": err.message,
                        "details": err.details
                    } for err in active_errors[:settings.MAX_WORKSPACE_ERRORS]
                ]
            }
        elif active_errors:
            workspace_data = {
                "errors": [
                    {
                        "event_id": err.event_id,
                        "event_type": err.event_type,
                        "source": err.source,
                        "severity": err.severity,
                        "message": err.message,
                        "details": err.details
                    } for err in active_errors[:settings.MAX_WORKSPACE_ERRORS]
                ]
            }

        return {
            "identity": identity_text,
            "skills": skills_overlays,
            "knowledge": search_results,
            "working_memory": {
                "active_goals": working_mem.get("active_goals", []),
                "active_context": working_mem.get("active_context", None)
            },
            "longterm_memory": {
                "lessons": [
                    {"concept_name": l.concept_name, "mastery_score": l.mastery_score} for l in lessons
                ],
                "projects": [
                    {"project_name": p.project_name, "tech_stack": p.tech_stack} for p in projects
                ]
            },
            "sensory_memory": recent_events,
            "workspace": workspace_data
        }

