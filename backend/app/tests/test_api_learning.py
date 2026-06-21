from fastapi.testclient import TestClient

def test_learning_api_crud(client: TestClient):
    # 1. Create Learning History entry
    concept_payload = {
        "concept_name": "SQLAlchemy Declarative",
        "mastery_score": 75
    }
    response = client.post("/api/v1/learning-history/", json=concept_payload)
    assert response.status_code == 201
    data = response.json()
    assert "concept_id" in data
    assert data["concept_name"] == "SQLAlchemy Declarative"
    assert data["mastery_score"] == 75
    concept_id = data["concept_id"]
    
    # 2. Get Learning History
    response = client.get(f"/api/v1/learning-history/{concept_id}")
    assert response.status_code == 200
    assert response.json()["concept_name"] == "SQLAlchemy Declarative"
    
    # 3. Update Learning History with valid score
    response = client.put(f"/api/v1/learning-history/{concept_id}", json={"mastery_score": 90})
    assert response.status_code == 200
    assert response.json()["mastery_score"] == 90
    
    # 4. Attempt Update with invalid score (ge 100, e.g. 105) -> Should fail validation (HTTP 422)
    response = client.put(f"/api/v1/learning-history/{concept_id}", json={"mastery_score": 105})
    assert response.status_code == 422
    
    # 5. Attempt Update with negative score -> Should fail validation (HTTP 422)
    response = client.put(f"/api/v1/learning-history/{concept_id}", json={"mastery_score": -10})
    assert response.status_code == 422
    
    # 6. List entries
    response = client.get("/api/v1/learning-history/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 7. Delete entry
    response = client.delete(f"/api/v1/learning-history/{concept_id}")
    assert response.status_code == 204
    
    # 8. Verify Deleted
    response = client.get(f"/api/v1/learning-history/{concept_id}")
    assert response.status_code == 404
