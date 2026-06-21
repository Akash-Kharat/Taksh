from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import GoalTracker
from app.schemas.goal import GoalTrackerCreate, GoalTrackerUpdate, GoalTrackerResponse
from app.repositories.goal import goal_repo
from app.core.logger import api_logger

router = APIRouter(prefix="/goals")

@router.post("/", response_model=GoalTrackerResponse, status_code=status.HTTP_201_CREATED)
def create_goal(goal_in: GoalTrackerCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating a goal record: {goal_in.description[:30]}")
    db_goal = GoalTracker(
        goal_id=goal_in.goal_id,
        description=goal_in.description,
        status=goal_in.status,
        target_date=goal_in.target_date
    )
    return goal_repo.create(db, db_goal)

@router.get("/{goal_id}", response_model=GoalTrackerResponse)
def get_goal(goal_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Retrieving goal: {goal_id}")
    db_goal = goal_repo.get(db, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_goal

@router.get("/", response_model=List[GoalTrackerResponse])
def list_goals(skip: int = 0, limit: int = 100, db: DbSession = Depends(get_db)):
    api_logger.info("Listing goals")
    return goal_repo.get_multi(db, skip=skip, limit=limit)

@router.put("/{goal_id}", response_model=GoalTrackerResponse)
def update_goal(goal_id: str, goal_in: GoalTrackerUpdate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Updating goal: {goal_id}")
    db_goal = goal_repo.get(db, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal_repo.update(db, db_goal, goal_in.model_dump(exclude_unset=True))

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Deleting goal: {goal_id}")
    db_goal = goal_repo.delete(db, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return None
