import logging
import collections
from app.core.config import settings
from app.services.providers.contracts import RealtimeConversationProvider, ProviderMetadata, ProviderState
from app.services.providers.registry import provider_registry

logger = logging.getLogger("providers")


class OpenAIRealtimeProvider(RealtimeConversationProvider):
    """Skeleton adapter for OpenAI Realtime conversation provider."""

    def __init__(self):
        self._state = ProviderState.DISCONNECTED
        self.audio_queue = collections.deque()
        self.text_queue = collections.deque()
        self.dropped_messages = 0

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="openai_realtime",
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
        logger.info("OpenAI Realtime connecting (skeleton)...")
        self._state = ProviderState.CONNECTED
        logger.info("OpenAI Realtime connected (skeleton).")

    async def disconnect(self) -> None:
        logger.info("OpenAI Realtime disconnecting...")
        self._state = ProviderState.DISCONNECTED
        logger.info("OpenAI Realtime disconnected.")

    def is_connected(self) -> bool:
        return self._state == ProviderState.CONNECTED

    async def start_session(self) -> None:
        if not self.is_connected():
            raise RuntimeError("OpenAI Realtime connection is not active.")
        logger.info("Starting OpenAI Realtime session (skeleton)...")
        self.audio_queue.clear()
        self.text_queue.clear()
        self.dropped_messages = 0

    async def end_session(self) -> None:
        logger.info("Ending OpenAI Realtime session (skeleton).")
        self.audio_queue.clear()
        self.text_queue.clear()

    def _enqueue(self, queue: collections.deque, item: any) -> None:
        """Helper to enqueue items while enforcing MAX_PROVIDER_QUEUE_SIZE budget."""
        if len(queue) >= settings.MAX_PROVIDER_QUEUE_SIZE:
            queue.popleft()
            self.dropped_messages += 1
            logger.warning(
                f"OpenAI Realtime queue limit reached. Dropped oldest message. Total dropped: {self.dropped_messages}"
            )
        queue.append(item)

    async def send_audio(self, audio_data: bytes) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        logger.info(f"OpenAI Realtime skeleton received {len(audio_data)} bytes of audio.")
        self._enqueue(self.audio_queue, audio_data)

    async def receive_audio(self) -> bytes:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        raise NotImplementedError("Realtime audio streaming via OpenAI Realtime is not implemented in MS-15.")

    async def send_text(self, text: str) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        logger.info(f"OpenAI Realtime skeleton received text: '{text}'")
        self._enqueue(self.text_queue, text)

    async def receive_text(self) -> str:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        raise NotImplementedError("Realtime text streaming via OpenAI Realtime is not implemented in MS-15.")


# Register OpenAI Realtime provider
provider_registry.register_realtime_provider("openai_realtime", OpenAIRealtimeProvider)
