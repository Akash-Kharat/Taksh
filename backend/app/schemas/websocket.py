from typing import Literal
from pydantic import BaseModel

class BaseMessage(BaseModel):
    type: str

class PingMessage(BaseMessage):
    type: Literal["ping"] = "ping"
    timestamp: float

class PongMessage(BaseMessage):
    type: Literal["pong"] = "pong"
    timestamp: float

class MessageEvent(BaseMessage):
    type: Literal["message"] = "message"
    payload: str

class ConnectedMessage(BaseMessage):
    type: Literal["connected"] = "connected"
    client_id: str

class ErrorMessage(BaseMessage):
    type: Literal["error"] = "error"
    code: str
    message: str
