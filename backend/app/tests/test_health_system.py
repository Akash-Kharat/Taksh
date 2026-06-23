"""
Tests for MS-19 Health System.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.health.manager import (
    HealthManager, HealthStatus, ComponentHealth,
    _probe_database, _probe_memory, _probe_knowledge,
)


# ---------------------------------------------------------------------------
# Unit tests for individual probes
# ---------------------------------------------------------------------------

def test_database_probe_healthy(db_session):
    result = asyncio.get_event_loop().run_until_complete(_probe_database(db_session))
    assert result.status == HealthStatus.HEALTHY


def test_database_probe_unhealthy():
    bad_db = MagicMock()
    bad_db.execute.side_effect = Exception("connection refused")
    result = asyncio.get_event_loop().run_until_complete(_probe_database(bad_db))
    assert result.status == HealthStatus.UNHEALTHY
    assert "connection refused" in result.detail


def test_memory_probe_does_not_crash():
    result = asyncio.get_event_loop().run_until_complete(_probe_memory())
    assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


def test_knowledge_probe_degraded_on_failure():
    with patch("app.services.knowledge.vector_store.ChromaDBClient", side_effect=RuntimeError("chroma down")):
        result = asyncio.get_event_loop().run_until_complete(_probe_knowledge())
    assert result.status == HealthStatus.DEGRADED


# ---------------------------------------------------------------------------
# Timeout behaviour
# ---------------------------------------------------------------------------

def test_health_check_timeout():
    """A slow probe must return DEGRADED within timeout, not hang."""
    manager = HealthManager()

    async def run():
        async def slow_probe():
            await asyncio.sleep(999)
        with patch("app.core.config.settings.HEALTH_CHECK_TIMEOUT_SECONDS", 1):
            return await manager._run_with_timeout(slow_probe, "test_component")

    result = asyncio.get_event_loop().run_until_complete(run())
    assert result.status == HealthStatus.DEGRADED
    assert "Timed out" in result.detail


# ---------------------------------------------------------------------------
# Aggregation logic
# ---------------------------------------------------------------------------

def test_overall_status_unhealthy_when_db_down(db_session):
    async def run():
        with patch(
            "app.services.health.manager._probe_database",
            new=AsyncMock(return_value=ComponentHealth("database", HealthStatus.UNHEALTHY, "down")),
        ):
            manager = HealthManager()
            return await manager.get_health(db_session)

    result = asyncio.get_event_loop().run_until_complete(run())
    assert result["status"] == HealthStatus.UNHEALTHY.value


def test_overall_status_contains_all_components(db_session):
    async def run():
        manager = HealthManager()
        return await manager.get_health(db_session)

    result = asyncio.get_event_loop().run_until_complete(run())
    assert "database" in result["components"]


def test_get_health_returns_component_map(db_session):
    async def run():
        manager = HealthManager()
        return await manager.get_health(db_session)

    result = asyncio.get_event_loop().run_until_complete(run())
    assert "status" in result
    assert "components" in result
    assert isinstance(result["components"], dict)


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_has_components(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert isinstance(data["components"], dict)


def test_health_endpoint_valid_status_values(client):
    response = client.get("/api/v1/health")
    data = response.json()
    valid = {"healthy", "degraded", "unhealthy"}
    assert data["status"] in valid
    for v in data["components"].values():
        assert v in valid
