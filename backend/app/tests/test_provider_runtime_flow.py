import pytest
from unittest.mock import patch, AsyncMock
from app.services.runtime.state_machine import RealtimeStateMachine
from app.services.providers.manager import provider_manager
from app.services.providers.factory import provider_factory

@pytest.mark.anyio
async def test_provider_runtime_flow_stt_tts(db_session):
    # We will configure STT/TTS defaults to "mock"
    with patch('app.core.config.settings.DEFAULT_STT_PROVIDER', "mock"):
        with patch('app.core.config.settings.DEFAULT_TTS_PROVIDER', "mock"):
            # Execute transcription through ProviderManager
            transcript = await provider_manager.transcribe_audio(
                runtime_session_id="session-flow-id",
                audio_bytes=b"test audio bytes",
                db=db_session
            )
            assert transcript == "mock transcript"
            
            # Execute synthesis through ProviderManager
            audio = await provider_manager.synthesize_speech(
                runtime_session_id="session-flow-id",
                text="test message text",
                db=db_session
            )
            assert len(audio) > 0
