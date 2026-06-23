"""
MS-20 Tests — System Readiness Report
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.readiness import ReadinessReporter, ReadinessReport, _status_from_score


# ---------------------------------------------------------------------------
# Status threshold logic
# ---------------------------------------------------------------------------

def test_status_ready_when_score_100():
    assert _status_from_score(100) == "ready"


def test_status_degraded_when_score_80_to_99():
    assert _status_from_score(95) == "degraded"
    assert _status_from_score(80) == "degraded"


def test_status_not_ready_when_score_below_80():
    assert _status_from_score(79) == "not_ready"
    assert _status_from_score(0) == "not_ready"


# ---------------------------------------------------------------------------
# ReadinessReport dataclass
# ---------------------------------------------------------------------------

def test_readiness_report_fields():
    report = ReadinessReport(
        status="ready", score=100,
        checks_passed=10, checks_failed=0, warnings=0,
    )
    assert report.status == "ready"
    assert report.score == 100
    assert report.checks_passed == 10
    assert report.checks_failed == 0
    assert report.warnings == 0


# ---------------------------------------------------------------------------
# ReadinessReporter unit tests
# ---------------------------------------------------------------------------

def _make_passing_startup_checks(n=3):
    from app.core.startup_validator import StartupCheck
    return [StartupCheck(name=f"Check{i}", critical=True, passed=True, detail="OK")
            for i in range(n)]


def _make_health_response(status="healthy"):
    return {
        "status": status,
        "components": {
            "database": status,
            "memory": status,
        }
    }


@pytest.mark.anyio
async def test_reporter_all_passing_gives_score_100(db_session):
    reporter = ReadinessReporter()

    with patch("app.core.startup_validator.startup_results",
               _make_passing_startup_checks(3)), \
         patch("app.services.health.manager.health_manager.get_health",
               new=AsyncMock(return_value=_make_health_response("healthy"))), \
         patch("app.core.config_validator.config_validator.validate_all",
               return_value=[
                   MagicMock(passed=True),
                   MagicMock(passed=True),
               ]):
        report = await reporter.get_report(db_session)

    assert report.score == 100
    assert report.status == "ready"
    assert report.checks_failed == 0


@pytest.mark.anyio
async def test_reporter_critical_failure_reduces_score(db_session):
    from app.core.startup_validator import StartupCheck
    reporter = ReadinessReporter()

    startup = [
        StartupCheck("DB", critical=True, passed=True, detail="OK"),
        StartupCheck("Migrations", critical=True, passed=False, detail="Missing"),
    ]
    with patch("app.core.startup_validator.startup_results", startup), \
         patch("app.services.health.manager.health_manager.get_health",
               new=AsyncMock(return_value={"status": "healthy", "components": {}})), \
         patch("app.core.config_validator.config_validator.validate_all",
               return_value=[]):
        report = await reporter.get_report(db_session)

    assert report.checks_failed >= 1
    assert report.score < 100


@pytest.mark.anyio
async def test_reporter_degraded_component_adds_warning(db_session):
    reporter = ReadinessReporter()

    health = {
        "status": "degraded",
        "components": {"database": "healthy", "knowledge": "degraded"},
    }
    with patch("app.core.startup_validator.startup_results", _make_passing_startup_checks(2)), \
         patch("app.services.health.manager.health_manager.get_health",
               new=AsyncMock(return_value=health)), \
         patch("app.core.config_validator.config_validator.validate_all",
               return_value=[MagicMock(passed=True)]):
        report = await reporter.get_report(db_session)

    assert report.warnings >= 1


@pytest.mark.anyio
async def test_reporter_exception_in_health_does_not_crash(db_session):
    reporter = ReadinessReporter()

    with patch("app.core.startup_validator.startup_results", _make_passing_startup_checks(1)), \
         patch("app.services.health.manager.health_manager.get_health",
               new=AsyncMock(side_effect=RuntimeError("health boom"))), \
         patch("app.core.config_validator.config_validator.validate_all",
               return_value=[]):
        report = await reporter.get_report(db_session)

    assert report.checks_failed >= 1  # health failure counted



# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def test_readiness_endpoint_returns_200(client):
    response = client.get("/api/v1/system/readiness")
    assert response.status_code == 200


def test_readiness_endpoint_has_required_fields(client):
    response = client.get("/api/v1/system/readiness")
    data = response.json()
    assert "status" in data
    assert "score" in data
    assert "checks_passed" in data
    assert "checks_failed" in data
    assert "warnings" in data


def test_readiness_status_is_valid_value(client):
    response = client.get("/api/v1/system/readiness")
    data = response.json()
    assert data["status"] in ("ready", "degraded", "not_ready")


def test_readiness_score_in_range(client):
    response = client.get("/api/v1/system/readiness")
    data = response.json()
    assert 0 <= data["score"] <= 100
