import logging
from app.services.providers.contracts import SpeechToTextProvider, ProviderMetadata, ProviderState
from app.services.providers.registry import provider_registry

logger = logging.getLogger("providers")


class MockSTTProvider(SpeechToTextProvider):
    """Offline mock Speech-To-Text engine for testing and local operations."""

    def __init__(self):
        self._state = ProviderState.DISCONNECTED

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock_stt",
            provider_type="stt",
            version="1.0.0",
            supports_streaming=False,
            supports_interruptions=False,
            supports_audio_input=True,
            supports_audio_output=False,
            supports_text_input=False,
            supports_text_output=True
        )

    def get_state(self) -> ProviderState:
        return self._state

    async def connect(self) -> None:
        self._state = ProviderState.CONNECTING
        logger.info("Mock STT connecting...")
        self._state = ProviderState.CONNECTED
        logger.info("Mock STT connected.")

    async def disconnect(self) -> None:
        logger.info("Mock STT disconnecting...")
        self._state = ProviderState.DISCONNECTED
        logger.info("Mock STT disconnected.")

    def is_connected(self) -> bool:
        return self._state == ProviderState.CONNECTED

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        if not self.is_connected():
            raise RuntimeError("STT provider is not connected.")
        logger.info(f"Mock STT transcribing {len(audio_bytes)} bytes of audio.")
        return "mock transcript"


# Register STT provider
provider_registry.register_stt_provider("mock", MockSTTProvider)
