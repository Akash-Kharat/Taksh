import pytest
from unittest.mock import patch, MagicMock
from app.services.runtime.state_machine import RealtimeStateMachine
from app.services.providers.manager import provider_manager

@pytest.mark.anyio
async def test_runtime_state_machine_delegates_to_provider_manager(db_session):
    # 1. Instantiate state machine for a session
    sm = RealtimeStateMachine("test-session-id")

    # 2. Test transcribe delegation
    with patch('app.services.providers.manager.provider_manager.transcribe_audio', return_value="transcribed text") as mock_transcribe:
        transcript = await sm.transcribe(b"test audio bytes", db=db_session)
        assert transcript == "transcribed text"
        mock_transcribe.assert_called_once_with(
            runtime_session_id="test-session-id",
            audio_bytes=b"test audio bytes",
            provider_name=None,
            db=db_session
        )

    # 3. Test synthesize delegation
    with patch('app.services.providers.manager.provider_manager.synthesize_speech', return_value=b"synthesized audio") as mock_synthesize:
        audio = await sm.synthesize("test text", db=db_session)
        assert audio == b"synthesized audio"
        mock_synthesize.assert_called_once_with(
            runtime_session_id="test-session-id",
            text="test text",
            provider_name=None,
            db=db_session
        )

    # 4. Test get_realtime_provider delegation
    mock_rt_provider = MagicMock()
    with patch('app.services.providers.manager.provider_manager.get_realtime_provider', return_value=mock_rt_provider) as mock_get_rt:
        provider = await sm.get_realtime_provider(db=db_session)
        assert provider is mock_rt_provider
        mock_get_rt.assert_called_once_with(
            runtime_session_id="test-session-id",
            provider_name=None,
            db=db_session
        )
