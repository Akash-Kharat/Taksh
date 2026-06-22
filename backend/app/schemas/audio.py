from pydantic import BaseModel, Field
from typing import Optional

class AudioFrameMetadata(BaseModel):
    sequence_number: int = Field(..., description="Monotonically increasing frame index")
    timestamp_ms: int = Field(..., description="Timestamp in milliseconds")
    sample_rate: int = Field(16000, description="Sample rate in Hz")
    channels: int = Field(1, description="Number of channels")
    encoding: str = Field("PCM16", description="Audio encoding standard")
    payload_size: int = Field(..., description="Size of raw audio payload in bytes")


class VoiceDiagnostics(BaseModel):
    active_sessions: int
    frames_received: int
    frames_sent: int
    dropped_frames: int
    missing_frames: int
    out_of_order_frames: int
    average_latency_ms: float
