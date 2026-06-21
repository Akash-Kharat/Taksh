import pytest
from sqlalchemy.orm import Session as DbSession
from fastapi.testclient import TestClient
from app.services.memory.manager import memory_manager
from app.models.database_models import Session, GoalTracker, LearningHistory, ProjectTracker

def test_sensory_cache_fifo_eviction(db_session: DbSession):
    # Temporarily set max_sensory_events to 3
    actual_max = memory_manager.max_sensory_events
    memory_manager.max_sensory_events = 3
    
    session_id = "test-session-fifo"
    # Ensure clean cache
    if session_id in memory_manager._sensory_cache:
        del memory_manager._sensory_cache[session_id]
        
    # Store parent session
    session = Session(session_id=session_id)
    db_session.add(session)
    db_session.commit()

    # Store 5 events
    for i in range(1, 6):
        memory_manager.store_event(
            db=db_session,
            session_id=session_id,
            primary_modality="text",
            summary=f"Event {i}",
            text_payload={"transcript": f"Transcript {i}"}
        )

    # Assert cache size is capped at 3
    assert memory_manager.get_cache_size(session_id) == 3
    
    # Assert oldest 2 events were evicted (FIFO)
    cached = memory_manager.get_recent_context(session_id, limit=5)
    summaries = [event["summary"] for event in cached]
    assert "Event 1" not in summaries
    assert "Event 2" not in summaries
    assert "Event 3" in summaries
    assert "Event 4" in summaries
    assert "Event 5" in summaries

    # Restore default capacity limit
    memory_manager.max_sensory_events = actual_max

def test_goal_repo_active_filtering(db_session: DbSession):
    # Reset
    db_session.query(GoalTracker).delete()
    db_session.commit()

    # 1. Create active goal
    g1 = GoalTracker(description="Active goal", status="active")
    # 2. Create completed goal
    g2 = GoalTracker(description="Completed goal", status="completed")
    db_session.add(g1)
    db_session.add(g2)
    db_session.commit()

    from app.repositories.goal import goal_repo
    active_goals = goal_repo.get_active(db_session)
    assert len(active_goals) == 1
    assert active_goals[0].description == "Active goal"

def test_memory_endpoints(client: TestClient, db_session: DbSession):
    # Prepare session
    sess = Session(session_id="session-test-endpoints")
    db_session.add(sess)
    
    # Prepare goals
    db_session.query(GoalTracker).delete()
    goal = GoalTracker(description="Goal for endpoints test", status="active")
    db_session.add(goal)
    
    # Prepare lessons and projects
    db_session.query(LearningHistory).delete()
    db_session.query(ProjectTracker).delete()
    lesson = LearningHistory(concept_name="Endpoint master", mastery_score=80)
    project = ProjectTracker(project_name="Endpoint proj", tech_stack=["Python"])
    db_session.add(lesson)
    db_session.add(project)
    db_session.commit()

    # Create event
    memory_manager.store_event(
        db=db_session,
        session_id="session-test-endpoints",
        primary_modality="workspace",
        summary="telemetry update",
        workspace_payload={"active_file": "main.py", "cursor_line": 10}
    )

    # 1. Test GET /api/v1/memory/working
    response = client.get("/api/v1/memory/working?session_id=session-test-endpoints")
    assert response.status_code == 200
    working = response.json()
    assert len(working["active_goals"]) == 1
    assert working["active_goals"][0]["description"] == "Goal for endpoints test"
    assert working["active_context"]["active_file"] == "main.py"

    # 2. Test GET /api/v1/memory/longterm
    response = client.get("/api/v1/memory/longterm")
    assert response.status_code == 200
    longterm = response.json()
    assert len(longterm["lessons"]) == 1
    assert longterm["lessons"][0]["concept_name"] == "Endpoint master"
    assert len(longterm["projects"]) == 1
    assert longterm["projects"][0]["project_name"] == "Endpoint proj"

    # 3. Test GET /api/v1/memory/info
    response = client.get("/api/v1/memory/info")
    assert response.status_code == 200
    info = response.json()
    assert info["active_sessions"] >= 1
    assert info["sensory_cache_sessions"] >= 1

    # 4. Test GET /api/v1/memory/session/{session_id}
    response = client.get("/api/v1/memory/session/session-test-endpoints")
    assert response.status_code == 200
    sess_detail = response.json()
    assert sess_detail["session"]["session_id"] == "session-test-endpoints"
    assert len(sess_detail["events"]) == 1
    assert sess_detail["events"][0]["summary"] == "telemetry update"

def test_session_close_summary_eviction(db_session: DbSession):
    session_id = "session-test-close"
    sess = Session(session_id=session_id)
    db_session.add(sess)
    db_session.commit()

    # Add telemetry event
    memory_manager.store_event(
        db=db_session,
        session_id=session_id,
        primary_modality="text",
        summary="Discussion summary",
        text_payload={"transcript": "hello world"}
    )
    
    # Assert cache exists
    assert memory_manager.get_cache_size(session_id) == 1

    # Close session
    closed_sess = memory_manager.close_session(db_session, session_id)
    assert closed_sess.closed_at is not None
    assert closed_sess.summary is not None
    assert "Total events: 1" in closed_sess.summary
    assert "text" in closed_sess.summary
    
    # Assert cache evicted
    assert memory_manager.get_cache_size(session_id) == 0
