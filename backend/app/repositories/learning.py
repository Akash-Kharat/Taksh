from app.repositories.base import BaseRepository
from app.models.database_models import LearningHistory

class LearningHistoryRepository(BaseRepository[LearningHistory]):
    def __init__(self):
        super().__init__(model=LearningHistory, pk_name="concept_id")

learning_repo = LearningHistoryRepository()
