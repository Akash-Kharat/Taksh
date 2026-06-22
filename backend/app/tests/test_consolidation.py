"""
Unit tests for SessionConsolidator engine.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.database_models import (
    MemoryEvent,
    TextPayload,
    Session as DBSession,
    ProjectMemory,
    ConversationProfile
)
from app.services.conversation.consolidation import SessionConsolidator


def test_session_consolidation(db_session: Session):
    # 1. Setup profile and active project
    project = ProjectMemory(
        project_name="Consolidation test project",
        status="active",
        summary="Testing consolidations"
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    profile = ConversationProfile(
        interaction_count=0,
        active_project_id=project.project_memory_id
    )
    db_session.add(profile)
    db_session.commit()

    # 2. Setup session and text events containing structured triggers
    sess = DBSession(session_id="session-consolidate-main")
    db_session.add(sess)

    ev1 = MemoryEvent(event_id="e1", session_id="session-consolidate-main", primary_modality="text")
    tp1 = TextPayload(event_id="e1", transcript="Goal: Complete Milestone-12 implementation. Next step: Write API tests.")
    ev2 = MemoryEvent(event_id="e2", session_id="session-consolidate-main", primary_modality="text")
    tp2 = TextPayload(event_id="e2", transcript="Milestone MS-12 completed. Decision: Use rule-based parsing for preferences.")
    
    db_session.add_all([ev1, tp1, ev2, tp2])
    db_session.commit()

    # 3. Consolidate session
    res = SessionConsolidator.consolidate_session(db_session, "session-consolidate-main")
    assert res is not None
    assert res["decisions_extracted"] == 1
    assert res["snapshot_generated"]

    # 4. Verify outputs in DB records
    db_session.refresh(project)
    db_session.refresh(profile)

    assert "Complete Milestone-12 implementation" in project.active_goals
    assert "Write API tests" in project.next_steps
    assert project.current_milestone == "MS-12"
    assert profile.interaction_count == 1
