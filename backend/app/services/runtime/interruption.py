import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.database_models import ConversationRuntimeSession
from app.services.runtime.events import runtime_event_bus, ConversationEvent

logger = logging.getLogger("runtime")


class InterruptionController:
    """Coordinates barge-in interruptions, clears output queues, and updates database statistics."""

    @staticmethod
    def register_handlers() -> None:
        """Registers the interruption handler to the event bus."""
        runtime_event_bus.subscribe(
            ConversationEvent.INTERRUPTION_DETECTED.value,
            InterruptionController.handle_interruption
        )
        logger.info("InterruptionController subscribed to INTERRUPTION_DETECTED events.")

    @staticmethod
    async def handle_interruption(runtime_session_id: str, metadata: dict) -> None:
        """
        Asynchronous subscriber callback triggered on INTERRUPTION_DETECTED.
        Flushes the audio queue and increments the interruption count in SQLite.
        """
        # 1. Clear output queue
        from app.services.runtime.output_queue import active_output_queues
        queue = active_output_queues.get(runtime_session_id)
        if queue:
            queue.clear()
            logger.info(f"Cleared audio output queue for session {runtime_session_id} due to interruption.")
        else:
            logger.debug(f"No active audio output queue found for session {runtime_session_id} to clear.")

        # 2. Update interruption_count in DB
        db: Session = SessionLocal()
        try:
            session_rec = db.query(ConversationRuntimeSession).filter(
                ConversationRuntimeSession.runtime_session_id == runtime_session_id
            ).first()
            if session_rec:
                session_rec.interruption_count += 1
                db.commit()
                logger.info(
                    f"Incremented interruption count for session {runtime_session_id} "
                    f"to {session_rec.interruption_count}."
                )
            else:
                logger.warning(f"Could not find session {runtime_session_id} to update interruption count.")
        except Exception as e:
            logger.error(f"Failed to increment interruption count for session {runtime_session_id}: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    async def trigger_interruption(runtime_session_id: str, db: Session) -> None:
        """
        Explicitly triggers an interruption by transitioning the active state machine.
        Validates transition and triggers downstream effects.
        """
        from app.services.runtime.state_machine import active_state_machines
        sm = active_state_machines.get(runtime_session_id)
        if not sm:
            raise ValueError(f"No active state machine found for session {runtime_session_id}")
        
        # State machine transition will publish INTERRUPTION_DETECTED event
        await sm.transition_to("interrupted", db)


# Automatically register the handler on module import
InterruptionController.register_handlers()
