import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database_models import MemoryEpisode, ProjectMemory, ConversationProfile
from app.services.conversation.episodic_memory_service import episodic_memory_service, RecallDecisionEngine, EmbeddingProvider

@pytest.mark.anyio
async def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert EmbeddingProvider.cosine_similarity(v1, v2) == 1.0
    assert EmbeddingProvider.cosine_similarity(v1, v3) == 0.0
    assert EmbeddingProvider.cosine_similarity(v1, [0.0, 0.0]) == 0.0

@pytest.mark.anyio
async def test_recall_decision_engine():
    # Keyword & similarity triggers
    should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
        query="what was our previous topic?",
        similarity_score=0.35
    )
    assert should_recall is True
    assert "keyword match" in reason

    # Continuation request trigger
    should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
        query="continue our ESP32 work",
        similarity_score=0.32
    )
    assert should_recall is True
    assert "continuation request" in reason

    # Project mentions trigger
    should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
        query="tell me about Taksh",
        similarity_score=0.33,
        active_project_name="Taksh"
    )
    assert should_recall is True
    assert "active project reference" in reason

    # High similarity trigger
    should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
        query="completely random query",
        similarity_score=0.45
    )
    assert should_recall is True
    assert "high semantic similarity" in reason

    # Low similarity trigger
    should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
        query="no match here",
        similarity_score=0.20
    )
    assert should_recall is False

@pytest.mark.anyio
async def test_episodic_memory_search_ranking(db_session: Session):
    # Setup two mock episodes with different importance scores
    ep1 = MemoryEpisode(
        session_id="session-s1",
        memory_type="episodic",
        title="ESP32 topic",
        summary="summary of ESP32",
        importance_score=0.5,
        embedding_vector=episodic_memory_service.embedding_provider.generate_embedding("ESP32 topic")
    )
    ep2 = MemoryEpisode(
        session_id="session-s2",
        memory_type="episodic",
        title="ESP32 topic 2",
        summary="summary of ESP32 topic 2",
        importance_score=1.0,
        embedding_vector=episodic_memory_service.embedding_provider.generate_embedding("ESP32 topic 2")
    )
    db_session.add_all([ep1, ep2])
    db_session.commit()

    # Search for "ESP32"
    results = episodic_memory_service.search_episodic_memory(db_session, "ESP32", limit=5)
    assert len(results) == 2
    # The one with higher importance score should be ranked first due to final_score = similarity * importance
    assert results[0][0].id == ep2.id
