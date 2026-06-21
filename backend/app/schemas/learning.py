from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class LearningHistoryBase(BaseModel):
    concept_name: str
    mastery_score: int = Field(default=0, ge=0, le=100)

class LearningHistoryCreate(LearningHistoryBase):
    concept_id: Optional[str] = None

class LearningHistoryUpdate(BaseModel):
    concept_name: Optional[str] = None
    mastery_score: Optional[int] = Field(None, ge=0, le=100)
    last_reviewed: Optional[datetime] = None

class LearningHistoryResponse(LearningHistoryBase):
    concept_id: str
    last_reviewed: datetime
    
    model_config = ConfigDict(from_attributes=True)
