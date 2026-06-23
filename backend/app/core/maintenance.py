"""
Taksh Background Maintenance Scheduler — MS-19

Runs periodic housekeeping tasks.

Isolation guarantee:
  Each task executes inside its own try/except block.
  A single task failure logs the error and allows remaining tasks to proceed.
  The outer scheduler loop is also guarded — it never terminates due to a task error.

Schedule:
  - Every 5 minutes  : cleanup tasks
  - Every 15 minutes : metrics snapshot persistence
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import metrics

logger = logging.getLogger("maintenance")

CYCLE_INTERVAL_SECONDS   = 5 * 60   # 5 minutes
METRICS_PERSIST_INTERVAL = 3         # persist every 3rd cycle (~15 min)


# ---------------------------------------------------------------------------
# Individual maintenance tasks
# ---------------------------------------------------------------------------

def cleanup_expired_approvals(db) -> None:
    """Delete ApprovalRequest rows older than APPROVAL_EXPIRATION_HOURS."""
    from app.models.database_models import ApprovalRequest
    cutoff = datetime.utcnow() - timedelta(hours=settings.APPROVAL_EXPIRATION_HOURS)
    deleted = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted:
        logger.info(f"[maintenance] Deleted {deleted} expired approval request(s)")


def cleanup_old_provider_health_records(db) -> None:
    """Delete ProviderHealthRecord rows older than HEALTH_HISTORY_RETENTION_DAYS."""
    from app.models.database_models import ProviderHealthRecord
    cutoff = datetime.utcnow() - timedelta(days=settings.HEALTH_HISTORY_RETENTION_DAYS)
    deleted = (
        db.query(ProviderHealthRecord)
        .filter(ProviderHealthRecord.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted:
        logger.info(f"[maintenance] Pruned {deleted} old provider health record(s)")


def cleanup_abandoned_runtime_sessions(db) -> None:
    """
    Mark ConversationRuntimeSession rows that are still 'active' but have
    started more than 2× PROVIDER_REQUEST_TIMEOUT_SECONDS hours ago as 'closed'.
    """
    from app.models.database_models import ConversationRuntimeSession
    # Sessions active for more than 2 hours without an ended_at are considered abandoned
    cutoff = datetime.utcnow() - timedelta(hours=2)
    sessions = (
        db.query(ConversationRuntimeSession)
        .filter(
            ConversationRuntimeSession.conversation_session_state == "active",
            ConversationRuntimeSession.started_at < cutoff,
            ConversationRuntimeSession.ended_at.is_(None),
        )
        .all()
    )
    for session in sessions:
        session.conversation_session_state = "closed"
        session.ended_at = datetime.utcnow()
    if sessions:
        db.commit()
        logger.info(f"[maintenance] Closed {len(sessions)} abandoned runtime session(s)")


def cleanup_temporary_memory_caches(db) -> None:
    """
    Clear working-memory in-memory caches for sessions that no longer have
    an active ConversationRuntimeSession record in the DB.
    """
    try:
        from app.services.memory.manager import MemoryManager
        from app.models.database_models import ConversationRuntimeSession
        manager = MemoryManager()
        if not hasattr(manager, "_working_memory"):
            return
        active_session_ids = {
            row.runtime_session_id
            for row in db.query(ConversationRuntimeSession)
            .filter(ConversationRuntimeSession.conversation_session_state == "active")
            .all()
        }
        stale = [k for k in manager._working_memory if k not in active_session_ids]
        for k in stale:
            manager._working_memory.pop(k, None)
        if stale:
            logger.info(f"[maintenance] Cleared {len(stale)} stale working-memory cache(s)")
    except Exception as exc:
        logger.warning(f"[maintenance] memory cache cleanup skipped: {exc}")


def persist_metrics_snapshot(db) -> None:
    """Persist current TakshMetrics counters to the MetricsSnapshot table."""
    from app.models.database_models import MetricsSnapshot
    snap = metrics.snapshot()
    record = MetricsSnapshot(
        conversation_count   = snap["conversation_count"],
        turn_count           = snap["turn_count"],
        provider_requests    = snap["provider_requests"],
        provider_failures    = snap["provider_failures"],
        tool_executions      = snap["tool_executions"],
        memory_recalls       = snap["memory_recalls"],
        knowledge_searches   = snap["knowledge_searches"],
        average_latency_ms   = snap["average_latency_ms"],
    )
    db.add(record)
    db.commit()
    logger.info("[maintenance] Metrics snapshot persisted to database")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class MaintenanceScheduler:
    """
    Runs all maintenance tasks on a periodic cycle.
    Each task is fully isolated — failures do not affect other tasks or
    terminate the scheduler loop.
    """

    def _run_task(self, name: str, fn, *args, **kwargs) -> None:
        """Execute a single maintenance task with isolation."""
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.error(f"[maintenance] Task '{name}' failed: {exc}", exc_info=True)

    def run_cycle(self, db, persist_metrics: bool = False) -> None:
        """Run all maintenance tasks for one cycle."""
        self._run_task("cleanup_expired_approvals",          cleanup_expired_approvals,          db)
        self._run_task("cleanup_old_provider_health_records",cleanup_old_provider_health_records, db)
        self._run_task("cleanup_abandoned_runtime_sessions", cleanup_abandoned_runtime_sessions,  db)
        self._run_task("cleanup_temporary_memory_caches",    cleanup_temporary_memory_caches,     db)
        if persist_metrics:
            self._run_task("persist_metrics_snapshot",       persist_metrics_snapshot,            db)

    async def start_maintenance_loop(self) -> None:
        """Async background loop — runs forever, survives all task errors."""
        logger.info("[maintenance] Maintenance scheduler started")
        cycle_count = 0
        while True:
            await asyncio.sleep(CYCLE_INTERVAL_SECONDS)
            cycle_count += 1
            should_persist = (cycle_count % METRICS_PERSIST_INTERVAL == 0)
            try:
                db = SessionLocal()
                try:
                    self.run_cycle(db, persist_metrics=should_persist)
                finally:
                    db.close()
            except Exception as exc:
                # Outer guard — scheduler never dies
                logger.error(f"[maintenance] Unexpected scheduler error: {exc}", exc_info=True)


# Module-level singleton
maintenance_scheduler = MaintenanceScheduler()
