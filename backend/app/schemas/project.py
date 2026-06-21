from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ProjectTrackerBase(BaseModel):
    project_name: str
    tech_stack: Optional[List[str]] = None
    historical_adr_keys: Optional[List[str]] = None

class ProjectTrackerCreate(ProjectTrackerBase):
    project_id: Optional[str] = None

class ProjectTrackerUpdate(BaseModel):
    project_name: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    historical_adr_keys: Optional[List[str]] = None

class ProjectTrackerResponse(ProjectTrackerBase):
    project_id: str
    
    model_config = ConfigDict(from_attributes=True)
