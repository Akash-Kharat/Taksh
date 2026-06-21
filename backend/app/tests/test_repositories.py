import pytest
from datetime import datetime
from sqlalchemy.orm import Session as DbSession
from app.models.database_models import Session, MemoryEvent, TextPayload, AudioPayload, WorkspacePayload, ProjectTracker, GoalTracker, LearningHistory
from app.repositories.session import session_repo
from app.repositories.memory import memory_repo
from app.repositories.project import project_repo
from app.repositories.goal import goal_repo
from app.repositories.learning import learning_repo

def test_session_repository_crud(db_session: DbSession):
    # Create
    sess = Session(closed_at=None)
    created = session_repo.create(db_session, sess)
    assert created.session_id is not None
    assert created.closed_at is None
    
    # Read
    fetched = session_repo.get(db_session, created.session_id)
    assert fetched is not None
    assert fetched.session_id == created.session_id
    
    # Update
    updated = session_repo.update(db_session, fetched, {"closed_at": datetime.utcnow()})
    assert updated.closed_at is not None
    
    # List
    all_sess = session_repo.get_multi(db_session)
    assert len(all_sess) >= 1
    
    # Delete (Physical)
    session_repo.delete(db_session, created.session_id)
    assert session_repo.get(db_session, created.session_id) is None

def test_memory_repository_crud(db_session: DbSession):
    # Create parent session
    sess = Session()
    session_repo.create(db_session, sess)
    
    # Create MemoryEvent
    event = MemoryEvent(
        session_id=sess.session_id,
        primary_modality="text",
        summary="A test memory event summary"
    )
    # Attach payload
    event.text_payload = TextPayload(transcript="Test transcript", system_prompt_injected="System prompt")
    
    created = memory_repo.create(db_session, event)
    assert created.event_id is not None
    assert created.text_payload is not None
    assert created.text_payload.transcript == "Test transcript"
    
    # Get by session
    events_in_session = memory_repo.get_by_session(db_session, sess.session_id)
    assert len(events_in_session) == 1
    assert events_in_session[0].event_id == created.event_id
    
    # Delete (Physical)
    memory_repo.delete(db_session, created.event_id)
    assert memory_repo.get(db_session, created.event_id) is None
    # Text payload should be cascade deleted
    assert db_session.query(TextPayload).filter_by(event_id=created.event_id).first() is None

def test_project_repository_crud(db_session: DbSession):
    project = ProjectTracker(
        project_name="Taksh Project",
        tech_stack=["FastAPI", "SQLite", "SQLAlchemy"],
        historical_adr_keys=["adr-001", "adr-002"]
    )
    created = project_repo.create(db_session, project)
    assert created.project_id is not None
    assert created.tech_stack == ["FastAPI", "SQLite", "SQLAlchemy"]
    
    # Update tech stack
    updated = project_repo.update(db_session, created, {"tech_stack": ["FastAPI", "SQLite"]})
    assert updated.tech_stack == ["FastAPI", "SQLite"]
    
    # Delete
    project_repo.delete(db_session, created.project_id)
    assert project_repo.get(db_session, created.project_id) is None

def test_goal_repository_crud(db_session: DbSession):
    goal = GoalTracker(
        description="Implement persistence layer",
        status="active"
    )
    created = goal_repo.create(db_session, goal)
    assert created.goal_id is not None
    assert created.status == "active"
    
    # Update status
    updated = goal_repo.update(db_session, created, {"status": "completed"})
    assert updated.status == "completed"
    
    # Delete
    goal_repo.delete(db_session, created.goal_id)
    assert goal_repo.get(db_session, created.goal_id) is None

def test_learning_repository_crud(db_session: DbSession):
    learning = LearningHistory(
        concept_name="SQLAlchemy 2.0 Mapped",
        mastery_score=85
    )
    created = learning_repo.create(db_session, learning)
    assert created.concept_id is not None
    assert created.mastery_score == 85
    
    # Update mastery score
    updated = learning_repo.update(db_session, created, {"mastery_score": 95})
    assert updated.mastery_score == 95
    
    # Delete
    learning_repo.delete(db_session, created.concept_id)
    assert learning_repo.get(db_session, created.concept_id) is None
