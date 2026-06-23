"""
MS-20 Tests — Configuration Validator
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.config_validator import ConfigValidator, ConfigCheck


def _get_checks_by_name(results, name):
    return [c for c in results if c.name == name]


# ---------------------------------------------------------------------------
# Domain: Database
# ---------------------------------------------------------------------------

def test_database_path_exists_passes(tmp_path):
    with patch("app.core.config.settings.TAKSH_DIR", tmp_path), \
         patch("app.core.config.settings.DATABASE_NAME", "test.db"):
        v = ConfigValidator()
        checks = v._check_database(MagicMock(
            TAKSH_DIR=tmp_path,
            DATABASE_NAME="test.db",
        ))
    names = [c.name for c in checks]
    assert "Path exists" in names


def test_database_path_writable_passes(tmp_path):
    mock_settings = MagicMock(
        TAKSH_DIR=tmp_path,
        DATABASE_NAME="test.db",
    )
    v = ConfigValidator()
    with patch("app.core.config.settings", mock_settings):
        checks = v._check_database(mock_settings)
    writable = next(c for c in checks if c.name == "Path writable")
    assert writable.passed is True


def test_database_migration_check_exists():
    """Migration check is part of the result set."""
    v = ConfigValidator()
    from unittest.mock import MagicMock, patch
    import tempfile, pathlib
    tmp = pathlib.Path(tempfile.mkdtemp())
    mock_settings = MagicMock(
        TAKSH_DIR=tmp,
        DATABASE_NAME="test.db",
    )
    with patch("app.core.config.settings", mock_settings):
        checks = v._check_database(mock_settings)
    names = [c.name for c in checks]
    assert "Migration current" in names


# ---------------------------------------------------------------------------
# Domain: Workspace
# ---------------------------------------------------------------------------

def test_workspace_exists_passes(tmp_path):
    mock_s = MagicMock(TAKSH_DIR=tmp_path)
    v = ConfigValidator()
    checks = v._check_workspace(mock_s)
    exists = next(c for c in checks if c.name == "Directory exists")
    assert exists.passed is True


def test_workspace_not_found_fails(tmp_path):
    missing = tmp_path / "does_not_exist"
    mock_s = MagicMock(TAKSH_DIR=missing)
    v = ConfigValidator()
    checks = v._check_workspace(mock_s)
    exists = next(c for c in checks if c.name == "Directory exists")
    assert exists.passed is False


def test_workspace_readable_passes(tmp_path):
    mock_s = MagicMock(TAKSH_DIR=tmp_path)
    v = ConfigValidator()
    checks = v._check_workspace(mock_s)
    readable = next(c for c in checks if c.name == "Readable")
    assert readable.passed is True


# ---------------------------------------------------------------------------
# Domain: Providers
# ---------------------------------------------------------------------------

def test_providers_configured_passes():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="mock",
        PROVIDER_REQUEST_TIMEOUT_SECONDS=30,
    )
    v = ConfigValidator()
    checks = v._check_providers(mock_s)
    configured = next(c for c in checks if c.name == "Configured")
    assert configured.passed is True


def test_providers_empty_name_fails():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="  ",
        PROVIDER_REQUEST_TIMEOUT_SECONDS=30,
    )
    v = ConfigValidator()
    checks = v._check_providers(mock_s)
    configured = next(c for c in checks if c.name == "Configured")
    assert configured.passed is False


def test_providers_timeout_valid():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="mock",
        PROVIDER_REQUEST_TIMEOUT_SECONDS=30,
    )
    v = ConfigValidator()
    checks = v._check_providers(mock_s)
    timeout = next(c for c in checks if c.name == "Timeout valid")
    assert timeout.passed is True


def test_providers_timeout_too_large_fails():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="mock",
        PROVIDER_REQUEST_TIMEOUT_SECONDS=999,
    )
    v = ConfigValidator()
    checks = v._check_providers(mock_s)
    timeout = next(c for c in checks if c.name == "Timeout valid")
    assert timeout.passed is False


# ---------------------------------------------------------------------------
# Domain: Voice
# ---------------------------------------------------------------------------

def test_voice_sample_rate_valid():
    mock_s = MagicMock(VOICE_SAMPLE_RATE=16000, VOICE_BUFFER_SIZE_FRAMES=256)
    v = ConfigValidator()
    checks = v._check_voice(mock_s)
    sr = next(c for c in checks if c.name == "Sample rate valid")
    assert sr.passed is True


def test_voice_sample_rate_out_of_range_fails():
    mock_s = MagicMock(VOICE_SAMPLE_RATE=1000, VOICE_BUFFER_SIZE_FRAMES=256)
    v = ConfigValidator()
    checks = v._check_voice(mock_s)
    sr = next(c for c in checks if c.name == "Sample rate valid")
    assert sr.passed is False


def test_voice_buffer_size_valid():
    mock_s = MagicMock(VOICE_SAMPLE_RATE=16000, VOICE_BUFFER_SIZE_FRAMES=256)
    v = ConfigValidator()
    checks = v._check_voice(mock_s)
    buf = next(c for c in checks if c.name == "Buffer size valid")
    assert buf.passed is True


# ---------------------------------------------------------------------------
# Domain: Security
# ---------------------------------------------------------------------------

def test_security_mock_provider_skips_api_key_check():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="mock",
        GEMINI_API_KEY="",
        TAKSH_PROFILE="development",
    )
    v = ConfigValidator()
    checks = v._check_security(mock_s)
    key_check = next(c for c in checks if c.name == "API key present")
    assert key_check.passed is True  # Skipped — mock


def test_security_non_mock_without_key_fails():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="gemini",
        GEMINI_API_KEY="",
        TAKSH_PROFILE="lab",
    )
    v = ConfigValidator()
    checks = v._check_security(mock_s)
    key_check = next(c for c in checks if c.name == "API key present")
    assert key_check.passed is False


def test_security_production_with_mock_fails():
    mock_s = MagicMock(
        DEFAULT_LLM_PROVIDER="mock",
        GEMINI_API_KEY="",
        TAKSH_PROFILE="production",
    )
    v = ConfigValidator()
    checks = v._check_security(mock_s)
    prod_check = next(c for c in checks if c.name == "Production defaults check")
    assert prod_check.passed is False


def test_validate_all_returns_list_of_config_checks():
    v = ConfigValidator()
    results = v.validate_all()
    assert isinstance(results, list)
    for c in results:
        assert isinstance(c, ConfigCheck)
        assert hasattr(c, "domain")
        assert hasattr(c, "name")
        assert hasattr(c, "passed")
