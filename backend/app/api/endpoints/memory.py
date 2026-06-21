from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import MemoryEvent, TextPayload, AudioPayload, WorkspacePayload
from app.schemas.memory import MemoryEventCreate, MemoryEventResponse
from app.repositories.memory import memory_repo
from app.core.logger import api_logger, memory_logger
from app.schemas.settings import LongTermMemorySummary

router = APIRouter(prefix="/memory")

# LongTerm memory compatibility endpoints (Must be declared before dynamic /{event_id} routes)
@router.get("/longterm", response_model=List[LongTermMemorySummary])
async def get_longterm_memory(db: DbSession = Depends(get_db)):
    api_logger.info("Fetching long-term memory episodes list")
    return []

@router.delete("/longterm/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def prune_longterm_memory(memory_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Pruning episodic memory: ID={memory_id}")
    memory_logger.info(f"Deleted episodic memory ID={memory_id} from SQLite database")
    return None

@router.post("/", response_model=MemoryEventResponse, status_code=status.HTTP_201_CREATED)
def create_memory_event(event_in: MemoryEventCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating memory event for session: {event_in.session_id}")
    
    # Extract payload data
    text_data = event_in.text_payload
    audio_data = event_in.audio_payload
    workspace_data = event_in.workspace_payload

    # Create MemoryEvent database object
    db_event = MemoryEvent(
        event_id=event_in.event_id,
        session_id=event_in.session_id,
        primary_modality=event_in.primary_modality,
        summary=event_in.summary
    )
    
    # Attach payloads if present
    if text_data:
        db_event.text_payload = TextPayload(
            transcript=text_data.transcript,
            system_prompt_injected=text_data.system_prompt_injected
        )
    if audio_data:
        db_event.audio_payload = AudioPayload(
            audio_file_path=audio_data.audio_file_path
        )
    if workspace_data:
        db_event.workspace_payload = WorkspacePayload(
            active_file=workspace_data.active_file,
            cursor_line=workspace_data.cursor_line,
            selected_code=workspace_data.selected_code,
            terminal_stderr=workspace_data.terminal_stderr
        )

    created_event = memory_repo.create(db, db_event)
    memory_logger.info(f"Created memory event {created_event.event_id} in SQLite")
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
