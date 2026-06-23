"""
Taksh Startup Validation Framework — MS-19

Runs structured pre-flight checks at boot time.
Critical failures raise RuntimeError (fast-fail).
Non-critical failures are logged as warnings and boot continues.

Results are cached in `startup_results` and surfaced via
GET /api/v1/system/startup-report.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger("startup")

# Module-level cache — written once during lifespan startup, read by endpoint
startup_results: List["StartupCheck"] = []


@dataclass
class StartupCheck:
    name: str
    critical: bool
    passed: bool
    detail: str = ""


class StartupValidator:
    """Runs all startup checks and returns a list of StartupCheck results."""

    def validate_all(self) -> List[StartupCheck]:
        checks: List[StartupCheck] = []

        checks.append(self._check_database())
        checks.append(self._check_alembic_migration())
        checks.append(self._check_workspace_dir())
        checks.append(self._check_chromadb())
        checks.append(self._check_identity_file())
        checks.append(self._check_skills_dir())
        checks.append(self._check_llm_provider())
        checks.append(self._check_docs_dir())
        checks.append(self._check_fts5())

        # Cache results for the startup-report endpoint
        global startup_results
        startup_results = checks

        # Log summary
        passed  = [c for c in checks if c.passed]
        failed  = [c for c in checks if not c.passed]
        critical_failures = [c for c in failed if c.critical]

        for c in checks:
            icon = "✓" if c.passed else ("✗" if c.critical else "⚠")
            level = logging.INFO if c.passed else (logging.ERROR if c.critical else logging.WARNING)
            logger.log(level, f"{icon} Startup check [{c.name}]: {c.detail}")

        if critical_failures:
            names = ", ".join(c.name for c in critical_failures)
            raise RuntimeError(
                f"Taksh startup aborted — critical checks failed: {names}"
            )

        return checks

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_database(self) -> StartupCheck:
        try:
            from sqlalchemy import text as sa_text
            from app.core.database import engine
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            return StartupCheck("Database", critical=True, passed=True, detail="Reachable")
        except Exception as exc:
            return StartupCheck("Database", critical=True, passed=False, detail=str(exc))

    def _check_alembic_migration(self) -> StartupCheck:
        try:
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig
            import os

            cfg = AlembicConfig("alembic.ini")
            script = ScriptDirectory.from_config(cfg)
            head_revisions = set(script.get_heads())

            from app.core.database import engine
            with engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                current = set(ctx.get_current_heads())

            if current >= head_revisions:
                return StartupCheck("Alembic Migration", critical=True, passed=True, detail=f"Current: {current}")
            return StartupCheck(
                "Alembic Migration", critical=True, passed=False,
                detail=f"Pending migrations. Current={current}, Head={head_revisions}",
            )
        except Exception as exc:
            return StartupCheck("Alembic Migration", critical=True, passed=False, detail=str(exc))

    def _check_workspace_dir(self) -> StartupCheck:
        try:
            taksh_dir = settings.TAKSH_DIR
            taksh_dir.mkdir(parents=True, exist_ok=True)
            probe = taksh_dir / ".startup_probe"
            probe.write_text("ok")
            probe.unlink()
            return StartupCheck("Workspace Directory", critical=True, passed=True, detail=str(taksh_dir.resolve()))
        except Exception as exc:
            return StartupCheck("Workspace Directory", critical=True, passed=False, detail=str(exc))

    def _check_chromadb(self) -> StartupCheck:
        try:
            from app.services.knowledge.vector_store import ChromaDBClient
            ChromaDBClient()
            return StartupCheck("ChromaDB", critical=True, passed=True, detail="Initialised")
        except Exception as exc:
            return StartupCheck("ChromaDB", critical=True, passed=False, detail=str(exc))

    def _check_identity_file(self) -> StartupCheck:
        path = settings.IDENTITY_PATH
        if path.exists():
            return StartupCheck("Identity File", critical=True, passed=True, detail=str(path.resolve()))
        return StartupCheck(
            "Identity File", critical=True, passed=False,
            detail=f"Not found at {path.resolve()}",
        )

    def _check_skills_dir(self) -> StartupCheck:
        path = settings.SKILLS_MANIFEST_DIR
        if path.exists() and path.is_dir():
            count = len(list(path.glob("*.json")))
            return StartupCheck("Skills Directory", critical=False, passed=True, detail=f"{count} manifests found")
        return StartupCheck(
            "Skills Directory", critical=False, passed=False,
            detail=f"Directory not found at {path.resolve()}",
        )

    def _check_llm_provider(self) -> StartupCheck:
        provider = settings.DEFAULT_LLM_PROVIDER
        if provider:
            return StartupCheck("Default LLM Provider", critical=False, passed=True, detail=provider)
        return StartupCheck("Default LLM Provider", critical=False, passed=False, detail="DEFAULT_LLM_PROVIDER is empty")

    def _check_docs_dir(self) -> StartupCheck:
        path = settings.DOCS_DIR
        if path.exists() and path.is_dir():
            return StartupCheck("Docs Directory", critical=True, passed=True, detail=str(path.resolve()))
        return StartupCheck(
            "Docs Directory", critical=True, passed=False,
            detail=f"Not found at {path.resolve()}",
        )

    def _check_fts5(self) -> StartupCheck:
        try:
            import sqlite3
            con = sqlite3.connect(":memory:")
            cur = con.cursor()
            cur.execute("CREATE VIRTUAL TABLE _fts5_test USING fts5(content);")
            cur.execute("DROP TABLE _fts5_test;")
            con.close()
            return StartupCheck("SQLite FTS5", critical=True, passed=True, detail="Available")
        except Exception as exc:
            return StartupCheck("SQLite FTS5", critical=True, passed=False, detail=str(exc))
