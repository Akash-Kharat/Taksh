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
            "sensory_memory": recent_events
        }
