"""
Taksh Unified Health Manager — MS-19

Aggregates real-time health status from all subsystems.
Every check runs under HEALTH_CHECK_TIMEOUT_SECONDS.
Timeout or exception → DEGRADED, never crashes the caller.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger("health")


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Individual probe helpers (sync, called inside asyncio.wait_for wrappers)
# ---------------------------------------------------------------------------

async def _probe_database(db: Session) -> ComponentHealth:
    try:
        db.execute(text("SELECT 1"))
        return ComponentHealth("database", HealthStatus.HEALTHY, "OK")
    except Exception as exc:
        logger.error(f"[health] database probe failed: {exc}")
        return ComponentHealth("database", HealthStatus.UNHEALTHY, str(exc))


async def _probe_memory() -> ComponentHealth:
    try:
        from app.services.memory.manager import MemoryManager
        MemoryManager()  # singleton init
        return ComponentHealth("memory", HealthStatus.HEALTHY, "OK")
    except Exception as exc:
        logger.error(f"[health] memory probe failed: {exc}")
        return ComponentHealth("memory", HealthStatus.DEGRADED, str(exc))


async def _probe_knowledge() -> ComponentHealth:
    try:
        from app.services.knowledge.vector_store import ChromaDBClient
        ChromaDBClient()
        return ComponentHealth("knowledge", HealthStatus.HEALTHY, "OK")
    except Exception as exc:
        logger.error(f"[health] knowledge probe failed: {exc}")
        return ComponentHealth("knowledge", HealthStatus.DEGRADED, str(exc))


async def _probe_providers(db: Session) -> ComponentHealth:
    try:
        from app.models.database_models import ProviderHealthRecord
        from sqlalchemy import desc
        record = (
            db.query(ProviderHealthRecord)
            .order_by(desc(ProviderHealthRecord.created_at))
            .first()
        )
        if record is None:
            return ComponentHealth("providers", HealthStatus.DEGRADED, "No health records yet")
        if record.healthy:
            return ComponentHealth("providers", HealthStatus.HEALTHY, "OK")
        return ComponentHealth("providers", HealthStatus.DEGRADED, record.error_message or "Last check failed")
    except Exception as exc:
        logger.error(f"[health] provider probe failed: {exc}")
        return ComponentHealth("providers", HealthStatus.DEGRADED, str(exc))


async def _probe_workspace() -> ComponentHealth:
    try:
        taksh_dir = settings.TAKSH_DIR
        taksh_dir.mkdir(parents=True, exist_ok=True)
        test_file = taksh_dir / ".health_probe"
        test_file.write_text("ok")
        test_file.unlink()
        return ComponentHealth("workspace", HealthStatus.HEALTHY, "OK")
    except Exception as exc:
        logger.error(f"[health] workspace probe failed: {exc}")
        return ComponentHealth("workspace", HealthStatus.DEGRADED, str(exc))


async def _probe_runtime() -> ComponentHealth:
    try:
        from app.services.runtime.state_machine import active_state_machines
        count = len(active_state_machines)
        return ComponentHealth("runtime", HealthStatus.HEALTHY, f"{count} active state machine(s)")
    except Exception as exc:
        logger.error(f"[health] runtime probe failed: {exc}")
        return ComponentHealth("runtime", HealthStatus.DEGRADED, str(exc))


async def _probe_tools() -> ComponentHealth:
    try:
        from app.services.tools import tool_registry  # type: ignore
        return ComponentHealth("tools", HealthStatus.HEALTHY, "OK")
    except ImportError:
        # tool_registry may not expose a direct import; fall back to directory check
        import os
        tools_dir = settings.TAKSH_DIR.parent / "app" / "services" / "tools"
        if tools_dir.exists():
            return ComponentHealth("tools", HealthStatus.HEALTHY, "tools directory present")
        return ComponentHealth("tools", HealthStatus.DEGRADED, "tools directory not found")
    except Exception as exc:
        logger.error(f"[health] tools probe failed: {exc}")
        return ComponentHealth("tools", HealthStatus.DEGRADED, str(exc))


# ---------------------------------------------------------------------------
# HealthManager
# ---------------------------------------------------------------------------

class HealthManager:
    """Aggregates health status from all Taksh subsystems with per-check timeouts."""

    async def _run_with_timeout(
        self,
        probe,
        name: str,
        *args,
        **kwargs,
    ) -> ComponentHealth:
        """Run a probe coroutine under HEALTH_CHECK_TIMEOUT_SECONDS."""
        timeout = float(settings.HEALTH_CHECK_TIMEOUT_SECONDS)
        try:
            return await asyncio.wait_for(probe(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"[health] {name} probe timed out after {timeout}s")
            return ComponentHealth(name, HealthStatus.DEGRADED, f"Timed out after {timeout}s")
        except Exception as exc:
            logger.error(f"[health] {name} probe raised unexpected error: {exc}")
            return ComponentHealth(name, HealthStatus.DEGRADED, str(exc))

    async def get_health(self, db: Session) -> Dict:
        """
        Run all subsystem probes and return aggregated health status.

        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "components": { "database": "healthy", ... }
            }
        """
        results: list[ComponentHealth] = await asyncio.gather(
            self._run_with_timeout(_probe_database, "database", db),
            self._run_with_timeout(_probe_memory, "memory"),
            self._run_with_timeout(_probe_knowledge, "knowledge"),
            self._run_with_timeout(_probe_providers, "providers", db),
            self._run_with_timeout(_probe_workspace, "workspace"),
            self._run_with_timeout(_probe_runtime, "runtime"),
            self._run_with_timeout(_probe_tools, "tools"),
        )

        components = {r.name: r.status.value for r in results}

        # Overall status = worst-of-components
        statuses = [r.status for r in results]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "components": components,
        }


# Module-level singleton
health_manager = HealthManager()
