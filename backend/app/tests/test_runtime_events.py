import asyncio
import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

from app.models.database_models import ConversationRuntimeTrace
from app.services.runtime.events import runtime_event_bus, ConversationEvent


@pytest.mark.anyio
async def test_runtime_event_bus_publishing():
    runtime_session_id = "test-session-123"
    
    # Reset event bus state for the session
    runtime_event_bus.reset_session(runtime_session_id)
    
    # Trace callback calls
    callback_calls = []
    
    async def dummy_callback(session_id: str, metadata: dict):
        callback_calls.append((session_id, metadata))

    # Subscribe callback
    runtime_event_bus.subscribe(ConversationEvent.USER_STARTED_SPEAKING.value, dummy_callback)
    
    db = SessionLocal()
    try:
        # Publish first event
        meta1 = {"test_key": "val1"}
        await runtime_event_bus.publish(
            runtime_session_id,
            ConversationEvent.USER_STARTED_SPEAKING.value,
            meta1
        )
        
        # Publish second event
        meta2 = {"test_key": "val2"}
        await runtime_event_bus.publish(
            runtime_session_id,
            ConversationEvent.USER_STOPPED_SPEAKING.value,
            meta2
        )
        
        # Verify sequence numbers in memory
        assert runtime_event_bus.get_session_sequence(runtime_session_id) == 2
        
        # Verify callback execution
        assert len(callback_calls) == 1
        assert callback_calls[0] == (runtime_session_id, meta1)
        
        # Verify database trace persistence
        traces = db.query(ConversationRuntimeTrace).filter(
            ConversationRuntimeTrace.runtime_session_id == runtime_session_id
        ).order_by(ConversationRuntimeTrace.event_sequence).all()
        
        assert len(traces) == 2
        assert traces[0].event_type == ConversationEvent.USER_STARTED_SPEAKING.value
        assert traces[0].event_sequence == 1
        assert traces[0].event_metadata == meta1
        
        assert traces[1].event_type == ConversationEvent.USER_STOPPED_SPEAKING.value
        assert traces[1].event_sequence == 2
        assert traces[1].event_metadata == meta2
        
    finally:
        db.close()
        runtime_event_bus.unsubscribe(ConversationEvent.USER_STARTED_SPEAKING.value, dummy_callback)
        runtime_event_bus.reset_session(runtime_session_id)
