import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, SessionLocal
from app.models.database_models import ConversationRuntimeSession
from app.services.runtime.state_machine import active_state_machines, RealtimeStateMachine
from app.services.runtime.output_queue import active_output_queues


@pytest.mark.anyio
async def test_runtime_endpoints_flow(client: TestClient):
    # Temporarily remove dependency override to avoid transaction lock conflicts in SQLite
    override = app.dependency_overrides.pop(get_db, None)
    
    # Ensure active caches are clean initially
    active_state_machines.clear()
    active_output_queues.clear()

    db = SessionLocal()
    try:
        # 1. Start session
        response = client.post("/api/v1/runtime/start", json={"voice_session_id": "voice-123"})
        assert response.status_code == 201
        data = response.json()
        assert "runtime_session_id" in data
        assert data["conversation_state"] == "listening"
        assert data["current_turn_owner"] == "user"
        
        runtime_session_id = data["runtime_session_id"]
        assert runtime_session_id in active_state_machines
        assert runtime_session_id in active_output_queues

        # 2. Get session diagnostics
        response = client.get(f"/api/v1/runtime/session/{runtime_session_id}")
        assert response.status_code == 200
        diag = response.json()
        assert diag["current_state"] == "listening"
        assert diag["turn_owner"] == "user"
        assert diag["interruption_count"] == 0

        # 3. Get runtime info (aggregates)
        response = client.get("/api/v1/runtime/info")
        assert response.status_code == 200
        info = response.json()
        assert info["active_sessions_count"] == 1
        assert info["total_sessions_count"] >= 1

        # 4. Transition to speaking so we can test interruption
        sm = active_state_machines[runtime_session_id]
        await sm.transition_to("thinking", db)
        await sm.transition_to("speaking", db)

        # 5. Interrupt session
        response = client.post(
            "/api/v1/runtime/interrupt",
            json={"runtime_session_id": runtime_session_id}
        )
        assert response.status_code == 200
        intr = response.json()
        assert intr["conversation_state"] == "interrupted"
        assert intr["current_turn_owner"] == "user"

        # Verify session diagnostics updated
        response = client.get(f"/api/v1/runtime/session/{runtime_session_id}")
        assert response.status_code == 200
        diag = response.json()
        assert diag["current_state"] == "interrupted"
        assert diag["interruption_count"] == 1

        # Transition from interrupted back to listening (via state machine)
        await sm.transition_to("listening", db)

        # 6. Close session
        response = client.post(
            "/api/v1/runtime/close",
            json={"runtime_session_id": runtime_session_id}
        )
        assert response.status_code == 200
        close_data = response.json()
        assert close_data["conversation_state"] == "closed"
        assert close_data["ended_at"] is not None
        
        # Assert eviction from memory caches
        assert runtime_session_id not in active_state_machines
        assert runtime_session_id not in active_output_queues
    finally:
        db.close()
        if override:
            app.dependency_overrides[get_db] = override


@pytest.mark.anyio
async def test_runtime_api_error_handling(client: TestClient):
    override = app.dependency_overrides.pop(get_db, None)
    try:
        # 1. Non-existent session diagnostics
        response = client.get("/api/v1/runtime/session/non-existent-uuid")
        assert response.status_code == 404
        
        # 2. Non-existent session interruption
        response = client.post("/api/v1/runtime/interrupt", json={"runtime_session_id": "non-existent-uuid"})
        assert response.status_code == 404

        # 3. Non-existent session close
        response = client.post("/api/v1/runtime/close", json={"runtime_session_id": "non-existent-uuid"})
        assert response.status_code == 404
    finally:
        if override:
            app.dependency_overrides[get_db] = override
