import asyncio
import logging
import struct
import time
import uuid
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from app.core.config import settings
from app.services.websocket.manager import ws_manager
from app.services.voice.session_manager import voice_session_manager
from app.services.voice.ring_buffer import AudioRingBuffer

logger = logging.getLogger("voice")

router = APIRouter(prefix="/voice")

# Active ring buffers registry mapped by voice_session_id
active_buffers: Dict[str, AudioRingBuffer] = {}

# Header format: Big-endian, uint32, uint64, uint32, uint8, uint8, uint32, 2 bytes padding
HEADER_FORMAT = "!IQIBBI2x"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # Should be 24

@router.websocket("/connect")
async def voice_connect(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for bidirectional binary voice transport.
    Supports JSON heartbeats and reuses MS-04 ConnectionManager.
    """
    if not client_id:
        client_id = str(uuid.uuid4())

    # 1. Accept websocket and register in ConnectionManager (MS-04)
    await ws_manager.connect(websocket, client_id)

    # 2. Check and initialize voice session
    session_data = voice_session_manager.create_session(client_id, session_id)
    if not session_data:
        logger.warning(f"Voice session creation rejected for client {client_id} (resource limit reached)")
        # Remove from ConnectionManager
        ws_manager.disconnect(client_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Max sessions reached")
        return

    voice_session_id = session_data["voice_session_id"]
    
    # 3. Create ring buffer for this connection
    ring_buffer = AudioRingBuffer(voice_session_id)
    active_buffers[voice_session_id] = ring_buffer

    disconnect_reason = "normal"
    logger.info(f"Voice transport connection established. Session: {voice_session_id}, Client: {client_id}")

    try:
        while True:
            # Enforce 30 seconds idle timeout (Revision 4)
            # wait_for returns the websocket message or raises TimeoutError
            message = await asyncio.wait_for(
                websocket.receive(),
                timeout=settings.VOICE_IDLE_TIMEOUT_SECONDS
            )

            # Check message type
            if "text" in message:
                text_data = message["text"]
                try:
                    import json
                    payload = json.loads(text_data)
                    msg_type = payload.get("type")
                    if msg_type == "heartbeat":
                        voice_session_manager.update_activity(voice_session_id)
                        await websocket.send_json({"type": "heartbeat_ack"})
                    else:
                        logger.warning(f"Unknown control message type: {msg_type}")
                except Exception as ex:
                    logger.error(f"Failed parsing text control frame: {ex}")

            elif "bytes" in message:
                voice_session_manager.update_activity(voice_session_id)
                raw_bytes = message["bytes"]
                
                # Check message size bounds
                if len(raw_bytes) > settings.MAX_AUDIO_FRAME_BYTES:
                    logger.warning(f"Frame size {len(raw_bytes)} exceeds limit")
                    disconnect_reason = "frame_size_limit_exceeded"
                    await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG, reason="Frame too big")
                    break

                if len(raw_bytes) < HEADER_SIZE:
                    logger.warning(f"Received frame too small to contain header: {len(raw_bytes)} bytes")
                    continue

                # Parse header
                try:
                    header_bytes = raw_bytes[:HEADER_SIZE]
                    payload_bytes = raw_bytes[HEADER_SIZE:]

                    seq, ts_ms, rate, channels, encoding, payload_size = struct.unpack(
                        HEADER_FORMAT, header_bytes
                    )

                    # Validate payload size matches bytes read
                    if len(payload_bytes) != payload_size:
                        logger.warning(f"Payload size mismatch: expected {payload_size}, got {len(payload_bytes)}")

                    # Calculate latency
                    now_ms = int(time.time() * 1000)
                    latency = max(0.0, float(now_ms - ts_ms))

                    # Track stats & buffer
                    voice_session_manager.record_frame_received(voice_session_id, len(payload_bytes), latency)
                    ring_buffer.push(seq, ts_ms, payload_bytes)
                except Exception as ex:
                    logger.error(f"Error processing binary audio frame: {ex}")

    except asyncio.TimeoutError:
        logger.warning(f"Voice session {voice_session_id} timed out due to inactivity")
        disconnect_reason = "idle_timeout"
        try:
            await websocket.close(code=status.WS_1001_GOING_AWAY, reason="Idle timeout")
        except Exception:
            pass
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for voice session {voice_session_id}")
        disconnect_reason = "client_disconnect"
    except Exception as ex:
        logger.error(f"Error in voice WebSocket session {voice_session_id}: {ex}")
        disconnect_reason = f"error: {str(ex)}"
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        # 4. Clean up connection
        ws_manager.disconnect(client_id)
        active_buffers.pop(voice_session_id, None)
        voice_session_manager.close_session(voice_session_id, disconnect_reason)
        logger.info(f"Cleaned up voice transport session {voice_session_id} for client {client_id}")
