from fastapi.testclient import TestClient

def test_memory_api_crud(client: TestClient):
    # Create parent session
    response = client.post("/api/v1/sessions/", json={})
    assert response.status_code == 201
    session_id = response.json()["session_id"]
    
    # 1. Create MemoryEvent with sub-payloads
    event_payload = {
        "session_id": session_id,
        "primary_modality": "text",
        "summary": "Meeting notes about architecture",
        "text_payload": {
            "transcript": "Let's use SQLite and SQLAlchemy 2.0",
            "system_prompt_injected": "Default System Prompt"
        }
    }
    response = client.post("/api/v1/memory/", json=event_payload)
    assert response.status_code == 201
    data = response.json()
    assert "event_id" in data
    assert data["primary_modality"] == "text"
    assert data["text_payload"]["transcript"] == "Let's use SQLite and SQLAlchemy 2.0"
    event_id = data["event_id"]
    
    # 2. Get MemoryEvent
    response = client.get(f"/api/v1/memory/{event_id}")
    assert response.status_code == 200
    assert response.json()["event_id"] == event_id
    assert response.json()["text_payload"]["transcript"] == "Let's use SQLite and SQLAlchemy 2.0"
    
    # 3. List MemoryEvents
    response = client.get("/api/v1/memory/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 3b. List filtered by session
    response = client.get(f"/api/v1/memory/?session_id={session_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # 4. Delete MemoryEvent
    response = client.delete(f"/api/v1/memory/{event_id}")
    assert response.status_code == 204
    
    # 5. Verify physical deletion
    response = client.get(f"/api/v1/memory/{event_id}")
    assert response.status_code == 404

def test_longterm_memory_compatibility(client: TestClient):
    response = client.get("/api/v1/memory/longterm")
    assert response.status_code == 200
    assert response.json() == {"lessons": [], "projects": []}
