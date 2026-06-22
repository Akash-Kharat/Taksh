import logging
import collections
import asyncio
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.database_models import ConversationMetrics

logger = logging.getLogger("conversation")

class AudioPlaybackController:
    """Manages audio queues, streams chunks, tracks completion, and manages speaking states."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AudioPlaybackController, cls).__new__(cls)
            # Map of runtime_session_id -> deque of bytes
            cls._instance.playback_queues: Dict[str, collections.deque] = {}
            # Map of runtime_session_id -> int
            cls._instance.dropped_chunks_cache: Dict[str, int] = {}
            # Map of runtime_session_id -> asyncio.Event indicating playback completion
            cls._instance.completion_events: Dict[str, asyncio.Event] = {}
        return cls._instance

    def get_queue(self, runtime_session_id: str) -> collections.deque:
        """Retrieves or creates playback queue for a session."""
        if runtime_session_id not in self.playback_queues:
            self.playback_queues[runtime_session_id] = collections.deque()
        return self.playback_queues[runtime_session_id]

    def get_completion_event(self, runtime_session_id: str) -> asyncio.Event:
        """Retrieves or creates completion event for a session."""
        if runtime_session_id not in self.completion_events:
            self.completion_events[runtime_session_id] = asyncio.Event()
            # Default to set (completed) if it's new/empty
            self.completion_events[runtime_session_id].set()
        return self.completion_events[runtime_session_id]

    def get_queue_depth(self, runtime_session_id: str) -> int:
        """Returns the size of the playback queue."""
        return len(self.playback_queues.get(runtime_session_id, []))

    async def enqueue_audio(self, runtime_session_id: str, audio_bytes: bytes, db: Optional[Session] = None) -> None:
        """
        Enqueues an audio chunk for playback.
        Enforces MAX_PLAYBACK_QUEUE_ITEMS limit and discards the oldest chunk if exceeded.
        """
        queue = self.get_queue(runtime_session_id)
        event = self.get_completion_event(runtime_session_id)
        event.clear()  # Playback is now active/pending

        if len(queue) >= settings.MAX_PLAYBACK_QUEUE_ITEMS:
            queue.popleft()
            # Record dropped chunk in local cache and DB
            self.dropped_chunks_cache[runtime_session_id] = self.dropped_chunks_cache.get(runtime_session_id, 0) + 1
            
            db_conn = db
            close_db = False
            if not db_conn:
                db_conn = SessionLocal()
                close_db = True
            try:
                metrics_rec = db_conn.query(ConversationMetrics).filter(
                    ConversationMetrics.runtime_session_id == runtime_session_id
                ).first()
                if metrics_rec:
                    metrics_rec.playback_dropped_chunks += 1
                    if not db:
                        db_conn.commit()
                    else:
                        db_conn.flush()
            except Exception as e:
                logger.error(f"Failed to update playback dropped chunks: {e}")
                if close_db:
                    db_conn.rollback()
            finally:
                if close_db:
                    db_conn.close()

            logger.warning(
                f"Playback queue limit reached for session {runtime_session_id}. "
                f"Discarded oldest chunk. Total dropped: {self.dropped_chunks_cache[runtime_session_id]}"
            )

        queue.append(audio_bytes)

    def retrieve_chunk(self, runtime_session_id: str) -> Optional[bytes]:
        """Pulls the next queued audio chunk. Sets completion event if queue becomes empty."""
        queue = self.get_queue(runtime_session_id)
        if queue:
            chunk = queue.popleft()
            if not queue:
                event = self.get_completion_event(runtime_session_id)
                event.set()  # Queue is now empty/completed
            return chunk
        return None

    def flush(self, runtime_session_id: str) -> None:
        """Clears the queue and marks playback completed."""
        if runtime_session_id in self.playback_queues:
            self.playback_queues[runtime_session_id].clear()
        event = self.get_completion_event(runtime_session_id)
        event.set()
        logger.info(f"Flushed audio playback queue for session {runtime_session_id}")

    async def wait_for_completion(self, runtime_session_id: str) -> None:
        """Blocks until the playback queue becomes empty."""
        event = self.get_completion_event(runtime_session_id)
        await event.wait()

    async def simulate_playback(self, runtime_session_id: str, db: Session) -> None:
        """
        Simulates playback asynchronously (useful for unit tests and headless mode).
        Pulls chunks, waits for duration, and transitions the state machine.
        """
        from app.services.runtime.state_machine import active_state_machines
        sm = active_state_machines.get(runtime_session_id)
        if not sm:
            logger.warning(f"No active state machine found for session {runtime_session_id} to run playback simulation.")
            return

        # Estimate chunk durations (e.g. 50ms per chunk or short delay)
        # Transition state machine to speaking
        try:
            await sm.transition_to("speaking", db)
        except Exception as e:
            logger.warning(f"Failed to transition state machine to speaking: {e}")
            return

        queue = self.get_queue(runtime_session_id)
        while queue:
            self.retrieve_chunk(runtime_session_id)
            # Sleep 10ms to simulate output
            await asyncio.sleep(0.01)

        # Wait for completion event just in case
        await self.wait_for_completion(runtime_session_id)

        # Transition back to listening
        try:
            await sm.transition_to("listening", db)
        except Exception as e:
            logger.warning(f"Failed to transition state machine back to listening: {e}")


# Global playback controller singleton instance
playback_controller = AudioPlaybackController()
