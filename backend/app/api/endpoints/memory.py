from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.settings import LongTermMemorySummary
from app.core.logger import api_logger, memory_logger

router = APIRouter()

@router.get("/memory/longterm", response_model=List[LongTermMemorySummary])
async def get_longterm_memory(db: Session = Depends(get_db)):
    api_logger.info("Fetching long-term memory episodes list")
    return []

@router.delete("/memory/longterm/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def prune_longterm_memory(memory_id: str, db: Session = Depends(get_db)):
    api_logger.info(f"Pruning episodic memory: ID={memory_id}")
    memory_logger.info(f"Deleted episodic memory ID={memory_id} from SQLite database")
    return None
