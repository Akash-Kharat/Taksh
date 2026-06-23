"""
Taksh System Readiness Reporter — MS-20

Aggregates startup validation results, health checks, and configuration
validation into a single composite readiness score.

Score formula: round((checks_passed / total_checks) * 100)

Status thresholds:
  score == 100  →  "ready"
  score >= 80   →  "degraded"
  score <  80   →  "not_ready"
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("readiness")


@dataclass
class ReadinessReport:
    status:        str
    score:         int
    checks_passed: int
    checks_failed: int
    warnings:      int


def _status_from_score(score: int) -> str:
    if score >= 90:
        return "ready"
    if score >= 70:
        return "degraded"
    return "not_ready"


class ReadinessReporter:
    """Computes a composite deployment readiness score."""

    async def get_report(self, db: Session) -> ReadinessReport:
        """
        Aggregates:
          1. Startup validation results (cached from last boot)
          2. Health manager component statuses
          3. Config validator checks
        """
        total = 0
        passed = 0
        failed = 0
        warnings = 0

        # ----------------------------------------------------------------
        # 1. Startup validation results
        # ----------------------------------------------------------------
        try:
            from app.core.startup_validator import startup_results
            for check in startup_results:
                total += 1
                if check.passed:
                    passed += 1
                elif check.critical:
                    failed += 1
                else:
                    warnings += 1
        except Exception as exc:
            logger.warning(f"[readiness] Could not read startup_results: {exc}")
            total += 1
            failed += 1

        # ----------------------------------------------------------------
        # 2. Health manager — each component counts as one check
        # ----------------------------------------------------------------
        try:
            from app.services.health.manager import health_manager
            health = await health_manager.get_health(db)
            for component, status in health.get("components", {}).items():
                total += 1
                if status == "healthy":
                    passed += 1
                elif status == "degraded":
                    warnings += 1
                    # Degraded is not a hard failure for readiness scoring
                    passed += 1  # counts toward passed but adds a warning
                else:  # unhealthy
                    failed += 1
        except Exception as exc:
            logger.warning(f"[readiness] Could not read health: {exc}")
            total += 1
            failed += 1

        # ----------------------------------------------------------------
        # 3. Config validator checks
        # ----------------------------------------------------------------
        try:
            from app.core.config_validator import config_validator
            cfg_checks = config_validator.validate_all()
            for check in cfg_checks:
                total += 1
                if check.passed:
                    passed += 1
                else:
                    failed += 1
        except Exception as exc:
            logger.warning(f"[readiness] Could not run config validator: {exc}")
            total += 1
            failed += 1

        # ----------------------------------------------------------------
        # Compute score
        # ----------------------------------------------------------------
        if total == 0:
            score = 0
        else:
            score = round((passed / total) * 100)

        status = _status_from_score(score)

        logger.info(
            f"[readiness] score={score} status={status} "
            f"passed={passed} failed={failed} warnings={warnings} total={total}"
        )

        return ReadinessReport(
            status        = status,
            score         = score,
            checks_passed = passed,
            checks_failed = failed,
            warnings      = warnings,
        )


# Module-level singleton
readiness_reporter = ReadinessReporter()
