import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
from unittest.mock import patch

from app.models.database_models import (
    ConversationProfile,
    ProjectMemory,
    PreferenceMemory,
    ProjectSnapshot,
    ConversationRuntimeSession,
    ConversationTurn,
    ConversationMetrics
)


def test_conversation_info_api(client: TestClient, db_session: Session):
    # 1. Populate DB with diagnostic stats
    p = ProjectMemory(
        project_name="Taksh CLI",
        status="active",
        summary="Command line tool"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    prof = ConversationProfile(
        interaction_count=3,
        active_project_id=p.project_memory_id
    )
    db_session.add(prof)

    pref1 = PreferenceMemory(category="general", value="Always use tabs", confidence_score=0.9)
    pref2 = PreferenceMemory(category="general", value="Always print summary", confidence_score=0.8)
    db_session.add_all([pref1, pref2])

    snap = ProjectSnapshot(
        project_name="Taksh CLI",
        milestone="v0.1",
        summary="Initial draft",
        decisions=[],
        open_questions=[],
        next_steps=[]
    )
    db_session.add(snap)
    db_session.commit()

    # 2. Query endpoint
    response = client.get("/api/v1/conversation/info")
    assert response.status_code == 200
    data = response.json()

    assert data["profiles"] == 1
    assert data["preferences"] == 2
    assert data["projects"] == 1
    assert data["snapshots"] == 1
    assert data["active_project"] == "Taksh CLI"
    assert "active_sessions" in data
    assert "total_turns" in data
    assert "avg_turn_latency_ms" in data


def test_conversation_pipeline_start_stop_apis(client: TestClient, db_session: Session):
    # Start session
    response = client.post("/api/v1/conversation/start", json={"voice_session_id": "test-ws-id"})
    assert response.status_code == 201
    start_data = response.json()
    assert "runtime_session_id" in start_data
    assert start_data["conversation_session_state"] == "active"
    
    runtime_session_id = start_data["runtime_session_id"]

    # Send message
    with patch('app.services.conversation.coordinator.conversation_coordinator.process_message') as mock_process:
        from app.models.database_models import ConversationTurn
        mock_turn = ConversationTurn(
            turn_id="t1",
            runtime_session_id=runtime_session_id,
            user_text="hello",
            assistant_text="world",
            latency_ms=100.0
        )
        mock_process.return_value = mock_turn

        response = client.post("/api/v1/conversation/message", json={
            "runtime_session_id": runtime_session_id,
            "message": "hello"
        })
        assert response.status_code == 200
        msg_data = response.json()
        assert msg_data["assistant_text"] == "world"
        assert msg_data["turn_id"] == "t1"

    # Stop session
    response = client.post("/api/v1/conversation/stop", json={"runtime_session_id": runtime_session_id})
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


def test_conversation_session_detail_api(client: TestClient, db_session: Session):
    # Seed session
    sess = ConversationRuntimeSession(
        runtime_session_id="session-detail-id",
        voice_session_id="voice-detail-id",
        conversation_state="listening",
        conversation_session_state="active"
    )
    db_session.add(sess)

    # Seed turns
    t1 = ConversationTurn(
        runtime_session_id="session-detail-id",
        user_text="hi",
        assistant_text="hello",
        latency_ms=10.0,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(t1)

    # Seed metrics
    metrics = ConversationMetrics(
        runtime_session_id="session-detail-id",
        total_turns=1,
        average_turn_latency_ms=10.0
    )
    db_session.add(metrics)
    db_session.commit()

    # Query details
    response = client.get("/api/v1/conversation/session/session-detail-id")
    assert response.status_code == 200
    data = response.json()

    assert "turns" in data
    assert len(data["turns"]) == 1
    assert data["turns"][0]["user_text"] == "hi"
    assert data["turns"][0]["assistant_text"] == "hello"
    assert data["metrics"]["total_turns"] == 1
