import pytest
from unittest.mock import patch, AsyncMock
from app.services.providers.gemini_live import GeminiLiveProvider
from app.services.providers.contracts import ProviderState
from app.services.providers.manager import provider_manager
from app.models.database_models import ProviderSession

@pytest.mark.anyio
async def test_provider_reconnect_success(db_session):
    provider = GeminiLiveProvider()
    
    mock_ws = AsyncMock()
    
    connect_calls = 0
    async def mock_connect_impl(url, open_timeout=None):
        nonlocal connect_calls
        connect_calls += 1
        if connect_calls < 3:
            raise ConnectionError("Temporary connection failure")
        return mock_ws

    provider_manager.reconnect_count = 0
    provider_manager.failure_count = 0

    with patch('app.core.config.settings.GEMINI_API_KEY', "test-key"):
        with patch('app.core.config.settings.PROVIDER_RECONNECT_DELAY_SECONDS', 0.01):
            with patch('websockets.connect', side_effect=mock_connect_impl):
                await provider.connect(db=db_session)
                
                assert provider.get_state() == ProviderState.CONNECTED
                assert provider.provider_state == "active"
                assert connect_calls == 3
                
                db_session.expire_all()
                session_rec = db_session.query(ProviderSession).filter(
                    ProviderSession.provider_session_id == provider.db_session_id
                ).first()
                assert session_rec is not None
                assert session_rec.provider_state == "active"
                
                assert provider_manager.reconnect_count >= 1

                await provider.disconnect()
