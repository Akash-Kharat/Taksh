import asyncio
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.database_models import ConversationRuntimeSession
from app.services.runtime.state_machine import RealtimeStateMachine, active_state_machines, TransitionError
from app.services.runtime.output_queue import active_output_queues


@pytest.mark.anyio
async def test_state_machine_transitions():
    db = SessionLocal()
    try:
        # 1. Create a dummy session in DB
        session_rec = ConversationRuntimeSession(
        conversation_state="idle",
        current_turn_owner="none",
        total_listening_ms=0,
        total_thinking_ms=0,
        total_speaking_ms=0
    )
        db.add(session_rec)
        db.commit()
        db.refresh(session_rec)
        
        runtime_session_id = session_rec.runtime_session_id
        
        # 2. Instantiate state machine
        sm = RealtimeStateMachine(runtime_session_id)
        
        # Verify initial conditions
        assert session_rec.conversation_state == "idle"
        assert session_rec.current_turn_owner == "none"

        # Test invalid transition (idle -> thinking is not allowed)
        with pytest.raises(TransitionError):
            await sm.transition_to("thinking", db)
            
        # Test valid transition (idle -> listening)
        await sm.transition_to("listening", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "listening"
        assert session_rec.current_turn_owner == "user"

        # Sleep a bit to accumulate listening duration
        await asyncio.sleep(0.05)
        
        # Transition: listening -> thinking
        await sm.transition_to("thinking", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "thinking"
        assert session_rec.current_turn_owner == "none"
        assert session_rec.total_listening_ms >= 40  # should be around 50ms

        # Sleep a bit to accumulate thinking duration
        await asyncio.sleep(0.05)

        # Transition: thinking -> speaking
        await sm.transition_to("speaking", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "speaking"
        assert session_rec.current_turn_owner == "assistant"
        assert session_rec.total_thinking_ms >= 40

        # Sleep a bit to accumulate speaking duration
        await asyncio.sleep(0.05)

        # Transition: speaking -> interrupted
        await sm.transition_to("interrupted", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "interrupted"
        assert session_rec.current_turn_owner == "user"
        assert session_rec.total_speaking_ms >= 40

        # Transition: interrupted -> listening
        await sm.transition_to("listening", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "listening"
        assert session_rec.current_turn_owner == "user"

        # Transition to closed (should be allowed from listening)
        await sm.transition_to("closed", db)
        db.refresh(session_rec)
        assert session_rec.conversation_state == "closed"
        assert session_rec.current_turn_owner == "none"
        assert session_rec.ended_at is not None
    finally:
        db.close()

