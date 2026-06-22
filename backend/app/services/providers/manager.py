import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
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
        return cls._instance

    def _resolve_sessions(self, runtime_session_id: Optional[str], db: Optional[Session] = None) -> Tuple[Optional[str], Optional[str]]:
        """Resolves (runtime_session_id, voice_session_id) for correlation tracing."""
        if not runtime_session_id:
            return None, None

        # If db is not provided, open a temporary one
        local_db = None
        if not db:
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
        logger.info(f"Routing STT request (runtime_session={rt_id}, voice_session={voice_id})")

        provider = provider_factory.get_stt_provider(provider_name)
        if not provider.is_connected():
            await provider.connect()

        # Execute transcription
        transcript = await provider.transcribe_audio(audio_bytes)
        return transcript

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
        logger.info(f"Routing TTS request (runtime_session={rt_id}, voice_session={voice_id})")

        provider = provider_factory.get_tts_provider(provider_name)
        if not provider.is_connected():
            await provider.connect()

        # Execute voice synthesis
        audio_bytes = await provider.synthesize(text)
        return audio_bytes

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
        logger.info(f"Retrieving Realtime provider (runtime_session={rt_id}, voice_session={voice_id})")

        provider = provider_factory.get_realtime_provider(provider_name)
        return provider


# Global provider manager singleton instance
provider_manager = ProviderManager()
