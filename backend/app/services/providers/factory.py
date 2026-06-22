import logging
from typing import Dict
from app.core.config import settings
from app.services.providers.registry import provider_registry
from app.services.providers.contracts import SpeechToTextProvider, TextToSpeechProvider, RealtimeConversationProvider

logger = logging.getLogger("providers")


class ProviderFactory:
    """Factory responsible for instantiating and caching singleton provider instances."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProviderFactory, cls).__new__(cls)
            cls._instance._stt_instances = {}
            cls._instance._tts_instances = {}
            cls._instance._realtime_instances = {}
        return cls._instance

    def get_stt_provider(self, name: str = None) -> SpeechToTextProvider:
        """Retrieves or instantiates a singleton STT provider instance by name."""
        if not name:
            name = settings.DEFAULT_STT_PROVIDER

        if name not in self._stt_instances:
            logger.info(f"Instantiating new Speech-To-Text provider: {name}")
            provider_cls = provider_registry.get_stt_provider_class(name)
            self._stt_instances[name] = provider_cls()
        return self._stt_instances[name]

    def get_tts_provider(self, name: str = None) -> TextToSpeechProvider:
        """Retrieves or instantiates a singleton TTS provider instance by name."""
        if not name:
            name = settings.DEFAULT_TTS_PROVIDER

        if name not in self._tts_instances:
            logger.info(f"Instantiating new Text-To-Speech provider: {name}")
            provider_cls = provider_registry.get_tts_provider_class(name)
            self._tts_instances[name] = provider_cls()
        return self._tts_instances[name]

    def get_realtime_provider(self, name: str = None) -> RealtimeConversationProvider:
        """Retrieves or instantiates a singleton Realtime Conversation provider instance by name."""
        if not name:
            name = settings.DEFAULT_REALTIME_PROVIDER

        if name not in self._realtime_instances:
            logger.info(f"Instantiating new Realtime Conversation provider: {name}")
            provider_cls = provider_registry.get_realtime_provider_class(name)
            self._realtime_instances[name] = provider_cls()
        return self._realtime_instances[name]

    def clear_cache(self) -> None:
        """Clears all cached singleton instances."""
        self._stt_instances.clear()
        self._tts_instances.clear()
        self._realtime_instances.clear()
        logger.info("Cleared all provider instances from factory cache.")


# Global factory singleton instance
provider_factory = ProviderFactory()
