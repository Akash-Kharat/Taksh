from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import func

from app.core.database import get_db
from app.core.logger import api_logger
from app.services.providers.registry import provider_registry
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import ProviderState
from app.models.database_models import ProviderHealthRecord
from app.schemas.providers import ProviderDiagnosticInfo

router = APIRouter()

@router.get("/providers/info", response_model=List[ProviderDiagnosticInfo])
async def get_providers_info(db: DbSession = Depends(get_db)):
    api_logger.info("Serving provider diagnostics check")
    results = []

    # Iterate over all registered provider types and names
    provider_types = [
        ("stt", provider_registry.list_stt_providers(), provider_factory.get_stt_provider),
        ("tts", provider_registry.list_tts_providers(), provider_factory.get_tts_provider),
        ("realtime", provider_registry.list_realtime_providers(), provider_factory.get_realtime_provider)
    ]

    for p_type, names, get_provider_fn in provider_types:
        for name in names:
            try:
                # Instantiate/retrieve provider via factory to get metadata and state
                provider_instance = get_provider_fn(name)
                metadata = provider_instance.get_metadata()
                state = provider_instance.get_state()
            except Exception as e:
                api_logger.error(f"Error loading provider {name} of type {p_type}: {e}")
                continue

            # Query database for the latest health check
            last_record = db.query(ProviderHealthRecord).filter(
                ProviderHealthRecord.provider_name == name,
                ProviderHealthRecord.provider_type == p_type
            ).order_by(ProviderHealthRecord.created_at.desc()).first()

            # Healthy status is determined by the last run or if it's connected/connecting
            healthy = last_record.healthy if last_record else (state in [ProviderState.CONNECTED, ProviderState.DISCONNECTED, ProviderState.CONNECTING])
            
            # Query last successful operation timestamp
            last_success = db.query(ProviderHealthRecord).filter(
                ProviderHealthRecord.provider_name == name,
                ProviderHealthRecord.provider_type == p_type,
                ProviderHealthRecord.healthy == True
            ).order_by(ProviderHealthRecord.created_at.desc()).first()

            last_successful_operation = last_success.created_at if last_success else None

            # Calculate average latency
            avg_latency = db.query(func.avg(ProviderHealthRecord.latency_ms)).filter(
                ProviderHealthRecord.provider_name == name,
                ProviderHealthRecord.provider_type == p_type
            ).scalar()

            average_latency_ms = float(avg_latency) if avg_latency is not None else 0.0

            results.append(
                ProviderDiagnosticInfo(
                    provider=name,
                    provider_type=p_type,
                    state=state.value,
                    healthy=healthy,
                    supports_streaming=metadata.supports_streaming,
                    last_successful_operation=last_successful_operation,
                    average_latency_ms=average_latency_ms
                )
            )

    return results
