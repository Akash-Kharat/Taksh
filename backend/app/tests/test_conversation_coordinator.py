import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.services.conversation.coordinator import conversation_coordinator
from app.models.database_models import ConversationRuntimeSession, Session as MemorySession

@pytest.mark.anyio
async def test_coordinator_start_session(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session, "fake-voice-id")
    
    assert runtime_session is not None
    assert runtime_session.voice_session_id == "fake-voice-id"
    assert runtime_session.conversation_state == "listening"
    assert runtime_session.conversation_session_state == "active"

    # Verify correlated memory session exists
    mem_session = db_session.query(MemorySession).filter(
        MemorySession.session_id == runtime_session.runtime_session_id
    ).first()
    assert mem_session is not None


@pytest.mark.anyio
async def test_coordinator_session_recovery_states(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id
    
    # State transitions
    assert runtime_session.conversation_session_state == "active"
    
    # Simulate recovering state
    runtime_session.conversation_session_state = "recovering"
    db_session.commit()
    
    db_session.refresh(runtime_session)
    assert runtime_session.conversation_session_state == "recovering"
    
    await conversation_coordinator.stop_conversation(db_session, runtime_session_id)
    db_session.refresh(runtime_session)
    assert runtime_session.conversation_session_state == "closed"


@pytest.mark.anyio
async def test_coordinator_consolidation_failure_isolation(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Mock SessionConsolidator to fail
    with patch('app.services.conversation.consolidation.SessionConsolidator.consolidate_session', side_effect=Exception("Consolidation exploded")):
        # Stopping conversation should complete cleanly despite the consolidation error
        await conversation_coordinator.stop_conversation(db_session, runtime_session_id)
        
        db_session.refresh(runtime_session)
        assert runtime_session.conversation_session_state == "closed"
        assert runtime_session.session_summary_status == "failed"
