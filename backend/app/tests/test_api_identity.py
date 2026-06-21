import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.services.memory.identity import CoreIdentityManager
from app.core.config import settings

def test_identity_manager_singleton():
    mgr1 = CoreIdentityManager()
    mgr2 = CoreIdentityManager()
    assert mgr1 is mgr2

def test_identity_api_endpoints(client: TestClient):
    # Test GET /api/v1/identity
    response = client.get("/api/v1/identity/")
    assert response.status_code == 200
    data = response.json()
    assert "identity" in data
    assert "Taksh" in data["identity"] and "Philosophical" in data["identity"]

    # Test GET /api/v1/identity/info
    response = client.get("/api/v1/identity/info")
    assert response.status_code == 200
    info = response.json()
    assert "loaded" in info
    assert "source" in info
    assert "cache_initialized" in info
    assert "identity_hash" in info
    assert len(info["identity_hash"]) == 64  # SHA-256 hash length

def test_identity_manager_fallback(monkeypatch):
    # Override settings.IDENTITY_PATH to a non-existent file
    monkeypatch.setattr(settings, "IDENTITY_PATH", Path("non_existent_identity.md"))
    
    # We create a clean instance or reset the initialization state of the singleton
    mgr = CoreIdentityManager()
    
    # Reset internal flags for test isolation
    mgr._initialized = False
    mgr._fallback_active = False
    
    mgr.initialize()
    
    # Verify fallback behavior
    assert mgr._fallback_active is True
    assert "Fallback Identity Activated" in mgr.get_identity() or "Socratic" in mgr.get_identity()
    assert mgr.get_metadata()["loaded"] is False
    
    # Restore the actual singleton state so subsequent tests don't break
    mgr._initialized = False
    mgr._fallback_active = False
    settings_actual_path = Path("../docs/Vision/taksh_identity.md")
    monkeypatch.setattr(settings, "IDENTITY_PATH", settings_actual_path)
    mgr.initialize()
