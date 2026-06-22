import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database_models import MemoryEpisode, MemoryRecall
from app.services.conversation.coordinator import conversation_coordinator
from app.services.conversation.episodic_memory_service import episodic_memory_service
from app.services.cognitive.context import ContextBuilder
from app.services.cognitive.prompt import PromptBuilder

@pytest.mark.anyio
async def test_memory_recall_flow_and_decay(db_session: Session):
    # 1. Start session
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # 2. Add an episode to the database
    ep = MemoryEpisode(
        session_id="past-session-id",
        memory_type="episodic",
        title="Predictive maintenance FFT discussion",
        summary="We discussed FFT algorithms for ADXL345 on ESP32",
        importance_score=0.8,
        embedding_vector=episodic_memory_service.embedding_provider.generate_embedding("FFT ADXL345 ESP32")
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)

    initial_recall_count = ep.recall_count
    initial_access_time = ep.last_accessed_at

    # 3. Retrieve relevant memories for query "continue our predictive maintenance discussion"
    mems = episodic_memory_service.retrieve_relevant_memories(
        db=db_session,
        query="continue our predictive maintenance discussion",
        session_id=runtime_session_id,
        limit=5
    )

    assert len(mems) > 0
    assert mems[0]["id"] == ep.id

    # Check decay metadata updated
    db_session.refresh(ep)
    assert ep.recall_count == initial_recall_count + 1
    assert ep.last_accessed_at > initial_access_time

    # Check MemoryRecall log was persisted
    recalls = db_session.query(MemoryRecall).filter(MemoryRecall.session_id == runtime_session_id).all()
    assert len(recalls) == 1
    assert recalls[0].episode_id == ep.id
    assert recalls[0].similarity_score > 0.0
    assert len(recalls[0].retrieval_reason) > 0

    # 4. Check prompt injection in ContextBuilder/PromptBuilder
    cb = ContextBuilder()
    context = cb.build_context(db_session, "continue our predictive maintenance discussion", selected_skills=[], session_id=runtime_session_id)
    
    assert "episodic_memories" in context
    assert len(context["episodic_memories"]) > 0
    assert context["episodic_memories"][0]["id"] == ep.id

    pb = PromptBuilder()
    prompt_package = pb.build_prompt_package("continue our predictive maintenance discussion", context)
    user_prompt = prompt_package["user_prompt"]

    assert "=== RECALLED PRIOR CONVERSATIONS (EPISODIC MEMORY) ===" in user_prompt
    assert "Topic: Predictive maintenance FFT discussion" in user_prompt
    assert "Summary: We discussed FFT algorithms for ADXL345 on ESP32" in user_prompt
