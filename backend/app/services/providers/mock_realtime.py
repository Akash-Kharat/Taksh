import logging
import collections
from app.core.config import settings
from app.services.providers.contracts import RealtimeConversationProvider, ProviderMetadata, ProviderState
from app.services.providers.registry import provider_registry

logger = logging.getLogger("providers")


class MockRealtimeProvider(RealtimeConversationProvider):
    """Offline mock Realtime Conversation engine for testing and local operations."""

    def __init__(self):
        self._state = ProviderState.DISCONNECTED
        self.audio_queue = collections.deque()
        self.text_queue = collections.deque()
        self.dropped_messages = 0
        self.interruptions = 0
        self.db_session_id = None

    async def interrupt(self, db = None) -> None:
        self.interruptions += 1
        if self.db_session_id:
            db_conn = db
            if db_conn is None:
                from app.core.database import SessionLocal
                db_conn = SessionLocal()
            try:
                from app.models.database_models import ProviderSession
                session_rec = db_conn.query(ProviderSession).filter(
                    ProviderSession.provider_session_id == self.db_session_id
                ).first()
                if session_rec:
                    session_rec.interruptions += 1
                    if db is None:
                        db_conn.commit()
                    else:
                        db_conn.flush()
            except Exception as e:
                logger.error(f"Failed to update provider interruptions in DB: {e}")
                if db is None:
                    db_conn.rollback()
            finally:
                if db is None:
                    db_conn.close()

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock_realtime",
            provider_type="realtime",
            version="1.0.0",
            supports_streaming=True,
            supports_interruptions=True,
            supports_audio_input=True,
            supports_audio_output=True,
            supports_text_input=True,
            supports_text_output=True
        )

    def get_state(self) -> ProviderState:
        return self._state

    async def connect(self) -> None:
        self._state = ProviderState.CONNECTING
        logger.info("Mock Realtime connecting...")
        self._state = ProviderState.CONNECTED
        logger.info("Mock Realtime connected.")

    async def disconnect(self) -> None:
        logger.info("Mock Realtime disconnecting...")
        self._state = ProviderState.DISCONNECTED
        logger.info("Mock Realtime disconnected.")

    def is_connected(self) -> bool:
        return self._state == ProviderState.CONNECTED

    async def start_session(self) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime provider connection is not active.")
        logger.info("Starting mock realtime session...")
        self.audio_queue.clear()
        self.text_queue.clear()
        self.dropped_messages = 0

    async def end_session(self) -> None:
        logger.info("Ending mock realtime session.")
        self.audio_queue.clear()
        self.text_queue.clear()

    def _enqueue(self, queue: collections.deque, item: any) -> None:
        """Helper to enqueue items while enforcing MAX_PROVIDER_QUEUE_SIZE budget."""
        if len(queue) >= settings.MAX_PROVIDER_QUEUE_SIZE:
            queue.popleft()
            self.dropped_messages += 1
            logger.warning(
                f"Realtime provider queue limit ({settings.MAX_PROVIDER_QUEUE_SIZE}) reached. "
                f"Dropped oldest message. Total dropped: {self.dropped_messages}"
            )
        queue.append(item)

    async def send_audio(self, audio_data: bytes) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime provider session is not active.")
        logger.info(f"Mock Realtime sending {len(audio_data)} bytes of audio.")
        self._enqueue(self.audio_queue, audio_data)

    async def receive_audio(self) -> bytes:
        if not self.is_connected():
            raise RuntimeError("Realtime provider session is not active.")
        if self.audio_queue:
            return self.audio_queue.popleft()
        return b"\x00" * 100

    async def send_text(self, text: str) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime provider session is not active.")
        logger.info(f"Mock Realtime sending text: '{text}'")
        self._enqueue(self.text_queue, text)

    async def receive_text(self) -> str:
        if not self.is_connected():
            raise RuntimeError("Realtime provider session is not active.")
        if self.text_queue:
            return self.text_queue.popleft()
        return "mock realtime response"


# Register Realtime provider
provider_registry.register_realtime_provider("mock", MockRealtimeProvider)
