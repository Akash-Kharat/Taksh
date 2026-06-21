import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.logger import system_logger
from app.services.cognitive.selector import SkillSelector
from app.services.cognitive.context import ContextBuilder
from app.services.cognitive.prompt import PromptBuilder
from app.models.database_models import CognitiveTrace

class CognitiveOrchestrator:
    """Offline cognitive planning and context assembly layer."""

    def __init__(self, chroma_client = None):
        self.selector = SkillSelector()
        self.context_builder = ContextBuilder(chroma_client=chroma_client)
        self.prompt_builder = PromptBuilder()

    def generate_plan(self, db: DbSession, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        system_logger.info(f"Generating cognitive plan for query='{query}', session_id='{session_id}'")
        
        # 1. Determine active file from workspace telemetry in memory
        active_file = None
        working_mem = self.context_builder.memory_manager.get_working_memory(db, session_id=session_id)
        active_ctx = working_mem.get("active_context")
        if active_ctx:
            active_file = active_ctx.get("active_file")

        # 2. Select top skills (max 3, sorted by score descending)
        selected_skills = self.selector.select_skills(query, active_file=active_file)
        
        # 3. Assemble structured context under budget limits
        context = self.context_builder.build_context(
            db=db,
            query=query,
            selected_skills=selected_skills,
            session_id=session_id
        )

        # 4. Format prompt package
        prompt_package = self.prompt_builder.build_prompt_package(query, context)

        # 5. Compile decision trace parameters
        selected_skills_trace = [{"skill": s["skill"], "score": s["score"]} for s in selected_skills]
        knowledge_chunks_used = [chunk["chunk_id"] for chunk in context["knowledge"]]
        
        active_goals_trace = [g["goal_id"] for g in context["working_memory"]["active_goals"]]
        recent_events_trace = [event["event_id"] for event in context["sensory_memory"]]
        memory_items_used = {
            "active_goals": active_goals_trace,
            "recent_events": recent_events_trace
        }

        decision_trace = {
            "selected_skills": selected_skills_trace,
            "knowledge_chunks_used": knowledge_chunks_used,
            "memory_items_used": memory_items_used
        }

        # 6. Persist trace log record in database
        try:
            trace_record = CognitiveTrace(
                session_id=session_id,
                query=query,
                selected_skills=selected_skills_trace,
                knowledge_chunks=knowledge_chunks_used,
                memory_items=memory_items_used,
                prompt_version=prompt_package["prompt_version"],
                final_prompt_preview=prompt_package["preview"]
            )
            db.add(trace_record)
            db.commit()
            system_logger.info(f"Persisted CognitiveTrace {trace_record.trace_id} in database")
        except Exception as e:
            db.rollback()
            system_logger.error(f"Failed to persist CognitiveTrace: {e}")

        # 7. Format output payload
        return {
            "query": query,
            "prompt_package": prompt_package,
            "decision_trace": decision_trace
        }
