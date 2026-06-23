"""
Tests for MS-19 Startup Report endpoint (GET /api/v1/system/startup-report).
"""
import pytest
from app.core.startup_validator import StartupCheck
import app.core.startup_validator as sv_module


FAKE_RESULTS = [
    StartupCheck(name="Database",           critical=True,  passed=True,  detail="Reachable"),
    StartupCheck(name="ChromaDB",           critical=True,  passed=True,  detail="Initialised"),
    StartupCheck(name="Workspace Directory",critical=True,  passed=True,  detail="/path/to/.taksh"),
    StartupCheck(name="Skills Directory",   critical=False, passed=False, detail="Not found"),
    StartupCheck(name="Default LLM Provider", critical=False, passed=True, detail="mock"),
]


def test_startup_report_returns_200(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    assert response.status_code == 200


def test_startup_report_has_checks_list(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    data = response.json()
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_startup_report_check_schema(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    checks = response.json()["checks"]
    assert len(checks) > 0
    for check in checks:
        assert "name" in check
        assert "critical" in check
        assert "passed" in check
        assert "detail" in check


def test_startup_report_total_counts(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    data = response.json()
    assert data["total"] == 5
    assert data["passed"] == 4
    assert data["failed"] == 1


def test_startup_report_identifies_failed_check(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    checks = response.json()["checks"]
    failed = [c for c in checks if not c["passed"]]
    assert len(failed) == 1
    assert failed[0]["name"] == "Skills Directory"
    assert failed[0]["critical"] is False


def test_startup_report_critical_flags_correct(client):
    sv_module.startup_results = list(FAKE_RESULTS)
    response = client.get("/api/v1/system/startup-report")
    checks = {c["name"]: c for c in response.json()["checks"]}
    assert checks["Database"]["critical"] is True
    assert checks["Skills Directory"]["critical"] is False


def test_startup_report_empty_when_no_results(client):
    sv_module.startup_results = []
    response = client.get("/api/v1/system/startup-report")
    data = response.json()
    assert data["total"] == 0
    assert data["checks"] == []
