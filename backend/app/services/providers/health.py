import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.database_models import ProviderHealthRecord
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import ProviderState

logger = logging.getLogger("providers")


class ProviderHealthMonitor:
    """Monitors provider health, latency, connection status, and handles DB logs & retention pruning."""

    async def run_health_check(
        self,
        db: Session,
        runtime_session_id: Optional[str] = None,
        voice_session_id: Optional[str] = None
    ) -> List[ProviderHealthRecord]:
        """
        Executes health checks on all active providers (STT, TTS, Realtime).
        Measures latency, updates timeout/success/failure metrics, and logs records.
        """
        records = []
        
        # Determine active provider names from settings
        stt_name = settings.DEFAULT_STT_PROVIDER
        tts_name = settings.DEFAULT_TTS_PROVIDER
        realtime_name = settings.DEFAULT_REALTIME_PROVIDER

        active_providers = [
            (stt_name, "stt", provider_factory.get_stt_provider(stt_name)),
            (tts_name, "tts", provider_factory.get_tts_provider(tts_name)),
            (realtime_name, "realtime", provider_factory.get_realtime_provider(realtime_name))
        ]

        for name, p_type, provider in active_providers:
            start_time = time.perf_counter()
            healthy = True
            error_message = None
            timeout = False

            try:
                # Stub connection check to measure latency
                if not provider.is_connected():
                    await asyncio.wait_for(
                        provider.connect(),
                        timeout=float(settings.PROVIDER_REQUEST_TIMEOUT_SECONDS)
                    )
                
                state = provider.get_state()
                if state in [ProviderState.FAILED, ProviderState.DISCONNECTED]:
                    healthy = False
                    error_message = f"Provider is in state: {state.value}"
            except asyncio.TimeoutError:
                healthy = False
                timeout = True
                error_message = "Connection timeout occurred during health check."
            except Exception as e:
                healthy = False
                error_message = str(e)
            
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Query last health record to roll over connection metrics
            last_record = db.query(ProviderHealthRecord).filter(
                ProviderHealthRecord.provider_name == name,
                ProviderHealthRecord.provider_type == p_type
            ).order_by(ProviderHealthRecord.created_at.desc()).first()

            prev_success = last_record.success_count if last_record else 0
            prev_failure = last_record.failure_count if last_record else 0
            prev_timeout = last_record.timeout_count if last_record else 0

            success_count = prev_success + (1 if healthy else 0)
            failure_count = prev_failure + (0 if healthy else 1)
            timeout_count = prev_timeout + (1 if timeout else 0)

            # Persist record
            record = ProviderHealthRecord(
                provider_name=name,
                provider_type=p_type,
                healthy=healthy,
                latency_ms=latency_ms,
                error_message=error_message,
                timeout_count=timeout_count,
                failure_count=failure_count,
                success_count=success_count,
                runtime_session_id=runtime_session_id,
                voice_session_id=voice_session_id,
                created_at=datetime.utcnow()
            )
            db.add(record)
            records.append(record)

        try:
            db.commit()
            logger.info("Successfully recorded provider health checks.")
        except Exception as e:
            logger.error(f"Failed to commit provider health check logs: {e}")
            db.rollback()

        return records

    def prune_old_records(self, db: Session) -> int:
        """Deletes historical health records older than the retention window (default 30 days)."""
        limit_date = datetime.utcnow() - timedelta(days=settings.PROVIDER_HEALTH_RETENTION_DAYS)
        try:
            deleted_count = db.query(ProviderHealthRecord).filter(
                ProviderHealthRecord.created_at < limit_date
            ).delete()
            db.commit()
            if deleted_count > 0:
                logger.info(f"Pruned {deleted_count} stale provider health records older than {settings.PROVIDER_HEALTH_RETENTION_DAYS} days.")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to prune old provider health records: {e}")
            db.rollback()
            return 0


# Background loop execution task runner
async def start_health_monitor_loop() -> None:
    """Periodic health monitoring background task."""
    logger.info("Starting provider health monitor background runner loop.")
    monitor = ProviderHealthMonitor()
    while True:
        if not settings.ENABLE_PROVIDER_HEALTH_CHECKS:
            logger.info("Provider health checks are disabled. Exiting background loop.")
            break

        db = SessionLocal()
        try:
            await monitor.run_health_check(db)
            monitor.prune_old_records(db)
        except Exception as e:
            logger.error(f"Error in background health monitor: {e}")
        finally:
            db.close()
            
        await asyncio.sleep(60)
