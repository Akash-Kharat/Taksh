import logging
from typing import Dict, Type, List
from app.services.providers.contracts import SpeechToTextProvider, TextToSpeechProvider, RealtimeConversationProvider

logger = logging.getLogger("providers")


class ProviderRegistry:
    """Central registry of all Speech-To-Text, Text-To-Speech, and Realtime AI providers."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProviderRegistry, cls).__new__(cls)
            cls._instance._stt_providers = {}
            cls._instance._tts_providers = {}
            cls._instance._realtime_providers = {}
        return cls._instance

    def register_stt_provider(self, name: str, provider_cls: Type[SpeechToTextProvider]) -> None:
        """Registers a Speech-To-Text provider class."""
        self._stt_providers[name] = provider_cls
        logger.info(f"Registered Speech-To-Text provider: {name}")

    def register_tts_provider(self, name: str, provider_cls: Type[TextToSpeechProvider]) -> None:
        """Registers a Text-To-Speech provider class."""
        self._tts_providers[name] = provider_cls
        logger.info(f"Registered Text-To-Speech provider: {name}")

    def register_realtime_provider(self, name: str, provider_cls: Type[RealtimeConversationProvider]) -> None:
        """Registers a Realtime Conversation provider class."""
        self._realtime_providers[name] = provider_cls
        logger.info(f"Registered Realtime Conversation provider: {name}")

    def get_stt_provider_class(self, name: str) -> Type[SpeechToTextProvider]:
        """Resolves an STT provider class by its registered key."""
        if name not in self._stt_providers:
            raise KeyError(f"Speech-To-Text provider '{name}' is not registered.")
        return self._stt_providers[name]

    def get_tts_provider_class(self, name: str) -> Type[TextToSpeechProvider]:
        """Resolves a TTS provider class by its registered key."""
        if name not in self._tts_providers:
            raise KeyError(f"Text-To-Speech provider '{name}' is not registered.")
        return self._tts_providers[name]

    def get_realtime_provider_class(self, name: str) -> Type[RealtimeConversationProvider]:
        """Resolves a Realtime Conversation provider class by its registered key."""
        if name not in self._realtime_providers:
            raise KeyError(f"Realtime Conversation provider '{name}' is not registered.")
        return self._realtime_providers[name]

    def list_stt_providers(self) -> List[str]:
        """Returns the list of registered STT provider names."""
        return list(self._stt_providers.keys())

    def list_tts_providers(self) -> List[str]:
        """Returns the list of registered TTS provider names."""
        return list(self._tts_providers.keys())

    def list_realtime_providers(self) -> List[str]:
        """Returns the list of registered Realtime provider names."""
        return list(self._realtime_providers.keys())


# Global registry singleton instance
provider_registry = ProviderRegistry()
