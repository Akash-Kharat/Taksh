"""
MS-20 Tests — Installer Checker
"""
import sys
import sqlite3
import pytest
from unittest.mock import patch
from app.core.installer_check import InstallerChecker, InstallCheck, REQUIRED_PACKAGES


def test_run_all_returns_list():
    checker = InstallerChecker()
    results = checker.run_all()
    assert isinstance(results, list)
    assert len(results) > 0


def test_all_results_are_install_checks():
    checker = InstallerChecker()
    results = checker.run_all()
    for r in results:
        assert isinstance(r, InstallCheck)
        assert r.status in ("PASS", "WARN", "FAIL")


def test_python_version_passes():
    checker = InstallerChecker()
    result = checker._check_python_version()
    # We're running 3.11 in condaenv311
    assert result.status == "PASS"
    assert "Python" in result.detail


def test_python_version_fails_below_311():
    import app.core.installer_check as ic_module
    checker = InstallerChecker()
    # sys.version_info is read-only; patch the sys module reference inside installer_check
    class FakeVersionInfo:
        major = 3; minor = 10; micro = 0
        def __ge__(self, other): return (self.major, self.minor, self.micro) >= tuple(other)
        def __str__(self): return "3.10.0"
    with patch.object(ic_module.sys, "version_info", FakeVersionInfo()):
        result = checker._check_python_version()
    assert result.status == "FAIL"
    assert "3.10" in result.detail


def test_sqlite_version_passes():
    checker = InstallerChecker()
    result = checker._check_sqlite_version()
    assert result.status == "PASS"


def test_fts5_check_passes():
    checker = InstallerChecker()
    result = checker._check_fts5()
    assert result.status == "PASS"
    assert "available" in result.detail.lower()


def test_fts5_check_fails_on_exception():
    checker = InstallerChecker()
    with patch("sqlite3.connect", side_effect=Exception("no fts5")):
        result = checker._check_fts5()
    assert result.status == "FAIL"


def test_chromadb_check_passes():
    checker = InstallerChecker()
    result = checker._check_chromadb()
    assert result.status == "PASS"


def test_chromadb_check_fails_on_import_error():
    checker = InstallerChecker()
    with patch.dict("sys.modules", {"chromadb": None}):
        with patch("builtins.__import__", side_effect=ImportError("no chromadb")):
            result = checker._check_chromadb()
    assert result.status == "FAIL"


def test_workspace_writable_passes(tmp_path):
    checker = InstallerChecker()
    with patch("app.core.config.settings.TAKSH_DIR", tmp_path):
        result = checker._check_workspace_writable()
    assert result.status == "PASS"


def test_docs_readable_warns_when_missing(tmp_path):
    checker = InstallerChecker()
    missing = tmp_path / "nonexistent_docs"
    with patch("app.core.config.settings.DOCS_DIR", missing):
        result = checker._check_docs_readable()
    assert result.status == "WARN"


def test_env_file_warns_when_missing(tmp_path, monkeypatch):
    # Change cwd to a temp dir that has no .env file
    monkeypatch.chdir(tmp_path)
    checker = InstallerChecker()
    result = checker._check_env_file()
    assert result.status == "WARN"


def test_required_packages_all_importable():
    checker = InstallerChecker()
    results = checker._check_required_packages()
    assert len(results) == len(REQUIRED_PACKAGES)
    passing = [r for r in results if r.status == "PASS"]
    # All required packages should be installed in test env
    assert len(passing) == len(REQUIRED_PACKAGES)


def test_required_packages_fail_on_import_error():
    checker = InstallerChecker()
    with patch("builtins.__import__", side_effect=ImportError("missing_pkg")):
        results = checker._check_required_packages()
    for r in results:
        assert r.status == "FAIL"


def test_check_names_are_unique():
    checker = InstallerChecker()
    results = checker.run_all()
    names = [r.name for r in results]
    # Names should be distinct (no duplicate check names)
    assert len(names) == len(set(names))
