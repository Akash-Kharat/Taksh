"""
MS-20 Tests — Backup Restore Validation
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app.core.backup_validator import BackupValidator, BackupValidationResult


# ---------------------------------------------------------------------------
# Minimal export fixture
# ---------------------------------------------------------------------------

MINIMAL_EXPORT = {
    "backup_version": "1",
    "taksh_version": "0.1",
    "created_at": "2026-06-23T00:00:00",
    "schema_version": "a1b2c3d4e5f6",
    "data": {
        "conversations":    [],
        "memory_episodes":  [],
        "projects":         [],
        "preferences":      [],
        "open_tasks":       [],
    },
}


# ---------------------------------------------------------------------------
# BackupValidationResult dataclass
# ---------------------------------------------------------------------------

def test_backup_validation_result_fields():
    r = BackupValidationResult(
        valid=True, export_valid=True, restore_valid=True,
        counts_match=True, records_restored=0, detail="OK",
    )
    assert r.valid is True
    assert r.records_restored == 0


# ---------------------------------------------------------------------------
# _verify_counts
# ---------------------------------------------------------------------------

def test_verify_counts_empty_export_is_zero():
    v = BackupValidator()
    data = MINIMAL_EXPORT["data"]
    ok = v._verify_counts(data, 0)
    assert ok is True


def test_verify_counts_mismatch_fails():
    v = BackupValidator()
    data = MINIMAL_EXPORT["data"].copy()
    # Pretend there's 1 episode in data but we restored 0
    data["memory_episodes"] = [{"id": 1, "session_id": "x"}]
    ok = v._verify_counts(data, 0)
    assert ok is False


def test_verify_counts_with_nested_turns():
    v = BackupValidator()
    data = {
        "conversations": [
            {"runtime_session_id": "c1", "turns": [{"turn_id": "t1"}, {"turn_id": "t2"}]},
        ],
        "memory_episodes": [],
        "projects": [],
        "preferences": [],
        "open_tasks": [],
    }
    # 1 conversation + 2 turns = 3
    ok = v._verify_counts(data, 3)
    assert ok is True


# ---------------------------------------------------------------------------
# Full validate() cycle
# ---------------------------------------------------------------------------

def test_validate_with_empty_db_succeeds(db_session):
    v = BackupValidator()
    result = v.validate(db_session)
    assert isinstance(result, BackupValidationResult)
    assert result.export_valid is True
    assert result.restore_valid is True
    assert result.valid is True
    assert result.records_restored == 0


def test_validate_returns_valid_true_on_success(db_session):
    v = BackupValidator()
    result = v.validate(db_session)
    assert result.valid is True


def test_validate_returns_false_when_export_fails(db_session):
    v = BackupValidator()
    with patch("app.core.backup.backup_manager.export_json",
               side_effect=RuntimeError("export boom")):
        result = v.validate(db_session)
    assert result.valid is False
    assert result.export_valid is False
    assert "export boom" in result.detail


def test_validate_records_restored_is_nonnegative(db_session):
    v = BackupValidator()
    result = v.validate(db_session)
    assert result.records_restored >= 0


def test_validate_with_one_conversation(db_session):
    """Backup validator round-trips a ConversationRuntimeSession correctly."""
    from app.models.database_models import ConversationRuntimeSession
    import uuid
    sid = f"backup-smoke-{uuid.uuid4().hex[:8]}"
    s = ConversationRuntimeSession(
        runtime_session_id         = sid,
        conversation_state         = "idle",
        conversation_session_state = "closed",
        current_turn_owner         = "none",
    )
    db_session.add(s)
    db_session.flush()

    v = BackupValidator()
    result = v.validate(db_session)
    assert result.export_valid is True
    assert result.restore_valid is True
    assert result.valid is True
    assert result.records_restored >= 1


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def test_backup_validate_endpoint_returns_200(client):
    response = client.post("/api/v1/system/backup/validate")
    assert response.status_code == 200


def test_backup_validate_endpoint_has_valid_field(client):
    response = client.post("/api/v1/system/backup/validate")
    data = response.json()
    assert "valid" in data
    assert "records_restored" in data


def test_backup_validate_endpoint_valid_is_bool(client):
    response = client.post("/api/v1/system/backup/validate")
    assert isinstance(response.json()["valid"], bool)


def test_backup_validate_endpoint_valid_true_on_clean_db(client):
    response = client.post("/api/v1/system/backup/validate")
    assert response.json()["valid"] is True
