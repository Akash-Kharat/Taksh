"""
Session Consolidation Engine (MS-12)

Summarizes completed sessions, extracts preferences, ADRs, lessons,
and generates snapshots when specific triggers occur. Enforces the
single active project policy.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.database_models import (
    ConversationProfile,
    MemoryEvent,
    PreferenceMemory,
    ProjectMemory,
    ProjectSnapshot,
    Session as DBSession
)
from app.services.conversation.preferences import PreferenceExtractor


class SessionConsolidator:
    """Consolidates closed sessions into profile, preference, and project memory."""

    DECISION_PATTERNS = [
        r"(?i)\bdecision:\s*(.*)",
        r"(?i)\badr:\s*(.*)",
        r"(?i)\bdecided to\s*(.*)"
    ]
    LESSON_PATTERNS = [
        r"(?i)\blesson:\s*(.*)",
        r"(?i)\blesson learned:\s*(.*)"
    ]
    GOAL_PATTERNS = [
        r"(?i)\bgoal:\s*(.*)",
        r"(?i)\bobjective:\s*(.*)"
    ]
    NEXT_STEP_PATTERNS = [
        r"(?i)\bnext step:\s*(.*)",
        r"(?i)\bnext:\s*(.*)"
    ]
    MILESTONE_PATTERNS = [
        r"(?i)\bmilestone\s+([\w\-\.]+)\s+completed\b",
        r"(?i)\bcompleted milestone\s+([\w\-\.]+)\b"
    ]

    @classmethod
    def extract_structured_data(cls, text: str) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
        """Extracts decisions, lessons, goals, next steps, and milestones from text."""
        decisions, lessons, goals, next_steps, milestones = [], [], [], [], []

        sentences = re.split(r"[.!?\n]", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check decisions
            for pattern in cls.DECISION_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    decisions.append(match.group(1).strip())
                    break

            # Check lessons
            for pattern in cls.LESSON_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    lessons.append(match.group(1).strip())
                    break

            # Check goals
            for pattern in cls.GOAL_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    goals.append(match.group(1).strip())
                    break

            # Check next steps
            for pattern in cls.NEXT_STEP_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    next_steps.append(match.group(1).strip())
                    break

            # Check milestones
            for pattern in cls.MILESTONE_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    milestones.append(match.group(1).strip())
                    break

        return decisions, lessons, goals, next_steps, milestones

    @classmethod
    def consolidate_session(cls, db: Session, session_id: str) -> Optional[dict]:
        """
        Consolidates session data post-closure.
        Performs preference extraction, project memory updates, and snapshot checks.
        """
        # 1. Fetch Session
        session_record = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not session_record:
            return None

        # 2. Get all text events (transcripts) from session
        events = db.query(MemoryEvent).filter(MemoryEvent.session_id == session_id).all()
        transcripts = []
        for e in events:
            if e.text_payload and e.text_payload.transcript:
                transcripts.append(e.text_payload.transcript)
        
        full_text = "\n".join(transcripts)

        # 3. Extract and persist preferences (traceability details mapping)
        # Use first event's trace_id as reference if available
        ref_trace_id = None
        for e in events:
            # Check if event is linked to cognitive trace
            # In MS-08, ConversationMessage has trace_id, MemoryEvent is linked to Session.
            # Let's search cognitive_traces or use a dummy trace/first available trace
            pass
        
        PreferenceExtractor.extract_and_persist(
            db=db,
            text=full_text,
            session_id=session_id,
            trace_id=ref_trace_id
        )

        # 4. Extract structured items (ADRs, Goals, Next Steps, Milestones)
        decisions, lessons, goals, next_steps, milestones = cls.extract_structured_data(full_text)

        # 5. Retrieve or Create ConversationProfile (ensure single active profile)
        profile = db.query(ConversationProfile).first()
        if not profile:
            profile = ConversationProfile(
                interaction_count=0,
                first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow()
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # 6. Retrieve active project
        active_project = None
        if profile.active_project_id:
            active_project = (
                db.query(ProjectMemory)
                .filter(ProjectMemory.project_memory_id == profile.active_project_id)
                .first()
            )
        
        # Fallback to first active/existing project or create a default "Default Project"
        if not active_project:
            active_project = db.query(ProjectMemory).filter(ProjectMemory.status == "active").first()
            if not active_project:
                active_project = db.query(ProjectMemory).first()
                
            if not active_project:
                # Create a default project memory record
                active_project = ProjectMemory(
                    project_name="Default Project",
                    status="active",
                    summary="Automatically created default workspace project."
                )
                db.add(active_project)
                db.commit()
                db.refresh(active_project)
            
            profile.active_project_id = active_project.project_memory_id
            db.commit()

        # Enforce single active project constraints
        if active_project.status != "active":
            cls.activate_project(db, active_project.project_memory_id)

        # 7. Update Project Memory attributes
        old_status = active_project.status
        old_milestone = active_project.current_milestone

        # Merge extracted list attributes
        if goals:
            current_goals = list(active_project.active_goals or [])
            current_goals.extend([g for g in goals if g not in current_goals])
            active_project.active_goals = current_goals

        if next_steps:
            current_next = list(active_project.next_steps or [])
            current_next.extend([ns for ns in next_steps if ns not in current_next])
            active_project.next_steps = current_next

        # Check if we completed any milestones in the text
        milestone_completed = False
        if milestones:
            active_project.current_milestone = milestones[-1]
            milestone_completed = True

        db.commit()
        db.refresh(active_project)

        # 8. Snapshot Trigger Validation (Revision 3)
        # Snapshots are created only on status changes, milestones completed, or ADRs approved
        status_changed = (old_status != active_project.status)
        adr_extracted = len(decisions) > 0

        if status_changed or milestone_completed or adr_extracted:
            # Create snapshot record
            snapshot = ProjectSnapshot(
                project_name=active_project.project_name,
                milestone=active_project.current_milestone or "Base",
                summary=active_project.summary or f"Consolidation snapshot for session {session_id}",
                decisions=decisions,
                open_questions=active_project.open_questions or [],
                next_steps=active_project.next_steps or []
            )
            db.add(snapshot)
            db.commit()

        # 9. Update ConversationProfile interaction counts
        profile.interaction_count += 1
        profile.last_seen_at = datetime.utcnow()
        db.commit()

        return {
            "decisions_extracted": len(decisions),
            "lessons_extracted": len(lessons),
            "snapshot_generated": (status_changed or milestone_completed or adr_extracted)
        }

    @classmethod
    def activate_project(cls, db: Session, project_id: str) -> None:
        """
        Enforces single active project policy:
        Sets target project to 'active', marks all other projects 'inactive',
        and updates ConversationProfile.
        """
        target = db.query(ProjectMemory).filter(ProjectMemory.project_memory_id == project_id).first()
        if not target:
            return

        # Deactivate all projects
        db.query(ProjectMemory).update({ProjectMemory.status: "inactive"})
        
        # Activate target
        target.status = "active"

        # Update profile pointer
        profile = db.query(ConversationProfile).first()
        if profile:
            profile.active_project_id = target.project_memory_id
            profile.updated_at = datetime.utcnow()

        db.commit()
