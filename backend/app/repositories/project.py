from app.repositories.base import BaseRepository
from app.models.database_models import ProjectTracker

class ProjectTrackerRepository(BaseRepository[ProjectTracker]):
    def __init__(self):
        super().__init__(model=ProjectTracker, pk_name="project_id")

project_repo = ProjectTrackerRepository()
