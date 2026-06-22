"""
Conversation Intelligence REST API (MS-12)

Endpoints
---------
GET /conversation/info — Continuity diagnostics and statistics summary
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import (
    ConversationProfile,
    PreferenceMemory,
    ProjectMemory,
    ProjectSnapshot,
)
from app.schemas.conversation import ConversationInfoResponse

router = APIRouter(prefix="/conversation", tags=["Conversation Intelligence"])


@router.get("/info", response_model=ConversationInfoResponse)
def conversation_info(db: Session = Depends(get_db)) -> ConversationInfoResponse:
    """Return counts and metadata summarizing current long-term continuity state."""
    profiles_count = db.query(ConversationProfile).count()
    preferences_count = db.query(PreferenceMemory).count()
    projects_count = db.query(ProjectMemory).count()
    snapshots_count = db.query(ProjectSnapshot).count()

    active_project_name = None
    profile = db.query(ConversationProfile).first()
    if profile and profile.active_project_id:
        active_project = (
            db.query(ProjectMemory)
            .filter(ProjectMemory.project_memory_id == profile.active_project_id)
            .first()
        )
        if active_project:
            active_project_name = active_project.project_name

    return ConversationInfoResponse(
        profiles=profiles_count,
        preferences=preferences_count,
        projects=projects_count,
        snapshots=snapshots_count,
        active_project=active_project_name,
    )
