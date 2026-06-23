from fastapi import APIRouter
from app.core.logger import api_logger
from app.core.metrics import metrics
from app.schemas.system import MetricsResponse

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    """
    Returns the current in-memory metrics snapshot.
    Counters are cumulative since last process start (hydrated from DB on boot).
    """
    api_logger.info("Serving metrics snapshot")
    snap = metrics.snapshot()
    return MetricsResponse(
        conversation_count   = snap["conversation_count"],
        turn_count           = snap["turn_count"],
        provider_requests    = snap["provider_requests"],
        provider_failures    = snap["provider_failures"],
        tool_executions      = snap["tool_executions"],
        memory_recalls       = snap["memory_recalls"],
        knowledge_searches   = snap["knowledge_searches"],
        average_latency_ms   = snap["average_latency_ms"],
        active_sessions      = metrics.active_sessions,
    )
