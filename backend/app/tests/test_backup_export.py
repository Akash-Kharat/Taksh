"""
Tests for MS-19 Backup & Export Framework.
"""
import io
import json
import zipfile
import pytest

from app.core.backup import BackupManager, BACKUP_VERSION, TAKSH_VERSION


def test_export_json_has_required_metadata_keys(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)

    assert "backup_version" in result
    assert "taksh_version" in result
    assert "created_at" in result
    assert "schema_version" in result
    assert "data" in result


def test_export_json_backup_version_is_current(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)
    assert result["backup_version"] == BACKUP_VERSION


def test_export_json_taksh_version(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)
    assert result["taksh_version"] == TAKSH_VERSION


def test_export_json_schema_version_is_string(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)
    assert isinstance(result["schema_version"], str)
    assert len(result["schema_version"]) > 0


def test_export_json_data_has_expected_sections(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)
    data = result["data"]
    assert "conversations" in data
    assert "memory_episodes" in data
    assert "projects" in data
    assert "preferences" in data
    assert "open_tasks" in data


def test_export_json_contains_no_api_keys(db_session):
    manager = BackupManager()
    result = manager.export_json(db_session)
    text = json.dumps(result)
    # API keys should never appear
    assert "GEMINI_API_KEY" not in text


def test_export_zip_is_valid_zip_archive(db_session):
    manager = BackupManager()
    zip_bytes = manager.export_zip(db_session)
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    buf = io.BytesIO(zip_bytes)
    assert zipfile.is_zipfile(buf)


def test_export_zip_contains_json_with_metadata(db_session):
    manager = BackupManager()
    zip_bytes = manager.export_zip(db_session)
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".json")
        content = json.loads(zf.read(names[0]))
    assert content["backup_version"] == BACKUP_VERSION
    assert "schema_version" in content


def test_backup_endpoint_returns_zip(client):
    response = client.get("/api/v1/system/backup")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    buf = io.BytesIO(response.content)
    assert zipfile.is_zipfile(buf)


def test_backup_endpoint_content_is_valid(client):
    response = client.get("/api/v1/system/backup")
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf) as zf:
        content = json.loads(zf.read(zf.namelist()[0]))
    assert content["backup_version"] == BACKUP_VERSION
    assert "data" in content
