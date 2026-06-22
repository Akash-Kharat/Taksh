import pytest
from fastapi.testclient import TestClient
from app.models.database_models import ProviderSession
from datetime import datetime

def test_get_providers_info_endpoint(client: TestClient, db_session):
    # Seed a provider session record
    session_rec = ProviderSession(
        provider_session_id="test-info-session",
        provider_name="mock",
        provider_state="active",
        connected_at=datetime.utcnow()
    )
    db_session.add(session_rec)
    db_session.commit()

    response = client.get("/api/v1/providers/info")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, dict)
    assert "active_provider" in data
    assert "provider_state" in data
    assert "healthy" in data
    assert "fallback_active" in data
    assert "active_sessions" in data
    assert "reconnect_count" in data
    assert "failure_count" in data
    
    assert data["fallback_active"] is False
    assert data["active_sessions"] >= 1
