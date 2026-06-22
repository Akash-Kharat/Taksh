import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime, timedelta

from app.services.providers.health import ProviderHealthMonitor
from app.models.database_models import ProviderHealthRecord
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import ProviderState
from app.core.config import settings

@pytest.mark.anyio
async def test_run_health_check_success(db_session):
    monitor = ProviderHealthMonitor()
    
    with patch('app.core.config.settings.DEFAULT_REALTIME_PROVIDER', "mock"):
        # Run health check on active providers (default is "mock" for all)
        records = await monitor.run_health_check(db_session)
        
        assert len(records) == 3
        for record in records:
            assert record.healthy is True
            assert record.latency_ms >= 0.0
            assert record.error_message is None
            assert record.success_count >= 1
            assert record.failure_count == 0
            assert record.timeout_count == 0

        # Running health check a second time should increment success count
        records_second = await monitor.run_health_check(db_session)
        assert len(records_second) == 3
        for record in records_second:
            assert record.success_count == 2
            assert record.failure_count == 0

@pytest.mark.anyio
async def test_run_health_check_failure_and_timeout(db_session):
    monitor = ProviderHealthMonitor()
    stt_provider = provider_factory.get_stt_provider("mock")
    
    with patch('app.core.config.settings.DEFAULT_REALTIME_PROVIDER', "mock"):
        # 1. Test general exception/failure during connect
        with patch.object(stt_provider, 'is_connected', return_value=False):
            with patch.object(stt_provider, 'connect', side_effect=Exception("Failed to connect mock")):
                records = await monitor.run_health_check(db_session)
                
                # Find the STT health record
                stt_rec = next(r for r in records if r.provider_type == "stt")
                assert stt_rec.healthy is False
                assert "Failed to connect mock" in stt_rec.error_message
                assert stt_rec.failure_count >= 1

        # 2. Test TimeoutError during connect
        with patch.object(stt_provider, 'is_connected', return_value=False):
            with patch.object(stt_provider, 'connect', side_effect=asyncio.TimeoutError()):
                records = await monitor.run_health_check(db_session)
                
                stt_rec = next(r for r in records if r.provider_type == "stt")
                assert stt_rec.healthy is False
                assert stt_rec.timeout_count >= 1
                assert "timeout" in stt_rec.error_message.lower()

        # 3. Test degraded/failed provider state
        with patch.object(stt_provider, 'get_state', return_value=ProviderState.FAILED):
            records = await monitor.run_health_check(db_session)
            stt_rec = next(r for r in records if r.provider_type == "stt")
            assert stt_rec.healthy is False
            assert "failed" in stt_rec.error_message.lower()

def test_prune_old_records(db_session):
    monitor = ProviderHealthMonitor()
    
    # Create a record that is 31 days old
    old_date = datetime.utcnow() - timedelta(days=32)
    old_record = ProviderHealthRecord(
        provider_name="mock",
        provider_type="stt",
        healthy=True,
        latency_ms=12.5,
        created_at=old_date
    )
    
    # Create a record that is 10 days old (should not be pruned)
    recent_date = datetime.utcnow() - timedelta(days=10)
    recent_record = ProviderHealthRecord(
        provider_name="mock",
        provider_type="stt",
        healthy=True,
        latency_ms=15.0,
        created_at=recent_date
    )
    
    db_session.add(old_record)
    db_session.add(recent_record)
    db_session.commit()
    
    old_id = old_record.record_id
    recent_id = recent_record.record_id
    
    # Verify both records exist
    total_records = db_session.query(ProviderHealthRecord).count()
    
    deleted_count = monitor.prune_old_records(db_session)
    assert deleted_count == 1
    
    # Verify only the old one was deleted
    left_records = db_session.query(ProviderHealthRecord).filter(
        ProviderHealthRecord.record_id == recent_id
    ).first()
    assert left_records is not None
    
    deleted_record = db_session.query(ProviderHealthRecord).filter(
        ProviderHealthRecord.record_id == old_id
    ).first()
    assert deleted_record is None
