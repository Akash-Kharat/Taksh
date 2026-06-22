import time
import pytest
from fastapi.testclient import TestClient
from app.services.voice.session_manager import voice_session_manager
from app.core.config import settings

def test_voice_diagnostics_endpoint(client: TestClient):
    # 1. Clear sessions and DB is populated via other tests or starts fresh
    voice_session_manager.active_sessions.clear()

    # 2. Get initial diagnostics
    response = client.get("/api/v1/voice/info")
    assert response.status_code == 200
    data = response.json()
    assert "active_sessions" in data
    assert "frames_received" in data
    assert "average_latency_ms" in data

    # 3. Create active session to verify counts update
    sess_data = voice_session_manager.create_session("client-api-test", "sess-api-test")
    voice_session_id = sess_data["voice_session_id"]
    voice_session_manager.record_frame_received(voice_session_id, size=200, latency_ms=15.0)

    # 4. Fetch endpoint again
    response = client.get("/api/v1/voice/info")
    assert response.status_code == 200
    data = response.json()
    assert data["active_sessions"] == 1
    assert data["frames_received"] >= 1
    assert data["average_latency_ms"] >= 15.0

    # Cleanup
    voice_session_manager.close_session(voice_session_id)


def test_voice_idle_timeout(client: TestClient, monkeypatch):
    # Patch the timeout config to be super fast (0.2s) instead of 30s
    monkeypatch.setattr(settings, "VOICE_IDLE_TIMEOUT_SECONDS", 0.2)
    voice_session_manager.active_sessions.clear()

    # Connect to websocket
    with client.websocket_connect("/api/v1/voice/connect?client_id=client-idle-test") as websocket:
        # Verify it's active
        assert voice_session_manager.get_active_session_count() == 1

        # Sleep for longer than the timeout window (0.4s)
        time.sleep(0.4)

        # Check if the connection has been terminated by the server due to timeout
        try:
            # Attempt to receive (or receive_json)
            # This should either raise exception or return a disconnect code
            websocket.receive()
        except Exception:
            pass  # Expected since the socket was closed

    # Verify that the session is finalized
    assert voice_session_manager.get_active_session_count() == 0
