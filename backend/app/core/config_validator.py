"""
Taksh Configuration Validator — MS-20

Validates correctness of runtime configuration values across 5 domains:
  - Database
  - Workspace
  - Providers
  - Voice
  - Security

Unlike StartupValidator (which checks existence), ConfigValidator checks
that configured values are sane and consistent.
"""
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("config_validator")


@dataclass
class ConfigCheck:
    domain:  str
    name:    str
    passed:  bool
    detail:  str = ""


class ConfigValidator:
    """Validates correctness of the active Settings instance."""

    def validate_all(self) -> List[ConfigCheck]:
        from app.core.config import settings

        checks: List[ConfigCheck] = []

        # Database
        checks += self._check_database(settings)

        # Workspace
        checks += self._check_workspace(settings)

        # Providers
        checks += self._check_providers(settings)

        # Voice
        checks += self._check_voice(settings)

        # Security
        checks += self._check_security(settings)

        passed = sum(1 for c in checks if c.passed)
        failed = sum(1 for c in checks if not c.passed)
        logger.info(
            f"[config_validator] Completed: {passed} passed, {failed} failed"
        )
        return checks

    # ------------------------------------------------------------------
    # Domain: Database
    # ------------------------------------------------------------------

    def _check_database(self, settings) -> List[ConfigCheck]:
        results = []

        # 1. DB path exists (or can be created)
        try:
            db_path = settings.TAKSH_DIR / settings.DATABASE_NAME
            settings.TAKSH_DIR.mkdir(parents=True, exist_ok=True)
            results.append(ConfigCheck(
                domain="Database", name="Path exists",
                passed=True, detail=str(db_path.resolve()),
            ))
        except Exception as exc:
            results.append(ConfigCheck(
                domain="Database", name="Path exists",
                passed=False, detail=str(exc),
            ))
            # Can't test writability if path creation failed
            results.append(ConfigCheck(
                domain="Database", name="Path writable",
                passed=False, detail="Parent path check failed",
            ))
            return results

        # 2. DB path writable
        try:
            probe = settings.TAKSH_DIR / ".cfg_probe"
            probe.write_text("ok")
            probe.unlink()
            results.append(ConfigCheck(
                domain="Database", name="Path writable",
                passed=True, detail=str(settings.TAKSH_DIR.resolve()),
            ))
        except Exception as exc:
            results.append(ConfigCheck(
                domain="Database", name="Path writable",
                passed=False, detail=str(exc),
            ))

        # 3. Migration current
        try:
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig
            from app.core.database import engine

            cfg    = AlembicConfig("alembic.ini")
            script = ScriptDirectory.from_config(cfg)
            heads  = set(script.get_heads())

            with engine.connect() as conn:
                ctx     = MigrationContext.configure(conn)
                current = set(ctx.get_current_heads())

            if current >= heads:
                results.append(ConfigCheck(
                    domain="Database", name="Migration current",
                    passed=True, detail=f"head={','.join(sorted(heads))}",
                ))
            else:
                results.append(ConfigCheck(
                    domain="Database", name="Migration current",
                    passed=False,
                    detail=f"Pending migration. current={current}, head={heads}",
                ))
        except Exception as exc:
            results.append(ConfigCheck(
                domain="Database", name="Migration current",
                passed=False, detail=str(exc),
            ))

        return results

    # ------------------------------------------------------------------
    # Domain: Workspace
    # ------------------------------------------------------------------

    def _check_workspace(self, settings) -> List[ConfigCheck]:
        results = []

        ws = settings.TAKSH_DIR

        # Exists
        if ws.exists() and ws.is_dir():
            results.append(ConfigCheck(
                domain="Workspace", name="Directory exists",
                passed=True, detail=str(ws.resolve()),
            ))
        else:
            results.append(ConfigCheck(
                domain="Workspace", name="Directory exists",
                passed=False, detail=f"Not found: {ws.resolve()}",
            ))
            results.append(ConfigCheck(
                domain="Workspace", name="Readable",
                passed=False, detail="Parent directory not found",
            ))
            return results

        # Readable (list directory)
        try:
            list(ws.iterdir())
            results.append(ConfigCheck(
                domain="Workspace", name="Readable",
                passed=True, detail="OK",
            ))
        except Exception as exc:
            results.append(ConfigCheck(
                domain="Workspace", name="Readable",
                passed=False, detail=str(exc),
            ))

        return results

    # ------------------------------------------------------------------
    # Domain: Providers
    # ------------------------------------------------------------------

    def _check_providers(self, settings) -> List[ConfigCheck]:
        results = []

        # Configured
        configured = bool(settings.DEFAULT_LLM_PROVIDER.strip())
        results.append(ConfigCheck(
            domain="Providers", name="Configured",
            passed=configured,
            detail=settings.DEFAULT_LLM_PROVIDER if configured else "DEFAULT_LLM_PROVIDER is empty",
        ))

        # Timeout valid: 0 < t <= 300
        t = settings.PROVIDER_REQUEST_TIMEOUT_SECONDS
        timeout_ok = 0 < t <= 300
        results.append(ConfigCheck(
            domain="Providers", name="Timeout valid",
            passed=timeout_ok,
            detail=f"{t}s" if timeout_ok else f"Invalid timeout: {t}s (must be 1–300)",
        ))

        return results

    # ------------------------------------------------------------------
    # Domain: Voice
    # ------------------------------------------------------------------

    def _check_voice(self, settings) -> List[ConfigCheck]:
        results = []

        # Sample rate: 8000–48000 Hz
        sr = settings.VOICE_SAMPLE_RATE
        sr_ok = 8000 <= sr <= 48000
        results.append(ConfigCheck(
            domain="Voice", name="Sample rate valid",
            passed=sr_ok,
            detail=f"{sr} Hz" if sr_ok else f"Invalid sample rate: {sr} Hz (8000–48000)",
        ))

        # Buffer size > 0
        buf = settings.VOICE_BUFFER_SIZE_FRAMES
        buf_ok = buf > 0
        results.append(ConfigCheck(
            domain="Voice", name="Buffer size valid",
            passed=buf_ok,
            detail=f"{buf} frames" if buf_ok else f"Invalid buffer size: {buf}",
        ))

        return results

    # ------------------------------------------------------------------
    # Domain: Security
    # ------------------------------------------------------------------

    def _check_security(self, settings) -> List[ConfigCheck]:
        results = []

        # API key present when LLM provider is not mock
        llm = settings.DEFAULT_LLM_PROVIDER
        if llm != "mock":
            key_present = bool(settings.GEMINI_API_KEY.strip())
            results.append(ConfigCheck(
                domain="Security", name="API key present",
                passed=key_present,
                detail="GEMINI_API_KEY set" if key_present
                       else f"GEMINI_API_KEY missing for provider '{llm}'",
            ))
        else:
            results.append(ConfigCheck(
                domain="Security", name="API key present",
                passed=True,
                detail="Skipped — mock provider active",
            ))

        # Defaults not used in production
        profile = settings.TAKSH_PROFILE.lower()
        if profile == "production":
            using_mock = (llm == "mock")
            results.append(ConfigCheck(
                domain="Security", name="Production defaults check",
                passed=not using_mock,
                detail="OK" if not using_mock
                       else "Mock providers must not be used in production profile",
            ))
        else:
            results.append(ConfigCheck(
                domain="Security", name="Production defaults check",
                passed=True,
                detail=f"Skipped — profile is '{profile}'",
            ))

        return results


# Module-level singleton
config_validator = ConfigValidator()
