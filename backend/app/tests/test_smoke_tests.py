"""
MS-20 Tests — Smoke Test Framework
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.smoke_tests import SmokeTestRunner, SmokeTestResult, SmokeTestReport


# ---------------------------------------------------------------------------
# Unit: _run() helper
# ---------------------------------------------------------------------------

def test_run_returns_passed_on_success(db_session):
    runner = SmokeTestRunner()
    result = runner._run("TestCat", "TestName", lambda: "OK detail")
    assert result.passed is True
    assert result.category == "TestCat"
    assert result.name == "TestName"
    assert result.detail == "OK detail"
    assert result.duration_ms >= 0


def test_run_returns_failed_on_exception(db_session):
    runner = SmokeTestRunner()
    result = runner._run("TestCat", "FailTest", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert result.passed is False
    assert "boom" in result.detail


def test_one_failure_does_not_stop_others(db_session):
    """Verify that a failing test in the middle does not prevent later tests."""
    runner = SmokeTestRunner()
    calls = []

    def good1(): calls.append("good1"); return "OK"
    def bad():   calls.append("bad"); raise RuntimeError("intentional")
    def good2(): calls.append("good2"); return "OK"

    results = [
        runner._run("X", "good1", good1),
        runner._run("X", "bad", bad),
        runner._run("X", "good2", good2),
    ]

    assert "good1" in calls
    assert "bad" in calls
    assert "good2" in calls
    assert results[0].passed is True
    assert results[1].passed is False
    assert results[2].passed is True


# ---------------------------------------------------------------------------
# Unit: report structure
# ---------------------------------------------------------------------------

def test_run_all_returns_smoke_test_report(db_session):
    runner = SmokeTestRunner()
    report = runner.run_all(db_session)
    assert isinstance(report, SmokeTestReport)
    assert isinstance(report.results, list)


def test_run_all_report_counts_are_consistent(db_session):
    runner = SmokeTestRunner()
    report = runner.run_all(db_session)
    assert report.total == len(report.results)
    assert report.passed + report.failed == report.total


def test_run_all_has_expected_categories(db_session):
    runner = SmokeTestRunner()
    report = runner.run_all(db_session)
    categories = {r.category for r in report.results}
    assert "Runtime" in categories
    assert "Memory" in categories
    assert "Knowledge" in categories
    assert "Provider" in categories
    assert "Conversation" in categories


def test_runtime_tests_run(db_session):
    runner = SmokeTestRunner()
    results = runner._run_runtime_tests(db_session)
    names = [r.name for r in results]
    assert "Create session" in names
    assert "Close session" in names


def test_memory_tests_run(db_session):
    runner = SmokeTestRunner()
    results = runner._run_memory_tests(db_session)
    names = [r.name for r in results]
    assert "Create episode" in names
    assert "Retrieve episode" in names


def test_knowledge_tests_run(db_session):
    runner = SmokeTestRunner()
    results = runner._run_knowledge_tests(db_session)
    names = [r.name for r in results]
    assert "Ingest chunk" in names
    assert "Search chunk" in names


def test_provider_tests_run(db_session):
    runner = SmokeTestRunner()
    results = runner._run_provider_tests(db_session)
    names = [r.name for r in results]
    assert "Mock generate" in names
    assert "Mock STT" in names
    assert "Mock TTS" in names


def test_conversation_tests_run(db_session):
    runner = SmokeTestRunner()
    results = runner._run_conversation_tests(db_session)
    names = [r.name for r in results]
    assert "Start" in names
    assert "Message" in names
    assert "Stop" in names


def test_smoke_test_result_duration_nonnegative(db_session):
    runner = SmokeTestRunner()
    report = runner.run_all(db_session)
    for r in report.results:
        assert r.duration_ms >= 0


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def test_smoke_test_endpoint_returns_200(client):
    response = client.post("/api/v1/system/smoke-test")
    assert response.status_code == 200


def test_smoke_test_endpoint_has_required_fields(client):
    response = client.post("/api/v1/system/smoke-test")
    data = response.json()
    assert "total" in data
    assert "passed" in data
    assert "failed" in data
    assert "results" in data
    assert "total_duration_ms" in data


def test_smoke_test_endpoint_results_have_schema(client):
    response = client.post("/api/v1/system/smoke-test")
    for r in response.json()["results"]:
        assert "category" in r
        assert "name" in r
        assert "passed" in r
        assert "duration_ms" in r
