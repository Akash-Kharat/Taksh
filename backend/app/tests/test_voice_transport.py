import struct
import time
import pytest
from fastapi.testclient import TestClient
from app.services.voice.session_manager import voice_session_manager
from app.services.websocket.manager import ws_manager
from app.core.config import settings

HEADER_FORMAT = "!IQIBBI2x"

def test_voice_websocket_handshake_and_heartbeat(client: TestClient):
    voice_session_manager.active_sessions.clear()

    # Establish websocket connection
    with client.websocket_connect("/api/v1/voice/connect?client_id=client-ws-test&session_id=session-ws-test") as websocket:
        # Check that it's registered in connection manager
        assert "client-ws-test" in ws_manager.get_active_clients()
        assert voice_session_manager.get_active_session_count() == 1

        # Send heartbeat (JSON text frame)
        websocket.send_text('{"type": "heartbeat"}')
        response = websocket.receive_json()
        assert response == {"type": "heartbeat_ack"}

    # After closing, registry should be cleaned up
    assert "client-ws-test" not in ws_manager.get_active_clients()
    assert voice_session_manager.get_active_session_count() == 0


def test_voice_binary_audio_frame_transport(client: TestClient):
    voice_session_manager.active_sessions.clear()

    with client.websocket_connect("/api/v1/voice/connect?client_id=client-binary&session_id=session-binary") as websocket:
        # Construct valid 24-byte header + 10 bytes payload
        # sequence=1, timestamp=now, sample_rate=16000, channels=1, encoding=1, payload_size=10
        ts_now = int(time.time() * 1000)
        header = struct.pack(HEADER_FORMAT, 1, ts_now, 16000, 1, 1, 10)
        payload = b"0123456789"
        
        # Send binary frame
        websocket.send_bytes(header + payload)

        # Allow simple processing time
        time.sleep(0.1)

        # Inspect the session stats
        active_sess = list(voice_session_manager.active_sessions.values())[0]
        assert active_sess["frames_received"] == 1
        assert active_sess["bytes_received"] == 10
        assert active_sess["average_latency_ms"] >= 0.0

        # Send second frame (sequence=2)
        header_2 = struct.pack(HEADER_FORMAT, 2, ts_now, 16000, 1, 1, 10)
        websocket.send_bytes(header_2 + payload)
        time.sleep(0.1)

        active_sess = list(voice_session_manager.active_sessions.values())[0]
        assert active_sess["frames_received"] == 2
        assert active_sess["bytes_received"] == 20


def test_voice_oversized_audio_frame_rejection(client: TestClient):
    voice_session_manager.active_sessions.clear()

    with client.websocket_connect("/api/v1/voice/connect?client_id=client-oversized&session_id=session-oversized") as websocket:
        # Construct frame that exceeds MAX_AUDIO_FRAME_BYTES (65536)
        oversized_payload = b"\x00" * 70000
        header = struct.pack(HEADER_FORMAT, 1, int(time.time() * 1000), 16000, 1, 1, 70000)
        
        # Send oversized frame
        try:
            websocket.send_bytes(header + oversized_payload)
            # The server should close the websocket connection
            websocket.receive()
        except Exception:
            pass  # Socket was closed by the server

    # Wait for the background thread to finish closing the session
    for _ in range(20):
        if voice_session_manager.get_active_session_count() == 0:
            break
        time.sleep(0.05)

    # Verify that the session is finalized
    assert voice_session_manager.get_active_session_count() == 0
