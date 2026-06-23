"""
MS-20 Tests — Release Manifest
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import app.core.release_manifest as rm_module


SAMPLE_MANIFEST = {
    "version": "0.1.0-rc1",
    "schema_version": "a1b2c3d4e5f6",
    "build_date": "2026-06-23T05:56:00Z",
    "completed_milestones": [f"MS-{i:02d}" for i in range(1, 21)],
}


@pytest.fixture(autouse=True)
def clear_manifest_cache():
    rm_module.clear_cache()
    yield
    rm_module.clear_cache()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_load_manifest_returns_dict(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        data = rm_module.load_manifest()

    assert isinstance(data, dict)
    assert data["version"] == "0.1.0-rc1"


def test_load_manifest_caches_result(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        first  = rm_module.load_manifest()
        second = rm_module.load_manifest()

    assert first is second  # Same object — cached


def test_get_manifest_is_alias_for_load(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        data = rm_module.get_manifest()

    assert "version" in data


def test_load_manifest_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.json"
    with patch.object(rm_module, "_MANIFEST_PATH", missing):
        with pytest.raises(FileNotFoundError):
            rm_module.load_manifest()


def test_load_manifest_raises_on_invalid_json(tmp_path):
    bad_file = tmp_path / "release_manifest.json"
    bad_file.write_text("NOT JSON {{{")
    with patch.object(rm_module, "_MANIFEST_PATH", bad_file):
        with pytest.raises(json.JSONDecodeError):
            rm_module.load_manifest()


def test_clear_cache_allows_reload(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        first = rm_module.load_manifest()
        rm_module.clear_cache()
        second = rm_module.load_manifest()

    assert first == second  # Same content
    assert first is not second  # Different objects (reloaded)


def test_manifest_has_all_required_fields(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        data = rm_module.load_manifest()

    assert "version" in data
    assert "schema_version" in data
    assert "build_date" in data
    assert "completed_milestones" in data


def test_completed_milestones_is_list(tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        data = rm_module.load_manifest()

    assert isinstance(data["completed_milestones"], list)
    assert len(data["completed_milestones"]) == 20


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

def test_release_endpoint_returns_200(client, tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        rm_module.clear_cache()
        response = client.get("/api/v1/system/release")

    assert response.status_code == 200


def test_release_endpoint_has_version(client, tmp_path):
    manifest_file = tmp_path / "release_manifest.json"
    manifest_file.write_text(json.dumps(SAMPLE_MANIFEST))

    with patch.object(rm_module, "_MANIFEST_PATH", manifest_file):
        rm_module.clear_cache()
        response = client.get("/api/v1/system/release")

    data = response.json()
    assert data["version"] == "0.1.0-rc1"
    assert data["schema_version"] == "a1b2c3d4e5f6"
    assert isinstance(data["completed_milestones"], list)
