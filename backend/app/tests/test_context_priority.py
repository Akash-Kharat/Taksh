"""
Integration tests for ContextBuilder budgets and priorities.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database_models import ConversationProfile, ProjectMemory, PreferenceMemory, ProjectSnapshot
from app.services.cognitive.context import ContextBuilder


def test_context_builder_budgets(db_session: Session):
    # 1. Setup profile and active project
    p = ProjectMemory(
        project_name="Budget project",
        status="active",
        summary="A budget testing project"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    prof = ConversationProfile(
        interaction_count=1,
        active_project_id=p.project_memory_id
    )
    db_session.add(prof)

    # 2. Add excess preferences (limit = 10, let's add 12)
    # We assign distinct confidence scores to verify ordering
    for i in range(12):
        pref = PreferenceMemory(
            category="workflow",
            value=f"Preference number {i}",
            confidence_score=0.1 + (i * 0.05)  # Range: 0.1 to 0.7
        )
        db_session.add(pref)

    # 3. Add excess snapshots (limit = 3, let's add 5)
    for i in range(5):
        snap = ProjectSnapshot(
            project_name="Budget project",
            milestone=f"MS-{i}",
            summary=f"Snapshot summary {i}",
            decisions=[],
            open_questions=[],
            next_steps=[],
            created_at=datetime.utcnow() + timedelta(seconds=i)
        )
        db_session.add(snap)

    db_session.commit()

    # 4. Build context
    cb = ContextBuilder()
    context = cb.build_context(
        db=db_session,
        query="Run test suite",
        selected_skills=[]
    )

    # 5. Assert budget limitations
    assert "active_project" in context
    assert context["active_project"]["project_name"] == "Budget project"

    # Snapshots limit = 3
    assert "project_snapshots" in context
    assert len(context["project_snapshots"]) == settings.MAX_PROJECT_SNAPSHOTS
    # Assert sorted newest first (ordered by created_at desc)
    # MS-4, MS-3, MS-2
    milestones = [s["milestone"] for s in context["project_snapshots"]]
    assert "MS-4" in milestones
    assert "MS-0" not in milestones  # oldest should be discarded

    # Preferences limit = 10
    assert "preferences" in context
    assert len(context["preferences"]) == settings.MAX_PREFERENCES
    # Assert sorted highest confidence first
    scores = [p["confidence_score"] for p in context["preferences"]]
    assert scores == sorted(scores, reverse=True)
    # The lowest confidence score should be excluded (preference number 0 had 0.1)
    pref_values = [p["value"] for p in context["preferences"]]
    assert "Preference number 0" not in pref_values
