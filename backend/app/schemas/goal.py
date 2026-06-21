from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict

GoalStatusType = Literal["active", "completed", "paused", "cancelled"]

class GoalTrackerBase(BaseModel):
    description: str
    status: GoalStatusType = "active"
    target_date: Optional[datetime] = None

class GoalTrackerCreate(GoalTrackerBase):
    goal_id: Optional[str] = None

class GoalTrackerUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[GoalStatusType] = None
    target_date: Optional[datetime] = None

class GoalTrackerResponse(GoalTrackerBase):
    goal_id: str
    
    model_config = ConfigDict(from_attributes=True)
