import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session
from app.services.conversation.coordinator import conversation_coordinator
from app.models.database_models import ConversationTurn, CognitiveTrace, AIResponse, ConversationRuntimeSession
from app.services.cognitive.context import ContextBuilder
from app.services.cognitive.prompt import PromptBuilder

@pytest.mark.anyio
async def test_conversation_pipeline_message_flow(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Mock provider manager transcribe and synthesize methods
    with patch('app.services.providers.manager.provider_manager.transcribe_audio', return_value="user speech") as mock_stt:
        with patch('app.services.providers.manager.provider_manager.synthesize_speech', return_value=b"audio data") as mock_tts:
            
            # Message injection
            turn = await conversation_coordinator.process_message(
                db=db_session,
                runtime_session_id=runtime_session_id,
                user_text="hello bot"
            )

            assert turn is not None
            assert turn.user_text == "hello bot"
            assert turn.assistant_text is not None
            assert turn.cognitive_trace_id is not None
            assert turn.ai_response_id is not None

            # Verify database relationships
            trace_rec = db_session.query(CognitiveTrace).filter(
                CognitiveTrace.trace_id == turn.cognitive_trace_id
            ).first()
            assert trace_rec is not None
            assert trace_rec.query == "hello bot"

            ai_resp = db_session.query(AIResponse).filter(
                AIResponse.response_id == turn.ai_response_id
            ).first()
            assert ai_resp is not None
            assert ai_resp.content == turn.assistant_text


@pytest.mark.anyio
async def test_context_builder_includes_turns(db_session: Session):
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # Insert 2 conversation turns with distinct started_at times to avoid SQLite sorting ambiguity
    from datetime import datetime, timedelta
    base_time = datetime.utcnow()
    turn1 = ConversationTurn(
        runtime_session_id=runtime_session_id,
        user_text="Turn 1 user",
        assistant_text="Turn 1 assistant",
        latency_ms=100.0,
        started_at=base_time - timedelta(seconds=10)
    )
    turn2 = ConversationTurn(
        runtime_session_id=runtime_session_id,
        user_text="Turn 2 user",
        assistant_text="Turn 2 assistant",
        latency_ms=200.0,
        started_at=base_time - timedelta(seconds=5)
    )
    db_session.add_all([turn1, turn2])
    db_session.commit()

    # Build context
    cb = ContextBuilder()
    context = cb.build_context(db_session, "next query", selected_skills=[], session_id=runtime_session_id)
    
    assert "conversation_turns" in context
    assert len(context["conversation_turns"]) == 2
    assert context["conversation_turns"][0]["user_text"] == "Turn 1 user"
    assert context["conversation_turns"][1]["user_text"] == "Turn 2 user"

    # Build prompt and check history is formatted
    pb = PromptBuilder()
    prompt_package = pb.build_prompt_package("next query", context)
    
    user_prompt = prompt_package["user_prompt"]
    assert "=== CONVERSATION HISTORY ===" in user_prompt
    assert "User: Turn 1 user" in user_prompt
    assert "Assistant: Turn 1 assistant" in user_prompt
