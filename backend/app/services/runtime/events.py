import asyncio
import uuid
import logging
from enum import Enum
from datetime import datetime
from typing import Dict, List, Callable, Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.database_models import ConversationRuntimeTrace

logger = logging.getLogger("runtime")

class ConversationEvent(str, Enum):
    USER_STARTED_SPEAKING = "USER_STARTED_SPEAKING"
    USER_STOPPED_SPEAKING = "USER_STOPPED_SPEAKING"
    ASSISTANT_STARTED_SPEAKING = "ASSISTANT_STARTED_SPEAKING"
    ASSISTANT_FINISHED_SPEAKING = "ASSISTANT_FINISHED_SPEAKING"
    INTERRUPTION_DETECTED = "INTERRUPTION_DETECTED"
    THINKING_STARTED = "THINKING_STARTED"
    THINKING_FINISHED = "THINKING_FINISHED"
    SESSION_CLOSED = "SESSION_CLOSED"


class ConversationEventBus:
    """Decoupled asynchronous event bus managing publisher/subscriber model and database tracing."""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConversationEventBus, cls).__new__(cls)
            cls._instance.subscriptions = {event.value: [] for event in ConversationEvent}
            cls._instance.sequences = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribes a callback to a specific event type."""
        if event_type in self.subscriptions:
            if callback not in self.subscriptions[event_type]:
                self.subscriptions[event_type].append(callback)
                logger.info(f"Subscribed callback to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribes a callback from a specific event type."""
        if event_type in self.subscriptions:
            if callback in self.subscriptions[event_type]:
                self.subscriptions[event_type].remove(callback)
                logger.info(f"Unsubscribed callback from event: {event_type}")

    async def publish(self, runtime_session_id: str, event_type: str, metadata: dict = None) -> None:
        """
        Publishes an event. Computes sequence number, writes trace record to SQLite,
        and triggers callback hooks concurrently.
        """
        if metadata is None:
            metadata = {}

        # 1. Get and increment monotonic sequence
        async with self._lock:
            current_seq = self.sequences.get(runtime_session_id, 0) + 1
            self.sequences[runtime_session_id] = current_seq

        # 2. Persist event trace to database
        db: Session = SessionLocal()
        try:
            trace = ConversationRuntimeTrace(
                trace_id=str(uuid.uuid4()),
                runtime_session_id=runtime_session_id,
                event_type=event_type,
                event_sequence=current_seq,
                timestamp=datetime.utcnow(),
                event_metadata=metadata
            )
            db.add(trace)
            db.commit()
            logger.debug(f"Event trace persisted: {event_type} (seq={current_seq}) for session {runtime_session_id}")
        except Exception as e:
            logger.error(f"Failed to persist runtime event trace: {e}")
            db.rollback()
        finally:
            db.close()

        # 3. Trigger callback triggers
        callbacks = self.subscriptions.get(event_type, [])
        if callbacks:
            tasks = []
            for cb in callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        tasks.append(cb(runtime_session_id, metadata))
                    else:
                        cb(runtime_session_id, metadata)
                except Exception as e:
                    logger.error(f"Error in event callback setup: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def get_session_sequence(self, runtime_session_id: str) -> int:
        """Returns the current sequence number for the session."""
        return self.sequences.get(runtime_session_id, 0)

    def reset_session(self, runtime_session_id: str) -> None:
        """Resets the sequence count for a session."""
        self.sequences.pop(runtime_session_id, None)


runtime_event_bus = ConversationEventBus()
