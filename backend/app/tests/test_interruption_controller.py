import asyncio
import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

from app.models.database_models import ConversationRuntimeSession
from app.services.runtime.events import runtime_event_bus, ConversationEvent
from app.services.runtime.state_machine import RealtimeStateMachine, active_state_machines
from app.services.runtime.output_queue import AudioOutputQueue, active_output_queues
from app.services.runtime.interruption import InterruptionController


@pytest.mark.anyio
async def test_audio_output_queue():
    queue = AudioOutputQueue()
    assert queue.size() == 0
    
    queue.enqueue({"data": "chunk1"})
    queue.enqueue({"data": "chunk2"})
    assert queue.size() == 2
    
    items = queue.flush()
    assert len(items) == 2
    assert queue.size() == 0
    assert items[0]["data"] == "chunk1"
    
    queue.enqueue({"data": "chunk3"})
    assert queue.size() == 1
    queue.clear()
    assert queue.size() == 0


@pytest.mark.anyio
async def test_interruption_handler_direct():
    db = SessionLocal()
    try:
        # 1. Setup session in DB
        session_rec = ConversationRuntimeSession(
            conversation_state="speaking",
            current_turn_owner="assistant",
            interruption_count=0
        )
        db.add(session_rec)
        db.commit()
        db.refresh(session_rec)
        
        runtime_session_id = session_rec.runtime_session_id
        
        # 2. Setup active output queue
        queue = AudioOutputQueue()
        queue.enqueue({"data": "payload"})
        active_output_queues[runtime_session_id] = queue
        
        assert queue.size() == 1
        
        # 3. Call handle_interruption directly
        await InterruptionController.handle_interruption(runtime_session_id, {})
        
        # 4. Assert queue is cleared and DB session count updated
        assert queue.size() == 0
        db.refresh(session_rec)
        assert session_rec.interruption_count == 1
        
        # Clean up
        active_output_queues.pop(runtime_session_id, None)
    finally:
        db.close()


@pytest.mark.anyio
async def test_interruption_trigger_flow():
    db = SessionLocal()
    try:
        # 1. Setup session in DB
        session_rec = ConversationRuntimeSession(
            conversation_state="speaking",
            current_turn_owner="assistant",
            interruption_count=0
        )
        db.add(session_rec)
        db.commit()
        db.refresh(session_rec)
        
        runtime_session_id = session_rec.runtime_session_id
        
        # 2. Setup active state machine and active output queue
        sm = RealtimeStateMachine(runtime_session_id)
        active_state_machines[runtime_session_id] = sm
        
        queue = AudioOutputQueue()
        queue.enqueue({"data": "assistant_voice_chunk"})
        active_output_queues[runtime_session_id] = queue
        
        assert queue.size() == 1
        
        # 3. Trigger interruption
        await InterruptionController.trigger_interruption(runtime_session_id, db)
        
        # Allow event loop to process callbacks
        await asyncio.sleep(0.01)
        
        # 4. Verify transition, queue cleared, and DB counter incremented
        db.refresh(session_rec)
        assert session_rec.conversation_state == "interrupted"
        assert session_rec.current_turn_owner == "user"
        assert session_rec.interruption_count == 1
        assert queue.size() == 0
        
        # Clean up
        active_state_machines.pop(runtime_session_id, None)
        active_output_queues.pop(runtime_session_id, None)
    finally:
        db.close()
