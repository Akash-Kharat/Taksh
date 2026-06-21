from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DbSession

def test_sessions_api_crud(client: TestClient):
    # 1. Create Session
    response = client.post("/api/v1/sessions/", json={})
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["closed_at"] is None
    session_id = data["session_id"]
    
    # 2. Get Session
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["session_id"] == session_id
    
    # 3. List Sessions
    response = client.get("/api/v1/sessions/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 4. Update Session
    response = client.put(f"/api/v1/sessions/{session_id}", json={"closed_at": "2026-06-21T12:00:00"})
    assert response.status_code == 200
    assert response.json()["closed_at"] is not None
    
    # 5. Delete Session
    response = client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204
    
    # 6. Verify Deleted
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 404
