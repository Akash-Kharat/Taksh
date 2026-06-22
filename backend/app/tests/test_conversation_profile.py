"""
Unit tests for ConversationProfile model.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database_models import ConversationProfile


def test_conversation_profile_creation(db_session: Session):
    profile = ConversationProfile(
        interaction_count=5,
        current_focus="Debugging process runner timeouts",
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow()
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.profile_id is not None
    assert profile.interaction_count == 5
    assert profile.current_focus == "Debugging process runner timeouts"
    assert profile.active_project_id is None
