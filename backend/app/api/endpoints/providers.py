from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import func

from app.core.database import get_db
from app.core.logger import api_logger
from app.core.config import settings
from app.services.providers.manager import provider_manager
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import ProviderState
from app.models.database_models import ProviderSession
from app.schemas.providers import ProviderInfoResponse, ProviderSessionsResponse, ProviderSessionSchema

router = APIRouter()

@router.get("/providers/info", response_model=ProviderInfoResponse)
async def get_providers_info(db: DbSession = Depends(get_db)):
    api_logger.info("Serving provider diagnostics check")

    # Determine active provider
    active_provider = provider_manager._get_provider_name(None, settings.DEFAULT_REALTIME_PROVIDER)

    # Determine state and health
    try:
        provider_instance = provider_factory.get_realtime_provider(active_provider)
        state_enum = provider_instance.get_state()
        state = getattr(provider_instance, "provider_state", "closed")
        healthy = (state_enum == ProviderState.CONNECTED or state == "active")
    except Exception:
        state = "failed"
        healthy = False

    # Query active session counts
    active_sessions = db.query(ProviderSession).filter(
        ProviderSession.disconnected_at == None
    ).count()

    return ProviderInfoResponse(
        active_provider=active_provider,
        provider_state=state,
        healthy=healthy,
        fallback_active=provider_manager.fallback_active,
        active_sessions=active_sessions,
        reconnect_count=provider_manager.reconnect_count,
        failure_count=provider_manager.failure_count
    )


@router.get("/providers/sessions", response_model=ProviderSessionsResponse)
async def get_provider_sessions(db: DbSession = Depends(get_db)):
    api_logger.info("Serving provider sessions history")

    # Fetch session history
    sessions_rec = db.query(ProviderSession).order_by(ProviderSession.connected_at.desc()).all()

    # Calculate aggregates
    total_sessions = len(sessions_rec)
    
    avg_latency = db.query(func.avg(ProviderSession.average_response_latency_ms)).scalar()
    average_latency_ms = float(avg_latency) if avg_latency is not None else 0.0

    total_interruptions = db.query(func.sum(ProviderSession.interruptions)).scalar()
    total_interruptions = int(total_interruptions) if total_interruptions is not None else 0

    total_audio_frames_sent = db.query(func.sum(ProviderSession.audio_frames_sent)).scalar()
    total_audio_frames_sent = int(total_audio_frames_sent) if total_audio_frames_sent is not None else 0

    total_audio_frames_received = db.query(func.sum(ProviderSession.audio_frames_received)).scalar()
    total_audio_frames_received = int(total_audio_frames_received) if total_audio_frames_received is not None else 0

    return ProviderSessionsResponse(
        sessions=sessions_rec,
        total_sessions=total_sessions,
        average_latency_ms=average_latency_ms,
        total_interruptions=total_interruptions,
        total_audio_frames_sent=total_audio_frames_sent,
        total_audio_frames_received=total_audio_frames_received
    )
