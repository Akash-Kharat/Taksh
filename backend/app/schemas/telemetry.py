from typing import Optional, Literal
from pydantic import BaseModel

class TelemetryPayload(BaseModel):
    active_file: str
    cursor_line: int
    selection_empty: bool = True
    compiler_error: Optional[str] = None

class ClientTelemetryMessage(BaseModel):
    type: Literal["telemetry"]
    timestamp: str
    payload: TelemetryPayload

class ClientInterruptMessage(BaseModel):
    type: Literal["interrupt"]
    timestamp: str

class ServerTranscriptPayload(BaseModel):
    text: str
    is_final: bool
    role: Literal["assistant", "user", "system"]

class ServerTranscriptMessage(BaseModel):
    type: Literal["transcript"]
    payload: ServerTranscriptPayload

class ServerStatePayload(BaseModel):
    status: Literal["listening", "thinking", "speaking", "idle"]
    active_skill: Optional[str] = None

class ServerStateMessage(BaseModel):
    type: Literal["state"]
    payload: ServerStatePayload
