import logging
from app.services.providers.contracts import TextToSpeechProvider, ProviderMetadata, ProviderState
from app.services.providers.registry import provider_registry

logger = logging.getLogger("providers")


class MockTTSProvider(TextToSpeechProvider):
    """Offline mock Text-To-Speech engine for testing and local operations."""

    def __init__(self):
        self._state = ProviderState.DISCONNECTED

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock_tts",
            provider_type="tts",
            version="1.0.0",
            supports_streaming=False,
            supports_interruptions=False,
            supports_audio_input=False,
            supports_audio_output=True,
            supports_text_input=True,
            supports_text_output=False
        )

    def get_state(self) -> ProviderState:
        return self._state

    async def connect(self) -> None:
        self._state = ProviderState.CONNECTING
        logger.info("Mock TTS connecting...")
        self._state = ProviderState.CONNECTED
        logger.info("Mock TTS connected.")

    async def disconnect(self) -> None:
        logger.info("Mock TTS disconnecting...")
        self._state = ProviderState.DISCONNECTED
        logger.info("Mock TTS disconnected.")

    def is_connected(self) -> bool:
        return self._state == ProviderState.CONNECTED

    async def synthesize(self, text: str) -> bytes:
        if not self.is_connected():
            raise RuntimeError("TTS provider is not connected.")
        logger.info(f"Mock TTS synthesizing text: '{text}'")
        # Return 100 bytes of dummy PCM audio data
        return b"\x00" * 100


# Register TTS provider
provider_registry.register_tts_provider("mock", MockTTSProvider)
