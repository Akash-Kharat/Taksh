import json
from typing import Optional
from app.schemas.websocket import PingMessage, PongMessage, MessageEvent, ErrorMessage

class MessageRouter:
    """Validates schemas and dispatches incoming WebSocket text messages."""

    async def route_message(self, raw_data: str) -> Optional[dict]:
        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            return ErrorMessage(
                code="INVALID_FRAME",
                message="Payload must be valid JSON"
            ).model_dump()

        if not isinstance(payload, dict):
            return ErrorMessage(
                code="INVALID_FRAME",
                message="Payload must be a JSON object"
            ).model_dump()

        msg_type = payload.get("type")
        if not msg_type:
            return ErrorMessage(
                code="INVALID_FRAME",
                message="Missing 'type' field in payload"
            ).model_dump()

        try:
            if msg_type == "ping":
                ping = PingMessage.model_validate(payload)
                return PongMessage(timestamp=ping.timestamp).model_dump()
                
            elif msg_type == "message":
                msg = MessageEvent.model_validate(payload)
                return MessageEvent(payload=f"Echo: {msg.payload}").model_dump()
                
            elif msg_type == "pong":
                # Heartbeat client response, ignore/no-op
                return None
                
            else:
                return ErrorMessage(
                    code="INVALID_FRAME",
                    message=f"Unknown message type: {msg_type}"
                ).model_dump()
                
        except Exception as e:
            return ErrorMessage(
                code="INVALID_FRAME",
                message=f"Validation failed: {str(e)}"
            ).model_dump()

message_router = MessageRouter()
