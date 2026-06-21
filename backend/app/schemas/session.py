from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class SessionBase(BaseModel):
    closed_at: Optional[datetime] = None

class SessionCreate(SessionBase):
    session_id: Optional[str] = None

class SessionUpdate(SessionBase):
    pass

class SessionResponse(SessionBase):
    session_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
