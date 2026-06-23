"""
MS-19 system-level Pydantic schemas for health, metrics, config, info, and startup report endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ComponentHealthSchema(BaseModel):
    status: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricsResponse(BaseModel):
    conversation_count: int
    turn_count: int
    provider_requests: int
    provider_failures: int
    tool_executions: int
    memory_recalls: int
    knowledge_searches: int
    average_latency_ms: float
    active_sessions: int


# ---------------------------------------------------------------------------
# System Config
# ---------------------------------------------------------------------------

class ProviderConfigSchema(BaseModel):
    llm: str
    stt: str
    tts: str
    realtime: str


class SystemConfigResponse(BaseModel):
    version: str
    environment: str
    providers: ProviderConfigSchema
    api_v1_prefix: str
    host: str
    port: int
    log_level: str
    enable_provider_health_checks: bool
    max_prompt_chars: int
    max_knowledge_chunks: int
    max_memory_items: int
    max_episodes: int
    health_check_timeout_seconds: int


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------

class SystemInfoResponse(BaseModel):
    version: str
    uptime_seconds: float
    active_runtime_sessions: int
    active_voice_sessions: int
    active_provider_sessions: int
    memory_episodes: int
    open_tasks: int
    metrics_snapshots: int
    health: str


# ---------------------------------------------------------------------------
# Startup Report
# ---------------------------------------------------------------------------

class StartupCheckSchema(BaseModel):
    name: str
    critical: bool
    passed: bool
    detail: str = ""


class StartupReportResponse(BaseModel):
    checks: List[StartupCheckSchema]
    total: int
    passed: int
    failed: int


# ---------------------------------------------------------------------------
# MS-20: Readiness
# ---------------------------------------------------------------------------

class ReadinessResponse(BaseModel):
    status:        str    # "ready" | "degraded" | "not_ready"
    score:         int    # 0–100
    checks_passed: int
    checks_failed: int
    warnings:      int


# ---------------------------------------------------------------------------
# MS-20: Smoke Tests
# ---------------------------------------------------------------------------

class SmokeTestResultSchema(BaseModel):
    category:    str
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str = ""


class SmokeTestReportResponse(BaseModel):
    total:             int
    passed:            int
    failed:            int
    total_duration_ms: float
    results:           List[SmokeTestResultSchema]


# ---------------------------------------------------------------------------
# MS-20: Release Manifest
# ---------------------------------------------------------------------------

class ReleaseManifestResponse(BaseModel):
    version:               str
    release_type:          Optional[str] = None
    schema_version:        str
    build_date:            str
    completed_milestones:  Optional[List[str]] = None
    milestones_completed:  Optional[List[str]] = None


# ---------------------------------------------------------------------------
# MS-20: Backup Validation
# ---------------------------------------------------------------------------

class BackupValidateResponse(BaseModel):
    valid:            bool
    records_restored: int

