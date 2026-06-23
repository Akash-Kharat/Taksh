"""
Tests for MS-19 Startup Validator.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.startup_validator import StartupValidator, StartupCheck


def _make_passing_check(name: str, critical: bool = True) -> StartupCheck:
    return StartupCheck(name=name, critical=critical, passed=True, detail="OK")


def _make_failing_check(name: str, critical: bool = True) -> StartupCheck:
    return StartupCheck(name=name, critical=critical, passed=False, detail="Simulated failure")


def _all_passing_patches(v: StartupValidator, overrides: dict = None):
    """Context manager that patches all individual check methods to pass."""
    from contextlib import ExitStack
    overrides = overrides or {}
    defaults = {
        "_check_database":          _make_passing_check("Database"),
        "_check_alembic_migration": _make_passing_check("Alembic"),
        "_check_workspace_dir":     _make_passing_check("Workspace"),
        "_check_chromadb":          _make_passing_check("ChromaDB"),
        "_check_identity_file":     _make_passing_check("Identity"),
        "_check_skills_dir":        _make_passing_check("Skills", critical=False),
        "_check_llm_provider":      _make_passing_check("LLM", critical=False),
        "_check_docs_dir":          _make_passing_check("Docs"),
        "_check_fts5":              _make_passing_check("FTS5"),
    }
    defaults.update(overrides)
    stack = ExitStack()
    for method, retval in defaults.items():
        stack.enter_context(patch.object(v, method, return_value=retval))
    return stack


# ---------------------------------------------------------------------------
# Unit tests for individual checks
# ---------------------------------------------------------------------------

def test_check_workspace_dir_passes_when_dir_exists(tmp_path):
    with patch("app.core.config.settings.TAKSH_DIR", tmp_path):
        v = StartupValidator()
        result = v._check_workspace_dir()
    assert result.passed is True
    assert result.critical is True


def test_check_identity_file_fails_when_missing(tmp_path):
    with patch("app.core.config.settings.IDENTITY_PATH", tmp_path / "nonexistent.md"):
        v = StartupValidator()
        result = v._check_identity_file()
    assert result.passed is False
    assert result.critical is True


def test_check_skills_dir_non_critical_on_failure(tmp_path):
    with patch("app.core.config.settings.SKILLS_MANIFEST_DIR", tmp_path / "no_skills"):
        v = StartupValidator()
        result = v._check_skills_dir()
    assert result.passed is False
    assert result.critical is False  # non-critical


def test_check_llm_provider_passes():
    v = StartupValidator()
    result = v._check_llm_provider()
    assert result.critical is False


def test_check_fts5_passes():
    v = StartupValidator()
    result = v._check_fts5()
    assert result.passed is True


# ---------------------------------------------------------------------------
# validate_all() behaviour
# ---------------------------------------------------------------------------

def test_critical_failure_raises_runtime_error():
    v = StartupValidator()
    with _all_passing_patches(v, {
        "_check_database": _make_failing_check("Database", critical=True),
    }):
        with pytest.raises(RuntimeError, match="Database"):
            v.validate_all()


def test_non_critical_failure_does_not_raise():
    v = StartupValidator()
    with _all_passing_patches(v, {
        "_check_skills_dir": _make_failing_check("Skills", critical=False),
    }):
        results = v.validate_all()

    failed = [c for c in results if not c.passed]
    assert len(failed) == 1
    assert failed[0].name == "Skills"


def test_validate_all_caches_results():
    from app.core import startup_validator as sv_module
    v = StartupValidator()
    with _all_passing_patches(v):
        results = v.validate_all()
    assert len(sv_module.startup_results) > 0


def test_validate_all_returns_list_of_checks():
    v = StartupValidator()
    with _all_passing_patches(v):
        results = v.validate_all()
    assert isinstance(results, list)
    assert all(isinstance(c, StartupCheck) for c in results)
