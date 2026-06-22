import pytest
from fastapi.testclient import TestClient
from app.models.database_models import ProviderSession

def test_get_provider_sessions_endpoint(client: TestClient, db_session):
    # Seed mock provider session records
    session_rec = ProviderSession(
        provider_session_id="test-session-uuid-123",
        provider_name="mock",
        provider_state="closed",
        messages_sent=4,
        messages_received=4,
        audio_frames_sent=100,
        audio_frames_received=100,
        interruptions=1,
        average_response_latency_ms=25.0
    )
    db_session.add(session_rec)
    db_session.commit()

    # Query API
    response = client.get("/api/v1/providers/sessions")
    assert response.status_code == 200
    
    data = response.json()
    assert "sessions" in data
    assert "total_sessions" in data
    assert "average_latency_ms" in data
    assert "total_interruptions" in data
    
    assert data["total_sessions"] >= 1
    assert data["average_latency_ms"] == 25.0
    assert data["total_interruptions"] >= 1
    assert data["total_audio_frames_sent"] == 100
    assert data["total_audio_frames_received"] == 100
