import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.models.database_models import ConversationRuntimeSession
from app.services.conversation.coordinator import conversation_coordinator

@pytest.mark.anyio
async def test_episodic_memory_failure_isolation(db_session: Session):
    # 1. Start session
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # 2. Mock episodic consolidation to raise an Exception
    with patch(
        'app.services.conversation.episodic_memory_service.episodic_memory_service.consolidate_episodic_memory',
        side_effect=Exception("Vector database went offline!")
    ):
        # 3. Stop session - should execute cleanly despite episodic memory consolidation failure
        await conversation_coordinator.stop_conversation(db_session, runtime_session_id)

        # 4. Assert session is closed successfully
        db_session.refresh(runtime_session)
        assert runtime_session.conversation_session_state == "closed"
