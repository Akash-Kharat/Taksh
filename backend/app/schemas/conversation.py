"""
Pydantic schemas for the Conversation Intelligence Layer REST API (MS-12).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ConversationInfoResponse(BaseModel):
    """Diagnostics and statistics summary of conversation continuity data."""
    profiles: int = Field(..., description="Number of conversation profiles tracked")
    preferences: int = Field(..., description="Total count of stored preference memory records")
    projects: int = Field(..., description="Total count of projects registered in database")
    snapshots: int = Field(..., description="Total count of project snapshots captured")
    active_project: Optional[str] = Field(None, description="Name of the currently active project")
