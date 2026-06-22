"""
Unit tests for PreferenceMemory and PreferenceExtractor.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database_models import PreferenceMemory
from app.services.conversation.preferences import PreferenceExtractor


def test_preference_categorization():
    assert PreferenceExtractor.categorize_preference("Always use pytest") == "coding_style"
    assert PreferenceExtractor.categorize_preference("I prefer esp32 hardware pinouts") == "hardware"
    assert PreferenceExtractor.categorize_preference("From now on write ADR logs") == "workflow"
    assert PreferenceExtractor.categorize_preference("Default to sandbox execution policy") == "policy"
    assert PreferenceExtractor.categorize_preference("I prefer to run in the morning") == "general"


def test_preference_extraction_triggers():
    text = "Always use pytest. Going forward ignore temporary files. I prefer esp32."
    items = PreferenceExtractor.extract_from_text(text)
    
    assert len(items) == 3
    assert any(i["category"] == "coding_style" and "Always use pytest" in i["value"] for i in items)
    assert any("Going forward ignore temporary files" in i["value"] for i in items)
    assert any(i["confidence_score"] == 0.9 for i in items)  # "Always use"
    assert any(i["confidence_score"] == 0.7 for i in items)  # "Going forward"


def test_preference_persistence_and_deduplication(db_session: Session):
    text = "Always use pytest."
    session_id = "sess-123"
    trace_id = "trace-456"

    # First extraction should create new record
    prefs = PreferenceExtractor.extract_and_persist(db_session, text, session_id, trace_id)
    assert len(prefs) == 1
    pref = prefs[0]
    assert pref.preference_id is not None
    assert pref.category == "coding_style"
    assert "Always use pytest" in pref.value
    assert pref.confidence_score == 0.9
    assert pref.source_session_id == session_id
    assert pref.source_trace_id == trace_id

    # Second extraction of duplicate statement should update confidence and datetime
    updated_prefs = PreferenceExtractor.extract_and_persist(db_session, text, "sess-789", "trace-012")
    assert len(updated_prefs) == 1
    updated_pref = updated_prefs[0]
    
    assert updated_pref.preference_id == pref.preference_id
    assert updated_pref.confidence_score == 1.0  # 0.9 + 0.1
    assert updated_pref.source_session_id == "sess-789"
    assert updated_pref.source_trace_id == "trace-012"
    
    # Assert database only contains 1 record
    count = db_session.query(PreferenceMemory).count()
    assert count == 1
