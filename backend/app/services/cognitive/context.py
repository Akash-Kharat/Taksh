from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.logger import system_logger
from app.services.memory.identity import CoreIdentityManager
from app.services.memory.manager import MemoryManager
from app.services.knowledge.search import HybridSearchEngine
from app.repositories.learning import learning_repo
from app.repositories.project import project_repo

from app.models.database_models import (
    ConversationProfile,
    PreferenceMemory,
    ProjectMemory,
    ProjectSnapshot,
)
from app.services.conversation.relationship import RelationshipTracker


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

        # 3. Conversation Intelligence Context (MS-12)
        profile = db.query(ConversationProfile).first()
        active_project = None
        if profile and profile.active_project_id:
            active_project = (
                db.query(ProjectMemory)
                .filter(ProjectMemory.project_memory_id == profile.active_project_id)
                .first()
            )
        
        active_project_data = {}
        project_summary_data = {}
        snapshots_data = []

        if active_project:
            active_project_data = {
                "project_memory_id": active_project.project_memory_id,
                "project_name": active_project.project_name,
                "status": active_project.status,
                "current_milestone": active_project.current_milestone,
                "active_goals": active_project.active_goals,
                "open_questions": active_project.open_questions,
                "next_steps": active_project.next_steps,
            }
            project_summary_data = {
                "project_name": active_project.project_name,
                "summary": active_project.summary
            }
            
            # Retrieve project snapshots up to budget limit
            snapshots = (
                db.query(ProjectSnapshot)
                .filter(ProjectSnapshot.project_name == active_project.project_name)
                .order_by(ProjectSnapshot.created_at.desc())
                .limit(settings.MAX_PROJECT_SNAPSHOTS)
                .all()
            )
            snapshots_data = [
                {
                    "snapshot_id": s.snapshot_id,
                    "project_name": s.project_name,
                    "milestone": s.milestone,
                    "summary": s.summary,
                    "decisions": s.decisions,
                    "open_questions": s.open_questions,
                    "next_steps": s.next_steps,
                    "created_at": s.created_at.isoformat()
                } for s in snapshots
            ]

        # Retrieve preferences up to budget limit
        prefs = (
            db.query(PreferenceMemory)
            .order_by(PreferenceMemory.confidence_score.desc())
            .limit(settings.MAX_PREFERENCES)
            .all()
        )
        preferences_data = [
            {
                "preference_id": p.preference_id,
                "category": p.category,
                "value": p.value,
                "confidence_score": p.confidence_score,
                "source_session_id": p.source_session_id,
                "source_trace_id": p.source_trace_id,
                "last_confirmed_at": p.last_confirmed_at.isoformat()
            } for p in prefs
        ]

        # Relationship context
        rel_context = RelationshipTracker.get_relationship_context(db)

        # 4. Knowledge Context (RRF search limited to budget)
        search_results = self.search_engine.search(db, query, limit=settings.MAX_KNOWLEDGE_CHUNKS)
        
        # 5. Working & Long-Term Memory Context
        working_mem = self.memory_manager.get_working_memory(db, session_id=session_id)
        
        # Fetch long-term items from repositories
        lessons = learning_repo.get_multi(db)
        projects = project_repo.get_multi(db)

        # 6. Sensory Memory Context (Recent events limited to budget)
        recent_events = []
        if session_id:
            events = self.memory_manager.get_recent_context(session_id, limit=settings.MAX_RECENT_EVENTS)
            recent_events = events

        # 7. Workspace Context (Enforcing budgets)
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

        # 8. Retrieve recent conversation turns up to settings.MAX_CONVERSATION_HISTORY_TURNS, respecting character budgets (Revision 2)
        turns_data = []
        if session_id:
            from app.models.database_models import ConversationTurn
            raw_turns = (
                db.query(ConversationTurn)
                .filter(ConversationTurn.runtime_session_id == session_id)
                .order_by(ConversationTurn.started_at.desc())
                .limit(settings.MAX_CONVERSATION_HISTORY_TURNS)
                .all()
            )
            
            # Apply character budget
            accumulated_chars = 0
            selected_turns = []
            for t in raw_turns:
                turn_chars = len(t.user_text or "") + len(t.assistant_text or "")
                if accumulated_chars + turn_chars > settings.MAX_CONVERSATION_HISTORY_CHARS:
                    # character budget exceeded, skip remaining older turns
                    break
                accumulated_chars += turn_chars
                selected_turns.append(t)
            
            selected_turns.reverse()  # Make it chronological
            turns_data = [
                {
                    "user_text": t.user_text,
                    "assistant_text": t.assistant_text,
                    "cognitive_trace_id": t.cognitive_trace_id,
                    "ai_response_id": t.ai_response_id,
                    "segment_count": t.segment_count,
                    "response_truncated": t.response_truncated
                } for t in selected_turns
            ]

        # 8b. Retrieve relevant episodic memories (Milestone-18)
        # Avoid unnecessary token usage by retrieving relevant memories only if similarity score is high or explicit keywords matched
        episodic_memories_data = []
        try:
            from app.services.conversation.episodic_memory_service import episodic_memory_service
            episodic_memories_data = episodic_memory_service.retrieve_relevant_memories(
                db=db,
                query=query,
                session_id=session_id,
                limit=settings.MEMORY_RETRIEVAL_LIMIT
            )
        except Exception as e:
            system_logger.error(f"Failed to retrieve episodic memories: {e}")

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
            "workspace": workspace_data,
            # Conversation Intelligence outputs (MS-12)
            "active_project": active_project_data,
            "project_summary": project_summary_data,
            "project_snapshots": snapshots_data,
            "preferences": preferences_data,
            "relationship_context": rel_context,
            "conversation_turns": turns_data,
            "episodic_memories": episodic_memories_data
        }

