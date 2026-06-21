from app.repositories.base import BaseRepository
from app.models.database_models import Session

class SessionRepository(BaseRepository[Session]):
    def __init__(self):
        super().__init__(model=Session, pk_name="session_id")

session_repo = SessionRepository()
