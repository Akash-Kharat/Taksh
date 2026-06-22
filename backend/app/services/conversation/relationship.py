"""
Relationship Context Tracker (MS-12)

Tracks engineering-focused interaction diagnostics:
- Interaction count.
- Total projects.
- Longest running project name.
- Last active timestamp.

Excludes emotional state, mood, and personality modeling.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database_models import ConversationProfile, ProjectMemory, Session as DBSession


class RelationshipTracker:
    """Computes technical relationship metrics to track Taksh project continuity."""

    @classmethod
    def get_relationship_context(cls, db: Session) -> Dict[str, Any]:
        """
        Calculate and return engineering-focused relationship metadata.
        Returns a dict of interaction stats.
        """
        # 1. Fetch conversation profile
        profile = db.query(ConversationProfile).first()
        
        # Fallback values if profile doesn't exist yet
        interaction_count = profile.interaction_count if profile else 0
        last_active_at = profile.last_seen_at if profile else datetime.utcnow()

        # 2. Total projects count
        total_projects = db.query(ProjectMemory).count()

        # 3. Find active project count (status in active, paused, completed)
        active_project_count = (
            db.query(ProjectMemory)
            .filter(ProjectMemory.status != "inactive")
            .count()
        )

        # 4. Longest running project
        # Determined by looking at the project that has the oldest updated/created time,
        # or oldest ProjectMemory record. We select the one with the earliest created_at / last_updated_at.
        # Since we don't have created_at on ProjectMemory, we use project_memory_id or last_updated_at.
        # A simple choice is to select the project memory record with the oldest last_updated_at or status.
        # Or sorting by last_updated_at ascending.
        longest_project_record = (
            db.query(ProjectMemory)
            .order_by(ProjectMemory.last_updated_at.asc())
            .first()
        )
        longest_running_project = longest_project_record.project_name if longest_project_record else None

        return {
            "interaction_count": interaction_count,
            "total_projects": total_projects,
            "active_project_count": active_project_count,
            "longest_running_project": longest_running_project,
            "last_active_at": last_active_at.isoformat() if last_active_at else None
        }
