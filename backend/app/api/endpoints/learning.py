from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_db
from app.models.database_models import LearningHistory
from app.schemas.learning import LearningHistoryCreate, LearningHistoryUpdate, LearningHistoryResponse
from app.repositories.learning import learning_repo
from app.core.logger import api_logger

router = APIRouter(prefix="/learning-history")

@router.post("/", response_model=LearningHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_concept(concept_in: LearningHistoryCreate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Creating a learning history record: {concept_in.concept_name}")
    db_concept = LearningHistory(
        concept_id=concept_in.concept_id,
        concept_name=concept_in.concept_name,
        mastery_score=concept_in.mastery_score
    )
    return learning_repo.create(db, db_concept)

@router.get("/{concept_id}", response_model=LearningHistoryResponse)
def get_concept(concept_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Retrieving concept: {concept_id}")
    db_concept = learning_repo.get(db, concept_id)
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return db_concept

@router.get("/", response_model=List[LearningHistoryResponse])
def list_concepts(skip: int = 0, limit: int = 100, db: DbSession = Depends(get_db)):
    api_logger.info("Listing learning history")
    return learning_repo.get_multi(db, skip=skip, limit=limit)

@router.put("/{concept_id}", response_model=LearningHistoryResponse)
def update_concept(concept_id: str, concept_in: LearningHistoryUpdate, db: DbSession = Depends(get_db)):
    api_logger.info(f"Updating concept: {concept_id}")
    db_concept = learning_repo.get(db, concept_id)
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return learning_repo.update(db, db_concept, concept_in.model_dump(exclude_unset=True))

@router.delete("/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(concept_id: str, db: DbSession = Depends(get_db)):
    api_logger.info(f"Deleting concept: {concept_id}")
    db_concept = learning_repo.delete(db, concept_id)
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return None
