"""
Unit tests for ProjectSnapshot creation rules.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.database_models import ProjectMemory, ProjectSnapshot, MemoryEvent, TextPayload, Session as DBSession
from app.services.conversation.consolidation import SessionConsolidator


def test_snapshot_creation_rules(db_session: Session):
    # 1. Setup session and project
    session_rec = DBSession(session_id="session-snap-test")
    project_rec = ProjectMemory(
        project_name="Snap test project",
        status="active",
        summary="Test snap"
    )
    db_session.add_all([session_rec, project_rec])
    db_session.commit()
    db_session.refresh(project_rec)

    # A. Test session closure with NO snapshot triggers (normal closure)
    ev1 = MemoryEvent(event_id="e1", session_id="session-snap-test", primary_modality="text")
    tp1 = TextPayload(event_id="e1", transcript="We did some basic code work today.")
    db_session.add_all([ev1, tp1])
    db_session.commit()

    # Consolidate session
    res = SessionConsolidator.consolidate_session(db_session, "session-snap-test")
    assert res is not None
    assert not res["snapshot_generated"]

    # Verify no snapshots are created
    snap_count = db_session.query(ProjectSnapshot).count()
    assert snap_count == 0

    # B. Test session closure WITH ADR (accepted architectural decision)
    session_rec2 = DBSession(session_id="session-snap-test-2")
    db_session.add(session_rec2)
    ev2 = MemoryEvent(event_id="e2", session_id="session-snap-test-2", primary_modality="text")
    tp2 = TextPayload(event_id="e2", transcript="ADR: Implemented ProcessRunner for sandboxed task execution.")
    db_session.add_all([ev2, tp2])
    db_session.commit()

    res2 = SessionConsolidator.consolidate_session(db_session, "session-snap-test-2")
    assert res2 is not None
    assert res2["decisions_extracted"] == 1
    assert res2["snapshot_generated"]

    # Verify snapshot was created
    snap_count = db_session.query(ProjectSnapshot).count()
    assert snap_count == 1
    snap = db_session.query(ProjectSnapshot).first()
    assert snap.project_name == project_rec.project_name
    assert "Implemented ProcessRunner" in snap.decisions[0]
