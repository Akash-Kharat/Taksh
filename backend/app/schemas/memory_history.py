from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.goal import GoalTrackerResponse
from app.schemas.project import ProjectTrackerResponse
from app.schemas.learning import LearningHistoryResponse
from app.schemas.session import SessionResponse
from app.schemas.memory import MemoryEventResponse

class SessionDetailResponse(BaseModel):
    session: SessionResponse
    events: List[MemoryEventResponse]
    summary: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkingMemoryResponse(BaseModel):
    active_goals: List[GoalTrackerResponse]
    active_context: Optional[dict] = None

class LongTermMemoryResponse(BaseModel):
    lessons: List[LearningHistoryResponse]
    projects: List[ProjectTrackerResponse]

class MemoryDiagnosticsResponse(BaseModel):
    active_sessions: int
    sensory_cache_sessions: int
    working_memory_enabled: bool
    longterm_memory_enabled: bool
