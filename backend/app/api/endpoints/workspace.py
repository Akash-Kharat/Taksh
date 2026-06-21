from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core.logger import api_logger
from app.schemas.workspace import (
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotResponse,
    WorkspaceInfoResponse,
    WorkspaceEventCreate,
    WorkspaceEventResponse,
    WorkspaceResolveRequest,
    WorkspaceResolveResponse
)
from app.services.workspace.manager import WorkspaceManager

router = APIRouter(prefix="/workspace")
manager = WorkspaceManager()

@router.post("/snapshot", response_model=WorkspaceSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_snapshot(payload: WorkspaceSnapshotRequest, db: DbSession = Depends(get_db)):
    api_logger.info("Creating a new workspace snapshot via API")
    try:
        snapshot = manager.create_snapshot(
            db=db,
            session_id=payload.session_id,
            active_file_path=payload.active_file_path,
            active_file_language=payload.active_file_language,
            cursor_line=payload.cursor_line,
            cursor_column=payload.cursor_column,
            selection_content=payload.selection_content
        )
        return snapshot
    except Exception as e:
        api_logger.error(f"Error creating snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating snapshot: {e}"
        )

@router.get("/current", response_model=WorkspaceSnapshotResponse)
def get_current_snapshot(session_id: Optional[str] = None, db: DbSession = Depends(get_db)):
    api_logger.info("Retrieving latest workspace snapshot via API")
    snapshot = manager.get_latest_snapshot(db, session_id=session_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workspace snapshot found."
        )
    return snapshot

@router.get("/info", response_model=WorkspaceInfoResponse)
def get_workspace_info(session_id: Optional[str] = None, db: DbSession = Depends(get_db)):
    api_logger.info("Retrieving workspace info metadata via API")
    snapshot = manager.get_latest_snapshot(db, session_id=session_id)
    if not snapshot:
        # Generate one on the fly without active file details
        snapshot = manager.create_snapshot(db, session_id=session_id)
    return snapshot

@router.post("/event", response_model=WorkspaceEventResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_event(payload: WorkspaceEventCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating a new workspace event '{payload.event_type}' via API")
    # Retrieve latest snapshot if any
    snapshot = manager.get_latest_snapshot(db, session_id=payload.session_id)
    snapshot_id = snapshot.snapshot_id if snapshot else None
    
    try:
        event = manager.log_event(
            db=db,
            event_type=payload.event_type,
            source=payload.source,
            severity=payload.severity,
            message=payload.message,
            details=payload.details,
            session_id=payload.session_id,
            snapshot_id=snapshot_id
        )
        return event
    except Exception as e:
        api_logger.error(f"Error logging workspace event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging workspace event: {e}"
        )

@router.get("/errors", response_model=List[WorkspaceEventResponse])
def get_active_errors(session_id: Optional[str] = None, db: DbSession = Depends(get_db)):
    api_logger.info("Retrieving unresolved workspace errors via API")
    return manager.get_active_errors(db, session_id=session_id)

@router.post("/events/resolve", response_model=WorkspaceResolveResponse)
def resolve_workspace_events(payload: WorkspaceResolveRequest, db: DbSession = Depends(get_db)):
    api_logger.info("Resolving workspace events via API")
    try:
        count = manager.resolve_events(db, event_ids=payload.event_ids)
        return {"status": "success", "count": count}
    except Exception as e:
        api_logger.error(f"Error resolving events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving events: {e}"
        )
