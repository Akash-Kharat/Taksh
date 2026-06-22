from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict

class TextPayloadSchema(BaseModel):
    transcript: Optional[str] = None
    system_prompt_injected: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AudioPayloadSchema(BaseModel):
    audio_file_path: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkspacePayloadSchema(BaseModel):
    active_file: Optional[str] = None
    cursor_line: Optional[int] = None
    selected_code: Optional[str] = None
    terminal_stderr: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class MemoryEventBase(BaseModel):
    primary_modality: Literal["text", "voice", "workspace"]
    summary: Optional[str] = None

class MemoryEventCreate(MemoryEventBase):
    event_id: Optional[str] = None
    session_id: str
    text_payload: Optional[TextPayloadSchema] = None
    audio_payload: Optional[AudioPayloadSchema] = None
    workspace_payload: Optional[WorkspacePayloadSchema] = None

class MemoryEventResponse(MemoryEventBase):
    event_id: str
    session_id: str
    created_at: datetime
    text_payload: Optional[TextPayloadSchema] = None
    audio_payload: Optional[AudioPayloadSchema] = None
    workspace_payload: Optional[WorkspacePayloadSchema] = None

    model_config = ConfigDict(from_attributes=True)


class MemoryEpisodeSchema(BaseModel):
    id: str
    session_id: str
    project_id: Optional[str] = None
    memory_type: str
    created_at: datetime
    last_accessed_at: datetime
    recall_count: int
    title: str
    summary: str
    key_decisions: List[str]
    important_facts: List[str]
    open_tasks: List[str]
    importance_score: float

    model_config = ConfigDict(from_attributes=True)


class OpenTaskSchema(BaseModel):
    id: str
    episode_id: str
    description: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MemorySearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5


class MemorySearchResult(BaseModel):
    episode: MemoryEpisodeSchema
    relevance_score: float


class MemorySearchResponse(BaseModel):
    results: List[MemorySearchResult]


class EpisodicMemoryDiagnosticsResponse(BaseModel):
    episodes_created: int
    episodes_recalled: int
    memory_search_latency: float
    avg_episode_size: float
    open_tasks_created: int
    open_tasks_completed: int
