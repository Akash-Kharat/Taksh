from typing import List
from sqlalchemy.orm import Session as DbSession
from app.repositories.base import BaseRepository
from app.models.database_models import GoalTracker

class GoalTrackerRepository(BaseRepository[GoalTracker]):
    def __init__(self):
        super().__init__(model=GoalTracker, pk_name="goal_id")

    def get_active(self, db: DbSession) -> List[GoalTracker]:
        """Returns only active goal tracking items."""
        return db.query(self.model).filter(self.model.status == "active").all()

goal_repo = GoalTrackerRepository()
