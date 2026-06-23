"""
Taksh Installer Checker — MS-20

Verifies that the runtime environment meets all installation requirements.
Produces PASS / WARN / FAIL results for each check.

Usage:
  checker = InstallerChecker()
  results = checker.run_all()
"""
import logging
import sqlite3
import sys
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("installer_check")

REQUIRED_PACKAGES = [
    "fastapi",
    "sqlalchemy",
    "alembic",
    "pydantic",
    "pydantic_settings",
    "chromadb",
    "uvicorn",
]


@dataclass
class InstallCheck:
    name:   str
    status: str   # "PASS" | "WARN" | "FAIL"
    detail: str = ""


class InstallerChecker:
    """Verifies the runtime environment meets all installation prerequisites."""

    def run_all(self) -> List[InstallCheck]:
        results: List[InstallCheck] = []

        results.append(self._check_python_version())
        results.append(self._check_sqlite_version())
        results.append(self._check_fts5())
        results.append(self._check_chromadb())
        results.append(self._check_workspace_writable())
        results.append(self._check_docs_readable())
        results.append(self._check_env_file())
        results += self._check_required_packages()

        passed = sum(1 for r in results if r.status == "PASS")
        warned = sum(1 for r in results if r.status == "WARN")
        failed = sum(1 for r in results if r.status == "FAIL")
        logger.info(
            f"[installer_check] {passed} PASS, {warned} WARN, {failed} FAIL"
        )
        return results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_python_version(self) -> InstallCheck:
        vi = sys.version_info
        version_str = f"{vi.major}.{vi.minor}.{vi.micro}"
        if vi >= (3, 11):
            return InstallCheck("Python version", "PASS", f"Python {version_str}")
        return InstallCheck(
            "Python version", "FAIL",
            f"Python {version_str} found — requires >= 3.11",
        )

    def _check_sqlite_version(self) -> InstallCheck:
        ver = sqlite3.sqlite_version_info
        ver_str = sqlite3.sqlite_version
        if ver >= (3, 35, 0):
            return InstallCheck("SQLite version", "PASS", f"SQLite {ver_str}")
        return InstallCheck(
            "SQLite version", "FAIL",
            f"SQLite {ver_str} found — requires >= 3.35",
        )

    def _check_fts5(self) -> InstallCheck:
        try:
            con = sqlite3.connect(":memory:")
            cur = con.cursor()
            cur.execute("CREATE VIRTUAL TABLE _fts5_probe USING fts5(content);")
            cur.execute("DROP TABLE _fts5_probe;")
            con.close()
            return InstallCheck("SQLite FTS5", "PASS", "FTS5 extension available")
        except Exception as exc:
            return InstallCheck("SQLite FTS5", "FAIL", str(exc))

    def _check_chromadb(self) -> InstallCheck:
        try:
            import chromadb  # noqa: F401
            return InstallCheck("ChromaDB", "PASS", f"chromadb importable")
        except ImportError as exc:
            return InstallCheck("ChromaDB", "FAIL", f"Cannot import chromadb: {exc}")

    def _check_workspace_writable(self) -> InstallCheck:
        try:
            from app.core.config import settings
            taksh_dir = settings.TAKSH_DIR
            taksh_dir.mkdir(parents=True, exist_ok=True)
            probe = taksh_dir / ".install_probe"
            probe.write_text("ok")
            probe.unlink()
            return InstallCheck(
                "Workspace writable", "PASS",
                str(taksh_dir.resolve()),
            )
        except Exception as exc:
            return InstallCheck("Workspace writable", "FAIL", str(exc))

    def _check_docs_readable(self) -> InstallCheck:
        try:
            from app.core.config import settings
            docs_dir = settings.DOCS_DIR
            if docs_dir.exists() and docs_dir.is_dir():
                return InstallCheck(
                    "Docs directory readable", "PASS",
                    str(docs_dir.resolve()),
                )
            return InstallCheck(
                "Docs directory readable", "WARN",
                f"Not found at {docs_dir.resolve()} — knowledge ingestion may be limited",
            )
        except Exception as exc:
            return InstallCheck("Docs directory readable", "WARN", str(exc))

    def _check_env_file(self) -> InstallCheck:
        from pathlib import Path
        env = Path(".env")
        if env.exists():
            return InstallCheck(".env file", "PASS", str(env.resolve()))
        return InstallCheck(
            ".env file", "WARN",
            ".env not found — using environment variable defaults only",
        )

    def _check_required_packages(self) -> List[InstallCheck]:
        results = []
        for pkg in REQUIRED_PACKAGES:
            try:
                __import__(pkg)
                results.append(InstallCheck(f"Package: {pkg}", "PASS", "importable"))
            except ImportError as exc:
                results.append(InstallCheck(f"Package: {pkg}", "FAIL", str(exc)))
        return results


# Module-level singleton
installer_checker = InstallerChecker()
