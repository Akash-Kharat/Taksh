"""
Unit tests for ProjectMemory and Active Project Policy.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.database_models import ProjectMemory, ConversationProfile
from app.services.conversation.consolidation import SessionConsolidator


def test_active_project_policy(db_session: Session):
    # 1. Create two projects
    p1 = ProjectMemory(
        project_name="Taksh core API",
        status="inactive",
        summary="Taksh Backend"
    )
    p2 = ProjectMemory(
        project_name="Taksh web front",
        status="inactive",
        summary="Taksh React Client"
    )
    db_session.add_all([p1, p2])
    db_session.commit()
    db_session.refresh(p1)
    db_session.refresh(p2)

    # 2. Create conversation profile
    profile = ConversationProfile(
        interaction_count=0
    )
    db_session.add(profile)
    db_session.commit()

    # 3. Activate project 1
    SessionConsolidator.activate_project(db_session, p1.project_memory_id)

    db_session.refresh(p1)
    db_session.refresh(p2)
    db_session.refresh(profile)

    assert p1.status == "active"
    assert p2.status == "inactive"
    assert profile.active_project_id == p1.project_memory_id

    # 4. Activate project 2 (should deactivate project 1)
    SessionConsolidator.activate_project(db_session, p2.project_memory_id)

    db_session.refresh(p1)
    db_session.refresh(p2)
    db_session.refresh(profile)

    assert p1.status == "inactive"
    assert p2.status == "active"
    assert profile.active_project_id == p2.project_memory_id
