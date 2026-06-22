"""
Preference Extractor Service (MS-12)

Rule-based extraction of user preferences from session transcripts.
Supports confidence scoring, categorization, deduplication, and traceability.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database_models import PreferenceMemory


class PreferenceExtractor:
    """Extracts, categorizes, and upserts user preferences from natural language."""

    # Trigger patterns mapped to (base_confidence, label)
    TRIGGERS = {
        r"(?i)\bfrom now on\b": (0.9, "From now on"),
        r"(?i)\balways use\b": (0.9, "Always use"),
        r"(?i)\bdefault to\b": (0.9, "Default to"),
        r"(?i)\bgoing forward\b": (0.7, "Going forward"),
        r"(?i)\bi prefer\b": (0.7, "I prefer"),
    }

    @classmethod
    def categorize_preference(cls, value: str) -> str:
        """Categorize preferences based on keywords in the text."""
        val_lower = value.lower()
        
        # Helper to search for whole words
        def has_word(kw: str) -> bool:
            return bool(re.search(rf"\b{re.escape(kw)}\b", val_lower))

        if any(has_word(kw) for kw in ["python", "test", "ruff", "pytest", "flake8", "lint", "pep8", "code", "style"]):
            return "coding_style"
        if any(has_word(kw) for kw in ["hardware", "esp32", "pcb", "board", "mcu", "pin", "peripheral", "sensor"]):
            return "hardware"
        if any(has_word(kw) for kw in ["workflow", "git", "commit", "adr", "pr", "ci", "branch", "repo"]):
            return "workflow"
        if any(has_word(kw) for kw in ["policy", "safety", "execution", "sandbox", "approval", "strict"]):
            return "policy"
        return "general"

    @classmethod
    def extract_from_text(cls, text: str) -> List[dict]:
        """
        Parses text for preference triggers and returns structured dictionaries
        containing category, value, and confidence.
        """
        extracted = []
        # Split text into sentences using basic delimiters
        sentences = re.split(r"[.!?\n]", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for pattern, (confidence, trigger_label) in cls.TRIGGERS.items():
                match = re.search(pattern, sentence)
                if match:
                    # Capture the rest of the sentence after the trigger or the whole sentence
                    start_idx = match.start()
                    val = sentence[start_idx:].strip()
                    # Clean up common sentence endings or extra quotes
                    val = re.sub(r'["\'`\(\)\[\]]', '', val)
                    if len(val) > 10:  # Ignore trivial extractions
                        cat = cls.categorize_preference(val)
                        extracted.append({
                            "category": cat,
                            "value": val,
                            "confidence_score": confidence
                        })
                        # Stop checking other triggers for this sentence once matched
                        break
        return extracted

    @classmethod
    def extract_and_persist(
        cls,
        db: Session,
        text: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> List[PreferenceMemory]:
        """
        Extracts preferences from text and upserts them to the database.
        Applies deduplication and audit trail links.
        """
        items = cls.extract_from_text(text)
        persisted = []

        for item in items:
            category = item["category"]
            value = item["value"]
            conf = item["confidence_score"]

            # Deduplication: Check for exact value match in the same category
            existing = (
                db.query(PreferenceMemory)
                .filter(
                    PreferenceMemory.category == category,
                    PreferenceMemory.value == value
                )
                .first()
            )

            if existing:
                # Update existing record: bump confidence slightly, update confirmation timestamp
                existing.last_confirmed_at = datetime.utcnow()
                existing.confidence_score = min(1.0, existing.confidence_score + 0.1)
                existing.source_session_id = session_id
                existing.source_trace_id = trace_id
                db.commit()
                db.refresh(existing)
                persisted.append(existing)
            else:
                # Create new preference memory with audit trail
                pref = PreferenceMemory(
                    category=category,
                    value=value,
                    confidence_score=conf,
                    source_session_id=session_id,
                    source_trace_id=trace_id,
                    last_confirmed_at=datetime.utcnow()
                )
                db.add(pref)
                db.commit()
                db.refresh(pref)
                persisted.append(pref)

        return persisted
