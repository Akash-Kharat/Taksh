import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.services.skills.registry import SkillsRegistry
from app.core.config import settings

def test_skills_registry_singleton():
    reg1 = SkillsRegistry()
    reg2 = SkillsRegistry()
    assert reg1 is reg2

def test_skills_api_endpoints(client: TestClient):
    # Test GET /api/v1/skills/info
    response = client.get("/api/v1/skills/info")
    assert response.status_code == 200
    info = response.json()
    assert "loaded_skills" in info
    assert "manifest_directory" in info
    assert info["registry_initialized"] is True
    assert info["loaded_skills"] >= 2  # Embedded Systems Architect, Fullstack Software Architect

    # Test GET /api/v1/skills
    response = client.get("/api/v1/skills/")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) >= 2
    assert any(s["name"] == "Embedded Systems Architect" for s in skills)

    # Test GET /api/v1/skills/{skill_name} with case-insensitive, hyphenated name
    response = client.get("/api/v1/skills/embedded-systems-architect")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Embedded Systems Architect"
    assert "Low-overhead" in data["prompt_overlay"]["role"] or "low-overhead" in data["prompt_overlay"]["role"].lower()

    # Test GET /api/v1/skills/{skill_name} with spaces
    response = client.get("/api/v1/skills/Embedded Systems Architect")
    assert response.status_code == 200
    assert response.json()["name"] == "Embedded Systems Architect"

    # Test GET /api/v1/skills/{skill_name} returning 404
    response = client.get("/api/v1/skills/non-existent-skill")
    assert response.status_code == 404

def test_skills_registry_empty_warning(monkeypatch):
    # Override settings.SKILLS_MANIFEST_DIR to an empty folder
    empty_dir = Path("./app/services/skills/empty_manifests")
    empty_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "SKILLS_MANIFEST_DIR", empty_dir)

    registry = SkillsRegistry()
    # Reset singleton initialization
    registry._initialized = False
    registry.skills.clear()
    
    registry.load_manifests()
    
    assert len(registry.skills) == 0
    assert registry.get_diagnostics()["loaded_skills"] == 0
    
    # Restore actual manifests state
    registry._initialized = False
    actual_dir = Path("./app/services/skills/manifests")
    monkeypatch.setattr(settings, "SKILLS_MANIFEST_DIR", actual_dir)
    registry.load_manifests()
    
    # Clean up empty directory
    try:
        empty_dir.rmdir()
    except Exception:
        pass
