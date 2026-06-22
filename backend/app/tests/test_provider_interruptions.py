import pytest
from unittest.mock import patch
from app.services.providers.factory import provider_factory
from app.services.runtime.interruption import InterruptionController
from app.models.database_models import ProviderSession, ConversationRuntimeSession

@pytest.mark.anyio
async def test_provider_interruption_persistence(db_session):
    # Retrieve mock provider and configure fake DB session correlation
    provider = provider_factory.get_realtime_provider("mock")
    provider.db_session_id = "test-session-uuid"
    provider.interruptions = 0
    
    # Seed ConversationRuntimeSession record to prevent lookups warning
    rt_rec = ConversationRuntimeSession(
        runtime_session_id="test-rt-session",
        conversation_state="active"
    )
    db_session.add(rt_rec)

    # Seed a ProviderSession record correlated with the runtime session
    session_rec = ProviderSession(
        provider_session_id="test-session-uuid",
        provider_name="mock",
        provider_state="active",
        runtime_session_id="test-rt-session",
        interruptions=0
    )
    db_session.add(session_rec)
    
    # Commit transaction to release write locks in SQLite shared cache
    db_session.commit()

    # Trigger interruption event flow
    with patch('app.core.database.SessionLocal', return_value=db_session):
        with patch('app.core.config.settings.DEFAULT_REALTIME_PROVIDER', "mock"):
            await InterruptionController.handle_interruption(
                runtime_session_id="test-rt-session",
                metadata={}
            )
        
        # Check in-memory count
        assert provider.interruptions == 1
        
        # Verify database record updated
        db_session.expire_all()
        updated_rec = db_session.query(ProviderSession).filter(
            ProviderSession.provider_session_id == "test-session-uuid"
        ).first()
        assert updated_rec is not None
        assert updated_rec.interruptions == 1
