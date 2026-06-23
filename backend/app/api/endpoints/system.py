"""
MS-19 System diagnostics endpoints:
  GET /api/v1/system/config          — sanitised configuration snapshot
  GET /api/v1/system/info            — uptime, DB counts, health status
  GET /api/v1/system/backup          — ZIP file download of full export
  GET /api/v1/system/startup-report  — cached startup validation results
"""
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logger import api_logger
from app.core.backup import backup_manager
from app.schemas.system import (
    SystemConfigResponse,
    SystemInfoResponse,
    ProviderConfigSchema,
    StartupReportResponse,
    StartupCheckSchema,
    ReadinessResponse,
    SmokeTestReportResponse,
    SmokeTestResultSchema,
    ReleaseManifestResponse,
    BackupValidateResponse,
)


router = APIRouter(prefix="/system", tags=["System Diagnostics"])

# Track server start time for uptime calculation
_SERVER_START_TIME = time.monotonic()


# ---------------------------------------------------------------------------
# GET /api/v1/system/config
# ---------------------------------------------------------------------------

@router.get("/config", response_model=SystemConfigResponse)
def get_system_config():
    """
    Returns a sanitised configuration snapshot.
    API keys and secrets are NEVER included in the response.
    """
    api_logger.info("Serving system config snapshot")
    return SystemConfigResponse(
        version                       = "0.1",
        environment                   = "development",
        providers                     = ProviderConfigSchema(
            llm      = settings.DEFAULT_LLM_PROVIDER,
            stt      = settings.DEFAULT_STT_PROVIDER,
            tts      = settings.DEFAULT_TTS_PROVIDER,
            realtime = settings.DEFAULT_REALTIME_PROVIDER,
        ),
        api_v1_prefix                 = settings.API_V1_STR,
        host                          = settings.HOST,
        port                          = settings.PORT,
        log_level                     = settings.LOG_LEVEL,
        enable_provider_health_checks = settings.ENABLE_PROVIDER_HEALTH_CHECKS,
        max_prompt_chars              = settings.MAX_PROMPT_CHARS,
        max_knowledge_chunks          = settings.MAX_KNOWLEDGE_CHUNKS,
        max_memory_items              = settings.MAX_MEMORY_ITEMS,
        max_episodes                  = settings.MAX_EPISODES,
        health_check_timeout_seconds  = settings.HEALTH_CHECK_TIMEOUT_SECONDS,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/system/info
# ---------------------------------------------------------------------------

@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(db: Session = Depends(get_db)):
    """
    Returns aggregated system diagnostics: uptime, active sessions, DB counts, health status.
    """
    api_logger.info("Serving system info")
    from app.models.database_models import (
        ConversationRuntimeSession,
        VoiceSession,
        ProviderSession,
        MemoryEpisode,
        OpenTask,
        MetricsSnapshot,
    )
    from app.services.health.manager import health_manager

    uptime = round(time.monotonic() - _SERVER_START_TIME, 2)

    active_runtime  = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.conversation_session_state == "active"
    ).count()

    active_voice = db.query(VoiceSession).filter(
        VoiceSession.state == "active"
    ).count() if hasattr(VoiceSession, "state") else 0

    active_providers = db.query(ProviderSession).filter(
        ProviderSession.provider_state.in_(["connected", "active", "streaming"])
    ).count()

    episode_count   = db.query(MemoryEpisode).count()
    open_task_count = db.query(OpenTask).filter(OpenTask.status == "OPEN").count()
    snapshots_count = db.query(MetricsSnapshot).count()

    health_result = await health_manager.get_health(db)

    return SystemInfoResponse(
        version                  = "0.1",
        uptime_seconds           = uptime,
        active_runtime_sessions  = active_runtime,
        active_voice_sessions    = active_voice,
        active_provider_sessions = active_providers,
        memory_episodes          = episode_count,
        open_tasks               = open_task_count,
        metrics_snapshots        = snapshots_count,
        health                   = health_result["status"],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/system/backup
# ---------------------------------------------------------------------------

@router.get("/backup")
def get_backup(db: Session = Depends(get_db)):
    """
    Streams a ZIP archive of all exportable data.
    No secrets or API keys are included.
    """
    api_logger.info("Generating system backup export")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename  = f"taksh_backup_{timestamp}.zip"

    zip_bytes = backup_manager.export_zip(db)

    def _iter():
        yield zip_bytes

    return StreamingResponse(
        _iter(),
        media_type   = "application/zip",
        headers      = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# GET /api/v1/system/startup-report
# ---------------------------------------------------------------------------

@router.get("/startup-report", response_model=StartupReportResponse)
def get_startup_report():
    """
    Returns the cached startup validation results from the most recent boot.
    Useful for diagnostics and operational support.
    """
    api_logger.info("Serving startup validation report")
    from app.core.startup_validator import startup_results

    checks = [
        StartupCheckSchema(
            name     = c.name,
            critical = c.critical,
            passed   = c.passed,
            detail   = c.detail,
        )
        for c in startup_results
    ]
    passed = sum(1 for c in checks if c.passed)
    return StartupReportResponse(
        checks = checks,
        total  = len(checks),
        passed = passed,
        failed = len(checks) - passed,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/system/readiness  (MS-20)
# ---------------------------------------------------------------------------

@router.get("/readiness", response_model=ReadinessResponse)
async def get_readiness(db: Session = Depends(get_db)):
    """
    Returns a composite deployment readiness score aggregating startup
    validation results, health checks, and configuration validation.
    """
    api_logger.info("Serving system readiness report")
    from app.core.readiness import readiness_reporter
    report = await readiness_reporter.get_report(db)
    return ReadinessResponse(
        status        = report.status,
        score         = report.score,
        checks_passed = report.checks_passed,
        checks_failed = report.checks_failed,
        warnings      = report.warnings,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/system/smoke-test  (MS-20)
# ---------------------------------------------------------------------------

@router.post("/smoke-test", response_model=SmokeTestReportResponse)
def run_smoke_test(db: Session = Depends(get_db)):
    """
    Runs the full deployment smoke test suite covering Runtime, Memory,
    Knowledge, Provider, and Conversation categories.
    """
    api_logger.info("Running smoke test suite")
    from app.core.smoke_tests import smoke_test_runner
    report = smoke_test_runner.run_all(db)
    return SmokeTestReportResponse(
        total             = report.total,
        passed            = report.passed,
        failed            = report.failed,
        total_duration_ms = report.total_duration_ms,
        results           = [
            SmokeTestResultSchema(
                category    = r.category,
                name        = r.name,
                passed      = r.passed,
                duration_ms = r.duration_ms,
                detail      = r.detail,
            )
            for r in report.results
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/system/release  (MS-20)
# ---------------------------------------------------------------------------

@router.get("/release", response_model=ReleaseManifestResponse)
def get_release():
    """
    Returns the release manifest: version, schema_version, build_date,
    and list of completed milestones.
    """
    api_logger.info("Serving release manifest")
    from app.core.release_manifest import get_manifest
    manifest = get_manifest()
    milestones = manifest.get("milestones_completed", manifest.get("completed_milestones", []))
    return ReleaseManifestResponse(
        version              = manifest.get("version"),
        release_type         = manifest.get("release_type", "production"),
        schema_version       = manifest.get("schema_version"),
        build_date           = manifest.get("build_date"),
        completed_milestones = milestones,
        milestones_completed = milestones,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/system/backup/validate  (MS-20)
# ---------------------------------------------------------------------------

@router.post("/backup/validate", response_model=BackupValidateResponse)
def validate_backup(db: Session = Depends(get_db)):
    """
    Exports a backup and restores it into a temporary database to verify
    integrity. Returns valid=True only if the full restore cycle succeeds.
    """
    api_logger.info("Running backup restore validation")
    from app.core.backup_validator import backup_validator
    result = backup_validator.validate(db)
    return BackupValidateResponse(
        valid            = result.valid,
        records_restored = result.records_restored,
    )
