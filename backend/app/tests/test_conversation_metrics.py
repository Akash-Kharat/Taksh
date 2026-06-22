import pytest
from sqlalchemy.orm import Session
from app.services.conversation.coordinator import conversation_coordinator
from app.services.conversation.playback import playback_controller
from app.models.database_models import ConversationMetrics

@pytest.mark.anyio
async def test_playback_queue_overflow_drop_metric(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Queue metrics should start at 0
    metrics = db_session.query(ConversationMetrics).filter(
        ConversationMetrics.runtime_session_id == runtime_session_id
    ).first()
    assert metrics is not None
    assert metrics.playback_dropped_chunks == 0

    # Overfill playback queue (MAX_PLAYBACK_QUEUE_ITEMS is 100, let's patch it to 3)
    with patch('app.core.config.settings.MAX_PLAYBACK_QUEUE_ITEMS', 3):
        # Enqueue 5 items
        for i in range(5):
            await playback_controller.enqueue_audio(runtime_session_id, f"chunk-{i}".encode(), db=db_session)
        
        # Check depth
        assert playback_controller.get_queue_depth(runtime_session_id) == 3
        
        # Check database metric updated (dropped 2 items)
        db_session.refresh(metrics)
        assert metrics.playback_dropped_chunks == 2
        
        # Items remaining in queue should be the latest 3 (chunk-2, chunk-3, chunk-4)
        c1 = playback_controller.retrieve_chunk(runtime_session_id)
        assert c1 == b"chunk-2"


# Add patch helper for unit tests
from unittest.mock import patch
