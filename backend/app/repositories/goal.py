from app.repositories.base import BaseRepository
from app.models.database_models import GoalTracker

class GoalTrackerRepository(BaseRepository[GoalTracker]):
    def __init__(self):
        super().__init__(model=GoalTracker, pk_name="goal_id")

goal_repo = GoalTrackerRepository()
