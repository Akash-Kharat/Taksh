import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logger import ws_logger
from app.services.orchestrator import Orchestrator
from app.schemas.telemetry import ClientTelemetryMessage, ClientInterruptMessage

router = APIRouter()

@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    ws_logger.info("Client WebSocket voice stream connection accepted")
    
    orchestrator = Orchestrator(websocket)
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                raw_pcm = message["bytes"]
                ws_logger.debug(f"Received binary voice frame of size: {len(raw_pcm)} bytes")
                await orchestrator.handle_client_audio(raw_pcm)
            elif "text" in message:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")
                    if msg_type == "telemetry":
                        telemetry = ClientTelemetryMessage.model_validate(payload)
                        ws_logger.info(f"Received client workspace telemetry for file: {telemetry.payload.active_file}")
                        await orchestrator.handle_client_telemetry(telemetry)
                    elif msg_type == "interrupt":
                        interrupt = ClientInterruptMessage.model_validate(payload)
                        ws_logger.warning("Received client voice activity interruption event")
                        await orchestrator.handle_client_interruption(interrupt)
                    else:
                        ws_logger.warning(f"Received unknown JSON WebSocket frame type: {msg_type}")
                except Exception as ex:
                    ws_logger.error(f"Failed parsing client text WebSocket payload: {ex}")
    except WebSocketDisconnect:
        ws_logger.info("Client WebSocket disconnected")
        await orchestrator.cleanup()
    except Exception as ex:
        ws_logger.error(f"Error in client WebSocket processing: {ex}")
        await orchestrator.cleanup()
