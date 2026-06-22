"""
Integration tests for Conversation REST API endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database_models import ConversationProfile, ProjectMemory, PreferenceMemory, ProjectSnapshot


def test_conversation_info_api(client: TestClient, db_session: Session):
    # 1. Populate DB with diagnostic stats
    p = ProjectMemory(
        project_name="Taksh CLI",
        status="active",
        summary="Command line tool"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    prof = ConversationProfile(
        interaction_count=3,
        active_project_id=p.project_memory_id
    )
    db_session.add(prof)

    pref1 = PreferenceMemory(category="general", value="Always use tabs", confidence_score=0.9)
    pref2 = PreferenceMemory(category="general", value="Always print summary", confidence_score=0.8)
    db_session.add_all([pref1, pref2])

    snap = ProjectSnapshot(
        project_name="Taksh CLI",
        milestone="v0.1",
        summary="Initial draft",
        decisions=[],
        open_questions=[],
        next_steps=[]
    )
    db_session.add(snap)
    db_session.commit()

    # 2. Query endpoint
    response = client.get("/api/v1/conversation/info")
    assert response.status_code == 200
    data = response.json()

    assert data["profiles"] == 1
    assert data["preferences"] == 2
    assert data["projects"] == 1
    assert data["snapshots"] == 1
    assert data["active_project"] == "Taksh CLI"
