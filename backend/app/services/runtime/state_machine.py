import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.database_models import ConversationRuntimeSession
from app.services.runtime.turn_manager import TurnManager
from app.services.runtime.events import runtime_event_bus, ConversationEvent

logger = logging.getLogger("runtime")

class TransitionError(Exception):
    """Raised when an invalid state transition is requested in the state machine."""
    pass


class RealtimeStateMachine:
    """Deterministic async-locked state machine coordinating state transitions and durations."""
    
    ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
        "idle": ["listening", "closed"],
        "listening": ["thinking", "closed"],
        "thinking": ["speaking", "closed"],
        "speaking": ["listening", "interrupted", "closed"],
        "interrupted": ["listening", "closed"],
        "closed": []
    }

    def __init__(self, runtime_session_id: str):
        self.runtime_session_id = runtime_session_id
        self.lock = asyncio.Lock()
        self.last_transition_time = datetime.utcnow()

    def _validate_transition(self, old_state: str, new_state: str) -> None:
        """Validates if transition is allowed, always permitting transitions to 'closed'."""
        if new_state == "closed":
            return
        allowed = self.ALLOWED_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            raise TransitionError(
                f"Invalid transition from state '{old_state}' to '{new_state}'"
            )

    async def transition_to(self, new_state: str, db: Session) -> None:
        """
        Transitions the session to a new state under a serialization lock.
        Computes duration in previous state and commits state variables to database.
        """
        async with self.lock:
            # 1. Fetch current session record
            session_rec = db.query(ConversationRuntimeSession).filter(
                ConversationRuntimeSession.runtime_session_id == self.runtime_session_id
            ).first()
            if not session_rec:
                raise ValueError(f"Runtime session '{self.runtime_session_id}' not found in database.")

            old_state = session_rec.conversation_state
            
            # 2. Validate state machine path
            self._validate_transition(old_state, new_state)

            # 3. Resolve turn ownership
            new_owner = TurnManager.get_owner_for_state(new_state)

            # 4. Calculate duration in previous state
            now = datetime.utcnow()
            duration_ms = int((now - self.last_transition_time).total_seconds() * 1000)

            # 5. Accumulate duration metrics
            if old_state == "listening":
                session_rec.total_listening_ms += duration_ms
            elif old_state == "thinking":
                session_rec.total_thinking_ms += duration_ms
            elif old_state == "speaking":
                session_rec.total_speaking_ms += duration_ms

            # 6. Apply state and owner mutations
            session_rec.conversation_state = new_state
            session_rec.current_turn_owner = new_owner
            if new_state == "closed":
                session_rec.ended_at = now

            db.commit()
            db.refresh(session_rec)
            
            self.last_transition_time = now
            logger.info(
                f"Session {self.runtime_session_id} transitioned: '{old_state}' -> '{new_state}' "
                f"(turn_owner={new_owner}, prev_duration={duration_ms}ms)"
            )

            # 7. Publish finished/started lifecycle events
            if old_state == "thinking":
                await runtime_event_bus.publish(
                    self.runtime_session_id,
                    ConversationEvent.THINKING_FINISHED.value,
                    {"duration_ms": duration_ms}
                )
            elif old_state == "speaking":
                await runtime_event_bus.publish(
                    self.runtime_session_id,
                    ConversationEvent.ASSISTANT_FINISHED_SPEAKING.value,
                    {"duration_ms": duration_ms}
                )

            event_type = None
            if new_state == "listening":
                event_type = ConversationEvent.USER_STARTED_SPEAKING.value
            elif new_state == "thinking":
                event_type = ConversationEvent.THINKING_STARTED.value
            elif new_state == "speaking":
                event_type = ConversationEvent.ASSISTANT_STARTED_SPEAKING.value
            elif new_state == "interrupted":
                event_type = ConversationEvent.INTERRUPTION_DETECTED.value
            elif new_state == "closed":
                event_type = ConversationEvent.SESSION_CLOSED.value

            if event_type:
                await runtime_event_bus.publish(
                    self.runtime_session_id,
                    event_type,
                    {"duration_ms": duration_ms}
                )


# In-memory active state machines cache: runtime_session_id -> RealtimeStateMachine
active_state_machines: Dict[str, RealtimeStateMachine] = {}
