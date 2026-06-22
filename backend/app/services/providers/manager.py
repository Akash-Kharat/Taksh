import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.database_models import ConversationRuntimeSession
from app.services.providers.factory import provider_factory
from app.services.providers.contracts import SpeechToTextProvider, TextToSpeechProvider, RealtimeConversationProvider

logger = logging.getLogger("providers")


class ProviderManager:
    """
    Unified entrypoint and boundary managing provider interactions,
    session correlations, and routing for the Runtime layer.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProviderManager, cls).__new__(cls)
            cls._instance.consecutive_failures = 0
            cls._instance.fallback_active = False
            cls._instance.failure_count = 0
            cls._instance.reconnect_count = 0
            cls._instance.last_error = None
        return cls._instance

    def record_reconnect(self) -> None:
        """Increments the reconnect attempts counter."""
        self.reconnect_count += 1

    def record_failure(self, error: Exception) -> None:
        """Records a provider failure and triggers fallback if failure threshold is reached."""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_error = str(error)
        logger.warning(f"Provider failure recorded. Consecutive failure count: {self.consecutive_failures}/{settings.PROVIDER_FAILURE_THRESHOLD}. Error: {error}")
        if self.consecutive_failures >= settings.PROVIDER_FAILURE_THRESHOLD:
            self.fallback_active = True
            logger.error("Provider circuit breaker triggered. Fallback active (routing all queries to offline mock).")

    def reset_failures(self) -> None:
        """Resets the consecutive failures counter on successful operations."""
        self.consecutive_failures = 0

    def _get_provider_name(self, name_param: Optional[str], default_setting: str) -> str:
        """Determines the provider name, routing to mock if circuit breaker fallback is active."""
        if name_param:
            return name_param
        if self.fallback_active and settings.ENABLE_PROVIDER_FALLBACK:
            return "mock"
        return default_setting

    def _resolve_sessions(self, runtime_session_id: Optional[str], db: Optional[Session] = None) -> Tuple[Optional[str], Optional[str]]:
        """Resolves (runtime_session_id, voice_session_id) for correlation tracing."""
        if not runtime_session_id:
            return None, None

        local_db = None
        if not db:
            from app.core.database import SessionLocal
            local_db = SessionLocal()
            db = local_db

        try:
            session_rec = db.query(ConversationRuntimeSession).filter(
                ConversationRuntimeSession.runtime_session_id == runtime_session_id
            ).first()
            if session_rec:
                return runtime_session_id, session_rec.voice_session_id
        except Exception as e:
            logger.warning(f"Failed to resolve session correlation: {e}")
        finally:
            if local_db:
                local_db.close()

        return runtime_session_id, None

    async def transcribe_audio(
        self,
        runtime_session_id: str,
        audio_bytes: bytes,
        provider_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> str:
        """
        Routes audio transcription request to active STT provider.
        Tracks session correlation for debugging.
        """
        rt_id, voice_id = self._resolve_sessions(runtime_session_id, db)
        resolved_name = self._get_provider_name(provider_name, settings.DEFAULT_STT_PROVIDER)
        logger.info(f"Routing STT request to {resolved_name} (runtime_session={rt_id}, voice_session={voice_id})")

        try:
            provider = provider_factory.get_stt_provider(resolved_name)
            if not provider.is_connected():
                await provider.connect()

            transcript = await provider.transcribe_audio(audio_bytes)
            self.reset_failures()
            return transcript
        except Exception as e:
            self.record_failure(e)
            raise e

    async def synthesize_speech(
        self,
        runtime_session_id: str,
        text: str,
        provider_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bytes:
        """
        Routes speech synthesis request to active TTS provider.
        Tracks session correlation for debugging.
        """
        rt_id, voice_id = self._resolve_sessions(runtime_session_id, db)
        resolved_name = self._get_provider_name(provider_name, settings.DEFAULT_TTS_PROVIDER)
        logger.info(f"Routing TTS request to {resolved_name} (runtime_session={rt_id}, voice_session={voice_id})")

        try:
            provider = provider_factory.get_tts_provider(resolved_name)
            if not provider.is_connected():
                await provider.connect()

            audio_bytes = await provider.synthesize(text)
            self.reset_failures()
            return audio_bytes
        except Exception as e:
            self.record_failure(e)
            raise e

    async def get_realtime_provider(
        self,
        runtime_session_id: str,
        provider_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> RealtimeConversationProvider:
        """
        Retrieves active realtime conversation provider instance.
        Tracks session correlation for debugging.
        """
        rt_id, voice_id = self._resolve_sessions(runtime_session_id, db)
        resolved_name = self._get_provider_name(provider_name, settings.DEFAULT_REALTIME_PROVIDER)
        logger.info(f"Retrieving Realtime provider {resolved_name} (runtime_session={rt_id}, voice_session={voice_id})")

        try:
            provider = provider_factory.get_realtime_provider(resolved_name)
            return provider
        except Exception as e:
            self.record_failure(e)
            raise e

    async def interrupt_session(
        self,
        runtime_session_id: str,
        provider_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> None:
        """Signals active provider to stop generation and records the interruption telemetry."""
        rt_id, voice_id = self._resolve_sessions(runtime_session_id, db)
        resolved_name = self._get_provider_name(provider_name, settings.DEFAULT_REALTIME_PROVIDER)
        logger.info(f"Interrupting Realtime provider {resolved_name} (runtime_session={rt_id}, voice_session={voice_id})")

        try:
            provider = provider_factory.get_realtime_provider(resolved_name)
            if hasattr(provider, "interrupt"):
                import inspect
                sig = inspect.signature(provider.interrupt)
                if "db" in sig.parameters:
                    await provider.interrupt(db=db)
                else:
                    await provider.interrupt()
        except Exception as e:
            self.record_failure(e)
            raise e


# Global provider manager singleton instance
provider_manager = ProviderManager()
