from fastapi.testclient import TestClient

def test_goals_api_crud(client: TestClient):
    # 1. Create Goal with default status "active"
    response = client.post("/api/v1/goals/", json={"description": "Implement goal validation"})
    assert response.status_code == 201
    data = response.json()
    assert "goal_id" in data
    assert data["status"] == "active"
    goal_id = data["goal_id"]
    
    # 2. Get Goal
    response = client.get(f"/api/v1/goals/{goal_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    
    # 3. Update Goal with valid status "completed"
    response = client.put(f"/api/v1/goals/{goal_id}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    
    # 4. Attempt Update with invalid status "done" -> Should fail validation (HTTP 422)
    response = client.put(f"/api/v1/goals/{goal_id}", json={"status": "done"})
    assert response.status_code == 422
    
    # 5. List Goals
    response = client.get("/api/v1/goals/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 6. Delete Goal
    response = client.delete(f"/api/v1/goals/{goal_id}")
    assert response.status_code == 204
    
    # 7. Verify Deleted
    response = client.get(f"/api/v1/goals/{goal_id}")
    assert response.status_code == 404
