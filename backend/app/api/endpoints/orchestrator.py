from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from collections import Counter

from app.core.database import get_db
from app.services.cognitive.orchestrator import CognitiveOrchestrator
from app.services.skills.registry import SkillsRegistry
from app.models.database_models import CognitiveTrace
from app.schemas.orchestrator import (
    OrchestratorPlanRequest,
    OrchestratorPlanResponse,
    OrchestratorInfoResponse
)

router = APIRouter()

@router.post("/orchestrator/plan", response_model=OrchestratorPlanResponse)
def generate_orchestrator_plan(
    payload: OrchestratorPlanRequest,
    db: DbSession = Depends(get_db)
):
    orchestrator = CognitiveOrchestrator()
    plan = orchestrator.generate_plan(db, payload.query, session_id=payload.session_id)
    return plan

@router.get("/orchestrator/info", response_model=OrchestratorInfoResponse)
def get_orchestrator_info(db: DbSession = Depends(get_db)):
    traces = db.query(CognitiveTrace).all()
    total_traces = len(traces)
    
    most_selected_skill = None
    avg_knowledge_chunks = 0.0
    avg_memory_items = 0.0
    
    if total_traces > 0:
        skill_counter = Counter()
        total_chunks = 0
        total_memory_items = 0
        
        for trace in traces:
            # selected_skills is a list of dicts: [{"skill": name, "score": score}]
            for skill_info in (trace.selected_skills or []):
                skill_counter[skill_info.get("skill")] += 1
                
            # knowledge_chunks is a list of chunk ids
            total_chunks += len(trace.knowledge_chunks or [])
            
            # memory_items is a dict {"active_goals": [...], "recent_events": [...]}
            m_items = trace.memory_items or {}
            goals_count = len(m_items.get("active_goals", []))
            events_count = len(m_items.get("recent_events", []))
            total_memory_items += (goals_count + events_count)
            
        if skill_counter:
            most_selected_skill = skill_counter.most_common(1)[0][0]
            
        avg_knowledge_chunks = round(total_chunks / total_traces, 2)
        avg_memory_items = round(total_memory_items / total_traces, 2)

    # Load registry to find available skills count
    registry = SkillsRegistry()
    registry.load_manifests()
    available_skills_count = len(registry.skills)

    return {
        "total_traces": total_traces,
        "most_selected_skill": most_selected_skill,
        "avg_knowledge_chunks": avg_knowledge_chunks,
        "avg_memory_items": avg_memory_items,
        "available_skills_count": available_skills_count,
        "status": "ready"
    }
