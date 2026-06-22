import pytest
from fastapi.testclient import TestClient
from app.models.database_models import ProviderHealthRecord
from datetime import datetime

def test_get_providers_info_endpoint(client: TestClient, db_session):
    # Seed the DB with some health records to verify aggregation
    success_record = ProviderHealthRecord(
        provider_name="mock",
        provider_type="stt",
        healthy=True,
        latency_ms=10.0,
        created_at=datetime.utcnow()
    )
    db_session.add(success_record)
    db_session.commit()

    response = client.get("/api/v1/providers/info")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # at least mock STT, mock TTS, mock realtime

    # Check mock stt structure
    stt_info = next((item for item in data if item["provider"] == "mock" and item["provider_type"] == "stt"), None)
    assert stt_info is not None
    assert "provider" in stt_info
    assert "provider_type" in stt_info
    assert "state" in stt_info
    assert "healthy" in stt_info
    assert "supports_streaming" in stt_info
    assert "last_successful_operation" in stt_info
    assert "average_latency_ms" in stt_info

    # Assert types and values
    assert stt_info["provider"] == "mock"
    assert stt_info["provider_type"] == "stt"
    assert stt_info["state"] == "disconnected" or stt_info["state"] == "connected"
    assert stt_info["healthy"] is True
    assert stt_info["supports_streaming"] is False
    assert stt_info["average_latency_ms"] == 10.0
    assert stt_info["last_successful_operation"] is not None
