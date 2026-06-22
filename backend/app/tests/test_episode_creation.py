import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database_models import MemoryEpisode, OpenTask, PreferenceMemory, ConversationTurn, ConversationRuntimeSession, Session as MemorySession
from app.services.conversation.coordinator import conversation_coordinator
from app.services.conversation.episodic_memory_service import episodic_memory_service

@pytest.mark.anyio
async def test_episodic_memory_creation_on_stop(db_session: Session):
    # 1. Start session
    runtime_session = await conversation_coordinator.start_conversation(db_session)
    runtime_session_id = runtime_session.runtime_session_id

    # 2. Add some mock conversation turns
    turn = ConversationTurn(
        runtime_session_id=runtime_session_id,
        user_text="We decided to use SPI Mode 3 and FFT needs to be implemented. I prefer using Python.",
        assistant_text="Acknowledged SPI Mode 3. I will make sure we use it.",
        started_at=datetime.utcnow()
    )
    db_session.add(turn)
    db_session.commit()

    # 3. Consolidate session manually to test episodic_memory_service directly
    episode = await episodic_memory_service.consolidate_episodic_memory(db_session, runtime_session_id)
    
    assert episode is not None
    assert episode.session_id == runtime_session_id
    assert episode.memory_type == "episodic"
    assert len(episode.title) > 0
    assert len(episode.summary) > 0
    assert episode.importance_score > 0.0
    assert len(episode.embedding_vector) == 384  # Standard Mock size

    # Verify open tasks are created
    tasks = db_session.query(OpenTask).filter(OpenTask.episode_id == episode.id).all()
    assert len(tasks) > 0
    assert any("FFT" in t.description for t in tasks)

    # Verify user preferences are created
    prefs = db_session.query(PreferenceMemory).filter(PreferenceMemory.source_session_id == runtime_session_id).all()
    assert len(prefs) > 0
