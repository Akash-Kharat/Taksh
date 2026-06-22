import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database_models import MemoryEpisode, OpenTask
from app.services.conversation.episodic_memory_service import episodic_memory_service

@pytest.mark.anyio
async def test_open_task_creation_and_completion(db_session: Session):
    # 1. Create a mock episode
    episode = MemoryEpisode(
        session_id="session-task-id",
        memory_type="episodic",
        title="ESP32 tasks",
        summary="ESP32 session summary",
        embedding_vector=[0.1] * 384
    )
    db_session.add(episode)
    db_session.flush()

    # 2. Add tasks manually to simulate consolidation extraction
    t1 = OpenTask(
        episode_id=episode.id,
        description="Implement FFT",
        status="OPEN"
    )
    t2 = OpenTask(
        episode_id=episode.id,
        description="Integrate DS18B20",
        status="OPEN"
    )
    db_session.add_all([t1, t2])
    db_session.commit()
    db_session.refresh(t1)
    db_session.refresh(t2)

    assert t1.status == "OPEN"
    assert t1.resolved_at is None

    # 3. Update task status to DONE
    updated_t1 = episodic_memory_service.update_task_status(db_session, t1.id, "DONE")
    
    assert updated_t1 is not None
    assert updated_t1.status == "DONE"
    assert updated_t1.resolved_at is not None
    assert isinstance(updated_t1.resolved_at, datetime)

    # 4. Check active open tasks query
    tasks = db_session.query(OpenTask).filter(OpenTask.status.in_(["OPEN", "IN_PROGRESS"])).all()
    assert len(tasks) == 1
    assert tasks[0].id == t2.id
