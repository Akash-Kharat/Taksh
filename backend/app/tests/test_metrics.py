"""
Tests for MS-19 In-Memory Metrics Layer.
"""
import threading
import pytest
from app.core.metrics import TakshMetrics


@pytest.fixture(autouse=True)
def fresh_metrics():
    """Reset the singleton state before each test."""
    m = TakshMetrics()
    m._reset()
    yield m


def test_initial_counters_are_zero(fresh_metrics):
    assert fresh_metrics.conversation_count == 0
    assert fresh_metrics.turn_count == 0
    assert fresh_metrics.provider_requests == 0
    assert fresh_metrics.provider_failures == 0
    assert fresh_metrics.tool_executions == 0
    assert fresh_metrics.memory_recalls == 0
    assert fresh_metrics.knowledge_searches == 0
    assert fresh_metrics.active_sessions == 0


def test_increment_methods(fresh_metrics):
    fresh_metrics.inc_conversation()
    fresh_metrics.inc_turn()
    fresh_metrics.inc_provider_request()
    fresh_metrics.inc_provider_failure()
    fresh_metrics.inc_tool_execution()
    fresh_metrics.inc_memory_recall()
    fresh_metrics.inc_knowledge_search()
    fresh_metrics.inc_active_session()

    assert fresh_metrics.conversation_count == 1
    assert fresh_metrics.turn_count == 1
    assert fresh_metrics.provider_requests == 1
    assert fresh_metrics.provider_failures == 1
    assert fresh_metrics.tool_executions == 1
    assert fresh_metrics.memory_recalls == 1
    assert fresh_metrics.knowledge_searches == 1
    assert fresh_metrics.active_sessions == 1


def test_dec_active_session_floor(fresh_metrics):
    fresh_metrics.dec_active_session()  # Should not go below 0
    assert fresh_metrics.active_sessions == 0


def test_latency_rolling_average(fresh_metrics):
    fresh_metrics.record_latency(100.0)
    fresh_metrics.record_latency(200.0)
    assert fresh_metrics.average_latency_ms == 150.0


def test_snapshot_returns_all_keys(fresh_metrics):
    snap = fresh_metrics.snapshot()
    expected = {
        "conversation_count", "turn_count", "provider_requests",
        "provider_failures", "tool_executions", "memory_recalls",
        "knowledge_searches", "average_latency_ms",
    }
    assert expected <= set(snap.keys())


def test_hydrate_restores_state(fresh_metrics):
    fresh_metrics.hydrate({
        "conversation_count": 42,
        "turn_count": 100,
        "provider_requests": 50,
        "provider_failures": 3,
        "tool_executions": 20,
        "memory_recalls": 15,
        "knowledge_searches": 10,
        "average_latency_ms": 250.0,
    })
    assert fresh_metrics.conversation_count == 42
    assert fresh_metrics.turn_count == 100
    assert fresh_metrics.average_latency_ms == 250.0


def test_thread_safety(fresh_metrics):
    """Concurrent increments must not lose any counts."""
    threads = []
    n = 100
    for _ in range(n):
        t = threading.Thread(target=fresh_metrics.inc_conversation)
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert fresh_metrics.conversation_count == n


def test_singleton_identity():
    a = TakshMetrics()
    b = TakshMetrics()
    assert a is b


def test_metrics_endpoint(client, fresh_metrics):
    fresh_metrics.inc_conversation()
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "conversation_count" in data
    assert "average_latency_ms" in data
    assert "active_sessions" in data
