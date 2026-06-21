from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class OrchestratorPlanRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class SkillConfidence(BaseModel):
    skill: str
    score: int

class PromptPackage(BaseModel):
    system_prompt: str
    user_prompt: str
    preview: str
    prompt_version: str

class MemoryItemsUsed(BaseModel):
    active_goals: List[str]
    recent_events: List[str]

class DecisionTrace(BaseModel):
    selected_skills: List[SkillConfidence]
    knowledge_chunks_used: List[str]
    memory_items_used: MemoryItemsUsed

class OrchestratorPlanResponse(BaseModel):
    query: str
    prompt_package: PromptPackage
    decision_trace: DecisionTrace

class OrchestratorInfoResponse(BaseModel):
    total_traces: int
    most_selected_skill: Optional[str] = None
    avg_knowledge_chunks: float
    avg_memory_items: float
    available_skills_count: int
    status: str
