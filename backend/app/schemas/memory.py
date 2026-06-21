from datetime import datetime
from typing import Optional, Literal
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
