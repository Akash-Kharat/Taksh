from fastapi.testclient import TestClient

def test_projects_api_crud(client: TestClient):
    # 1. Create Project
    proj_payload = {
        "project_name": "Taksh Persist",
        "tech_stack": ["FastAPI", "SQLite"],
        "historical_adr_keys": ["adr-001"]
    }
    response = client.post("/api/v1/projects/", json=proj_payload)
    assert response.status_code == 201
    data = response.json()
    assert "project_id" in data
    assert data["project_name"] == "Taksh Persist"
    assert data["tech_stack"] == ["FastAPI", "SQLite"]
    project_id = data["project_id"]
    
    # 2. Get Project
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["project_name"] == "Taksh Persist"
    
    # 3. Update Project
    response = client.put(f"/api/v1/projects/{project_id}", json={"project_name": "Taksh Persist V2"})
    assert response.status_code == 200
    assert response.json()["project_name"] == "Taksh Persist V2"
    
    # 4. List Projects
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 5. Delete Project
    response = client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 204
    
    # 6. Verify Deleted
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 404
