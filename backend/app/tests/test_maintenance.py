"""
Tests for MS-19 Background Maintenance Scheduler.
"""
import uuid
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from app.core.maintenance import (
    MaintenanceScheduler,
    cleanup_expired_approvals,
    cleanup_old_provider_health_records,
    cleanup_abandoned_runtime_sessions,
    persist_metrics_snapshot,
)
from app.models.database_models import (
    ToolExecution, ApprovalRequest, ProviderHealthRecord,
    ConversationRuntimeSession, MetricsSnapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_execution(db_session) -> str:
    """Create a ToolExecution row needed as FK for ApprovalRequest."""
    exec_id = str(uuid.uuid4())
    te = ToolExecution(
        execution_id=exec_id,
        tool_name="test_tool",
        tool_version="1.0.0",
        capability_level="read",
        category="test",
        parameters={},
        status="pending_approval",
    )
    db_session.add(te)
    db_session.flush()
    return exec_id


# ---------------------------------------------------------------------------
# Individual task tests
# ---------------------------------------------------------------------------

def test_cleanup_expired_approvals(db_session):
    exec_id = _make_tool_execution(db_session)
    old_cutoff = datetime.utcnow() - timedelta(hours=48)
    req = ApprovalRequest(
        execution_id=exec_id,
        tool_name="test_tool",
        capability_level="read",
        parameters={},
        reason="test",
        status="pending",
        expires_at=old_cutoff,
        created_at=old_cutoff,
    )
    db_session.add(req)
    db_session.commit()

    with patch("app.core.config.settings.APPROVAL_EXPIRATION_HOURS", 24):
        cleanup_expired_approvals(db_session)

    remaining = db_session.query(ApprovalRequest).filter(
        ApprovalRequest.execution_id == exec_id
    ).first()
    assert remaining is None


def test_cleanup_old_provider_health_records(db_session):
    old_date = datetime.utcnow() - timedelta(days=35)
    unique_name = f"mock_{uuid.uuid4().hex[:8]}"
    record = ProviderHealthRecord(
        provider_name=unique_name,
        provider_type="stt",
        healthy=True,
        latency_ms=10.0,
        created_at=old_date,
    )
    db_session.add(record)
    db_session.commit()

    with patch("app.core.config.settings.HEALTH_HISTORY_RETENTION_DAYS", 30):
        cleanup_old_provider_health_records(db_session)

    remaining = db_session.query(ProviderHealthRecord).filter(
        ProviderHealthRecord.provider_name == unique_name
    ).first()
    assert remaining is None


def test_cleanup_abandoned_runtime_sessions(db_session):
    old_start = datetime.utcnow() - timedelta(hours=3)
    session_id = f"abandoned-{uuid.uuid4().hex[:8]}"
    session = ConversationRuntimeSession(
        runtime_session_id=session_id,
        conversation_state="listening",
        conversation_session_state="active",
        current_turn_owner="none",
        started_at=old_start,
    )
    db_session.add(session)
    db_session.commit()

    cleanup_abandoned_runtime_sessions(db_session)

    updated = db_session.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.runtime_session_id == session_id
    ).first()
    assert updated.conversation_session_state == "closed"
    assert updated.ended_at is not None


def test_persist_metrics_snapshot(db_session):
    from app.core.metrics import TakshMetrics
    m = TakshMetrics()
    m._reset()
    m.inc_conversation()
    m.inc_turn()

    persist_metrics_snapshot(db_session)

    snap = db_session.query(MetricsSnapshot).order_by(MetricsSnapshot.captured_at.desc()).first()
    assert snap is not None
    assert snap.conversation_count >= 1


# ---------------------------------------------------------------------------
# Isolation: one failing task must not stop others
# ---------------------------------------------------------------------------

def test_task_isolation_in_run_cycle(db_session):
    scheduler = MaintenanceScheduler()
    call_log = []

    def good_task(db):
        call_log.append("good")

    def bad_task(db):
        call_log.append("bad_attempted")
        raise RuntimeError("intentional failure")

    def another_good(db):
        call_log.append("another_good")

    def patched_run(db, persist_metrics=False):
        scheduler._run_task("good_task",    good_task,    db)
        scheduler._run_task("bad_task",     bad_task,     db)
        scheduler._run_task("another_good", another_good, db)

    original = scheduler.run_cycle
    scheduler.run_cycle = patched_run
    try:
        scheduler.run_cycle(db_session)
    finally:
        scheduler.run_cycle = original

    assert "good" in call_log
    assert "bad_attempted" in call_log
    assert "another_good" in call_log  # must still run after failure


def test_run_task_logs_on_failure(db_session, caplog):
    scheduler = MaintenanceScheduler()
    import logging
    with caplog.at_level(logging.ERROR, logger="maintenance"):
        scheduler._run_task("failing_task", lambda db: (_ for _ in ()).throw(RuntimeError("boom")), db_session)
    assert any("boom" in m for m in caplog.messages)


def test_run_cycle_completes_without_error(db_session):
    """run_cycle with a clean DB should complete without exceptions."""
    scheduler = MaintenanceScheduler()
    scheduler.run_cycle(db_session, persist_metrics=True)  # no exception expected
