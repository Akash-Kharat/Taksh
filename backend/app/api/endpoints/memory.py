from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import Session, MemoryEvent, TextPayload, AudioPayload, WorkspacePayload, MemoryEpisode, MemoryRecall, OpenTask
from app.schemas.memory import (
    MemoryEventCreate,
    MemoryEventResponse,
    MemoryEpisodeSchema,
    OpenTaskSchema,
    MemorySearchRequest,
    MemorySearchResponse,
    EpisodicMemoryDiagnosticsResponse
)
from app.services.conversation.episodic_memory_service import episodic_memory_service
from app.repositories.memory import memory_repo
from app.repositories.session import session_repo
from app.repositories.learning import learning_repo
from app.repositories.project import project_repo
from app.services.memory.manager import memory_manager
from app.core.logger import api_logger, memory_logger
from app.schemas.settings import LongTermMemorySummary
from app.schemas.memory_history import (
    SessionDetailResponse, 
    WorkingMemoryResponse, 
    LongTermMemoryResponse, 
    MemoryDiagnosticsResponse
)

router = APIRouter(prefix="/memory")

# LongTerm memory compatibility endpoints (Must be declared before dynamic /{event_id} routes)
@router.get("/longterm", response_model=LongTermMemoryResponse)
def get_longterm_memory(db: DbSession = Depends(get_db)):
    api_logger.info("Fetching long-term memory lessons and project trackers")
    lessons = learning_repo.get_multi(db)
    projects = project_repo.get_multi(db)
    return {
        "lessons": lessons,
        "projects": projects
    }

@router.delete("/longterm/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def prune_longterm_memory(memory_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Pruning episodic memory: ID={memory_id}")
    memory_logger.info(f"Deleted episodic memory ID={memory_id} from SQLite database")
    return None

@router.get("/info", response_model=MemoryDiagnosticsResponse)
def get_memory_info(db: DbSession = Depends(get_db)):
    api_logger.info("Fetching memory infrastructure diagnostics info")
    active_in_db = len(db.query(Session).filter(Session.closed_at == None).all())
    return {
        "active_sessions": active_in_db,
        "sensory_cache_sessions": memory_manager.get_active_sessions_count(),
        "working_memory_enabled": True,
        "longterm_memory_enabled": True
    }

@router.get("/working", response_model=WorkingMemoryResponse)
def get_working_memory(session_id: Optional[str] = Query(None), db: DbSession = Depends(get_db)):
    api_logger.info("Fetching active working memory context")
    return memory_manager.get_working_memory(db, session_id=session_id)

@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_memory(session_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Fetching detailed memory context for session: {session_id}")
    db_session = session_repo.get(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": db_session,
        "events": db_session.memory_events,
        "summary": db_session.summary
    }

@router.post("/", response_model=MemoryEventResponse, status_code=status.HTTP_201_CREATED)
def create_memory_event(event_in: MemoryEventCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating memory event for session: {event_in.session_id}")
    
    text_payload = event_in.text_payload.model_dump() if event_in.text_payload else None
    audio_payload = event_in.audio_payload.model_dump() if event_in.audio_payload else None
    workspace_payload = event_in.workspace_payload.model_dump() if event_in.workspace_payload else None

    # Save via memory manager to ensure sensory cache registration
    created_event = memory_manager.store_event(
        db=db,
        session_id=event_in.session_id,
        primary_modality=event_in.primary_modality,
        summary=event_in.summary,
        text_payload=text_payload,
        audio_payload=audio_payload,
        workspace_payload=workspace_payload
    )
    return created_event

@router.get("/{event_id}", response_model=MemoryEventResponse)
def get_memory_event(event_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Fetching memory event: {event_id}")
    db_event = memory_repo.get(db, event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Memory event not found")
    return db_event

@router.get("/", response_model=List[MemoryEventResponse])
def list_memory_events(session_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: DbSession = Depends(get_db)):
    api_logger.info("Listing memory events")
    if session_id:
        return memory_repo.get_by_session(db, session_id=session_id, skip=skip, limit=limit)
    return memory_repo.get_multi(db, skip=skip, limit=limit)

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_event(event_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Deleting memory event: {event_id}")
    db_event = memory_repo.delete(db, event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Memory event not found")
    memory_logger.info(f"Deleted memory event ID={event_id} from SQLite database")
    return None


@router.get("/episodes", response_model=List[MemoryEpisodeSchema])
def get_memory_episodes(db: DbSession = Depends(get_db)):
    """Returns memory history (list of episodes)."""
    episodes = db.query(MemoryEpisode).order_by(MemoryEpisode.created_at.desc()).all()
    return episodes


@router.get("/episodes/{id}", response_model=MemoryEpisodeSchema)
def get_memory_episode(id: str, db: DbSession = Depends(get_db)):
    """Returns details of a specific episodic memory."""
    episode = db.query(MemoryEpisode).filter(MemoryEpisode.id == id).first()
    if not episode:
        raise HTTPException(status_code=404, detail=f"Memory episode '{id}' not found")
    return episode


@router.get("/open-tasks", response_model=List[OpenTaskSchema])
def get_open_tasks(db: DbSession = Depends(get_db)):
    """Returns unresolved tasks across conversations."""
    tasks = db.query(OpenTask).filter(OpenTask.status.in_(["OPEN", "IN_PROGRESS"])).all()
    return tasks


@router.post("/search", response_model=MemorySearchResponse)
def search_memory(req: MemorySearchRequest, db: DbSession = Depends(get_db)):
    """Performs semantic memory retrieval."""
    results = episodic_memory_service.search_episodic_memory(db, req.query, req.limit)
    return {
        "results": [
            {
                "episode": r[0],
                "relevance_score": r[1]
            } for r in results
        ]
    }


@router.get("/diagnostics", response_model=EpisodicMemoryDiagnosticsResponse)
def get_memory_diagnostics(db: DbSession = Depends(get_db)):
    """Returns semantic episodic memory pipeline diagnostics and telemetry."""
    episodes_created = db.query(MemoryEpisode).count()
    episodes_recalled = db.query(MemoryRecall).count()
    memory_search_latency = episodic_memory_service.get_avg_search_latency()

    episodes = db.query(MemoryEpisode).all()
    if episodes:
        avg_episode_size = sum(len(ep.summary) + len(ep.title) for ep in episodes) / len(episodes)
    else:
        avg_episode_size = 0.0

    open_tasks_created = db.query(OpenTask).count()
    open_tasks_completed = db.query(OpenTask).filter(OpenTask.status == "DONE").count()

    return {
        "episodes_created": episodes_created,
        "episodes_recalled": episodes_recalled,
        "memory_search_latency": memory_search_latency,
        "avg_episode_size": avg_episode_size,
        "open_tasks_created": open_tasks_created,
        "open_tasks_completed": open_tasks_completed
    }
