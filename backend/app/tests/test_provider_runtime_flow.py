import pytest
from unittest.mock import patch, AsyncMock
from app.services.runtime.state_machine import RealtimeStateMachine
from app.services.providers.manager import provider_manager
from app.services.providers.factory import provider_factory

@pytest.mark.anyio
async def test_provider_runtime_flow_stt_tts(db_session):
    sm = RealtimeStateMachine("session-flow-id")
    
    # We will configure STT/TTS defaults to "mock"
    with patch('app.core.config.settings.DEFAULT_STT_PROVIDER', "mock"):
        with patch('app.core.config.settings.DEFAULT_TTS_PROVIDER', "mock"):
            # Execute transcription through StateMachine
            transcript = await sm.transcribe(b"test audio bytes", db=db_session)
            assert transcript == "mock transcript"
            
            # Execute synthesis through StateMachine
            audio = await sm.synthesize("test message text", db=db_session)
            assert len(audio) > 0
