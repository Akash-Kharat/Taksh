"""
Unit tests for RelationshipTracker.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database_models import ConversationProfile, ProjectMemory
from app.services.conversation.relationship import RelationshipTracker


def test_relationship_context(db_session: Session):
    # 1. Create two projects with distinct last_updated_at values
    p1 = ProjectMemory(
        project_name="Taksh Project Alpha",
        status="active",
        summary="Summary Alpha",
        last_updated_at=datetime.utcnow() - timedelta(days=5)
    )
    p2 = ProjectMemory(
        project_name="Taksh Project Beta",
        status="inactive",
        summary="Summary Beta",
        last_updated_at=datetime.utcnow() - timedelta(days=10)
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    # 2. Create conversation profile
    profile = ConversationProfile(
        interaction_count=42,
        first_seen_at=datetime.utcnow() - timedelta(days=30),
        last_seen_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(profile)
    db_session.commit()

    # 3. Retrieve context
    ctx = RelationshipTracker.get_relationship_context(db_session)
    
    assert ctx["interaction_count"] == 42
    assert ctx["total_projects"] == 2
    assert ctx["active_project_count"] == 1
    # Longest running project should be Project Beta (oldest last_updated_at)
    assert ctx["longest_running_project"] == "Taksh Project Beta"
    assert ctx["last_active_at"] is not None
