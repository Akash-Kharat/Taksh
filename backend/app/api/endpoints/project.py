from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import ProjectTracker
from app.schemas.project import ProjectTrackerCreate, ProjectTrackerUpdate, ProjectTrackerResponse
from app.repositories.project import project_repo
from app.core.logger import api_logger

router = APIRouter(prefix="/projects")

@router.post("/", response_model=ProjectTrackerResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectTrackerCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating a project record: {project_in.project_name}")
    db_project = ProjectTracker(
        project_id=project_in.project_id,
        project_name=project_in.project_name,
        tech_stack=project_in.tech_stack,
        historical_adr_keys=project_in.historical_adr_keys
    )
    return project_repo.create(db, db_project)

@router.get("/{project_id}", response_model=ProjectTrackerResponse)
def get_project(project_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Retrieving project: {project_id}")
    db_project = project_repo.get(db, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.get("/", response_model=List[ProjectTrackerResponse])
def list_projects(skip: int = 0, limit: int = 100, db: DbSession = Depends(get_db)):
    api_logger.info("Listing project trackers")
    return project_repo.get_multi(db, skip=skip, limit=limit)

@router.put("/{project_id}", response_model=ProjectTrackerResponse)
def update_project(project_id: str, project_in: ProjectTrackerUpdate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Updating project: {project_id}")
    db_project = project_repo.get(db, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_repo.update(db, db_project, project_in.model_dump(exclude_unset=True))

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Deleting project: {project_id}")
    db_project = project_repo.delete(db, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return None
