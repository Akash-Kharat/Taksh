import pytest
from unittest.mock import patch
from app.services.providers.manager import provider_manager
from app.core.config import settings

@pytest.mark.anyio
async def test_provider_fallback_circuit_breaker(db_session):
    # Reset provider manager state before test
    provider_manager.consecutive_failures = 0
    provider_manager.fallback_active = False
    provider_manager.failure_count = 0
    provider_manager.last_error = None

    # Verify circuit breaker failure thresholds and dynamic mock fallback routing
    with patch('app.core.config.settings.PROVIDER_FAILURE_THRESHOLD', 5):
        # Trigger 4 failures
        for i in range(4):
            provider_manager.record_failure(Exception(f"Fail {i}"))
        
        assert provider_manager.consecutive_failures == 4
        assert provider_manager.fallback_active is False
        
        # Trigger 5th failure to trip the circuit breaker
        provider_manager.record_failure(Exception("Fail 5"))
        assert provider_manager.consecutive_failures == 5
        assert provider_manager.fallback_active is True
        
        # Verify fallback active routing resolves to "mock" instead of primary "gemini_live"
        with patch('app.core.config.settings.ENABLE_PROVIDER_FALLBACK', True):
            resolved = provider_manager._get_provider_name(None, "gemini_live")
            assert resolved == "mock"
            
        # Verify that if fallback is disabled, it resolves back to the configured provider
        with patch('app.core.config.settings.ENABLE_PROVIDER_FALLBACK', False):
            resolved = provider_manager._get_provider_name(None, "gemini_live")
            assert resolved == "gemini_live"
