import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.services.conversation.coordinator import conversation_coordinator
from app.services.conversation.playback import playback_controller
from app.models.database_models import ConversationTurn

@pytest.mark.anyio
async def test_streaming_budget_truncation_segments(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Mock LLM to return many segments
    long_response = ". ".join([f"sentence {i}" for i in range(100)]) + "."
    
    with patch('app.services.llm.manager.LLMManager.generate') as mock_llm:
        from app.services.llm.contracts import LLMResponse
        mock_llm.return_value = LLMResponse(
            status="success",
            content=long_response,
            provider="mock",
            model_name="mock-model",
            latency_ms=10
        )
        
        with patch('app.core.config.settings.MAX_RESPONSE_SEGMENTS', 5):
            with patch('app.services.providers.manager.provider_manager.synthesize_speech', return_value=b"audio") as mock_tts:
                turn = await conversation_coordinator.process_message(
                    db=db_session,
                    runtime_session_id=runtime_session_id,
                    user_text="tell me a long story"
                )

                assert turn.response_truncated is True
                assert turn.segment_count == 5
                assert mock_tts.call_count == 5


@pytest.mark.anyio
async def test_streaming_budget_truncation_chars(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Create a long response segment that exceeds character limits
    long_text = "A very long sentence."
    
    with patch('app.services.llm.manager.LLMManager.generate') as mock_llm:
        from app.services.llm.contracts import LLMResponse
        mock_llm.return_value = LLMResponse(
            status="success",
            content=long_text,
            provider="mock",
            model_name="mock-model",
            latency_ms=10
        )
        
        with patch('app.core.config.settings.MAX_RESPONSE_CHARS', 10):
            with patch('app.services.providers.manager.provider_manager.synthesize_speech', return_value=b"audio") as mock_tts:
                turn = await conversation_coordinator.process_message(
                    db=db_session,
                    runtime_session_id=runtime_session_id,
                    user_text="say hello"
                )

                assert turn.response_truncated is True
                assert turn.segment_count == 0  # Truncated before the first segment accumulated character limit
                assert mock_tts.call_count == 0
