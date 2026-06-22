import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.services.conversation.coordinator import conversation_coordinator
from app.models.database_models import ConversationRuntimeSession

@pytest.mark.anyio
async def test_stt_failure_recovery(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Mock STT to fail/raise Exception
    with patch('app.services.providers.manager.provider_manager.transcribe_audio', side_effect=Exception("STT Connection Lost")):
        with patch('app.services.providers.manager.provider_manager.synthesize_speech', return_value=b"audio"):
            # Process voice message
            turn = await conversation_coordinator.process_message(
                db=db_session,
                runtime_session_id=runtime_session_id,
                audio_bytes=b"invalid voice bytes"
            )

            # Session should remain active (Revision 6)
            db_session.refresh(runtime_session)
            assert runtime_session.conversation_session_state == "active"
            assert conversation_coordinator.provider_fallbacks[runtime_session_id] >= 1
            assert turn.user_text == "STT Error fallback text"


@pytest.mark.anyio
async def test_tts_failure_recovery(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Mock TTS to fail
    with patch('app.services.providers.manager.provider_manager.synthesize_speech', side_effect=Exception("TTS Failed")):
        # Process message
        turn = await conversation_coordinator.process_message(
            db=db_session,
            runtime_session_id=runtime_session_id,
            user_text="hello bot"
        )

        # Session should remain active
        db_session.refresh(runtime_session)
        assert runtime_session.conversation_session_state == "active"
        assert conversation_coordinator.provider_fallbacks[runtime_session_id] >= 1
        assert turn.assistant_text is not None
