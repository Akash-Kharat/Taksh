from typing import List
from sqlalchemy.orm import Session as DbSession
from app.repositories.base import BaseRepository
from app.models.database_models import MemoryEvent

class MemoryEventRepository(BaseRepository[MemoryEvent]):
    def __init__(self):
        super().__init__(model=MemoryEvent, pk_name="event_id")

    def get_by_session(self, db: DbSession, session_id: str, skip: int = 0, limit: int = 100) -> List[MemoryEvent]:
        return db.query(self.model).filter(self.model.session_id == session_id).offset(skip).limit(limit).all()

memory_repo = MemoryEventRepository()
