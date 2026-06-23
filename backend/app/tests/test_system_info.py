"""
Tests for MS-19 System Info and Config endpoints.
"""
import pytest


def test_system_config_returns_200(client):
    response = client.get("/api/v1/system/config")
    assert response.status_code == 200


def test_system_config_has_expected_fields(client):
    response = client.get("/api/v1/system/config")
    data = response.json()
    expected_keys = {
        "version", "environment", "providers",
        "api_v1_prefix", "host", "port", "log_level",
        "enable_provider_health_checks",
        "max_prompt_chars", "max_knowledge_chunks",
        "max_memory_items", "max_episodes",
        "health_check_timeout_seconds",
    }
    assert expected_keys <= set(data.keys())


def test_system_config_does_not_expose_api_key(client):
    response = client.get("/api/v1/system/config")
    text = response.text
    # The key name may appear (as a field label) but not the secret value
    # We verify GEMINI_API_KEY is not present as a top-level key
    data = response.json()
    assert "gemini_api_key" not in data
    assert "GEMINI_API_KEY" not in data


def test_system_config_providers_shape(client):
    response = client.get("/api/v1/system/config")
    providers = response.json()["providers"]
    assert "llm" in providers
    assert "stt" in providers
    assert "tts" in providers
    assert "realtime" in providers


def test_system_info_returns_200(client):
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200


def test_system_info_has_uptime(client):
    response = client.get("/api/v1/system/info")
    data = response.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_system_info_has_health_field(client):
    response = client.get("/api/v1/system/info")
    data = response.json()
    assert "health" in data
    assert data["health"] in {"healthy", "degraded", "unhealthy"}


def test_system_info_has_count_fields(client):
    response = client.get("/api/v1/system/info")
    data = response.json()
    count_fields = {
        "active_runtime_sessions", "active_voice_sessions",
        "active_provider_sessions", "memory_episodes",
        "open_tasks", "metrics_snapshots",
    }
    assert count_fields <= set(data.keys())
    for f in count_fields:
        assert isinstance(data[f], int)
        assert data[f] >= 0
