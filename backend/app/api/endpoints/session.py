from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import Session
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse
from app.repositories.session import session_repo
from app.core.logger import api_logger

router = APIRouter(prefix="/sessions")

@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_in: SessionCreate, db: DbSession = Depends(get_db)):
    api_logger.info("Creating a new session")
    db_session_obj = Session(
        session_id=session_in.session_id,
        closed_at=session_in.closed_at
    )
    return session_repo.create(db, db_session_obj)

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Retrieving session {session_id}")
    db_session = session_repo.get(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session

@router.get("/", response_model=List[SessionResponse])
def list_sessions(skip: int = 0, limit: int = 100, db: DbSession = Depends(get_db)):
    api_logger.info("Listing sessions")
    return session_repo.get_multi(db, skip=skip, limit=limit)

@router.put("/{session_id}", response_model=SessionResponse)
def update_session(session_id: str, session_in: SessionUpdate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Updating session {session_id}")
    db_session = session_repo.get(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_repo.update(db, db_session, session_in.model_dump(exclude_unset=True))

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Deleting session {session_id}")
    db_session = session_repo.delete(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return None
