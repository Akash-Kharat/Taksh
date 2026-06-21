from typing import Optional, List
from pydantic import BaseModel

class AppSettings(BaseModel):
    personality_mode: str = "mentor"
    socratic_coaching_enabled: bool = True
    active_skills: List[str] = []

class HealthCheck(BaseModel):
    status: str = "OK"
    project: str = "Taksh"
    version: str = "0.1"

class LongTermMemorySummary(BaseModel):
    id: str
    summary: str
    importance_score: float
    created_at: str
