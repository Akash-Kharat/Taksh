# Taksh Operations Guide

## Overview

Day-to-day operational procedures for running Taksh in production or lab environments.

---

## Health Checks

### API Health Endpoint

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "memory": "healthy",
    "knowledge": "healthy",
    "providers": "healthy",
    "workspace": "healthy",
    "runtime": "healthy",
    "tools": "healthy"
  }
}
```

| Status | Meaning |
|--------|---------|
| `healthy` | Component operating normally |
| `degraded` | Component partially functional — investigation recommended |
| `unhealthy` | Component is down — immediate action required |

### Readiness Score

```bash
curl http://127.0.0.1:8000/api/v1/system/readiness
```

- `score >= 95` — Ready for production traffic
- `score >= 80` — Degraded but operational
- `score < 80` — Not ready — investigate before routing traffic

### Startup Report

View pre-flight check results from the most recent boot:

```bash
curl http://127.0.0.1:8000/api/v1/system/startup-report
```

---

## Metrics

### Current Metrics

```bash
curl http://127.0.0.1:8000/api/v1/metrics
```

Response fields:

| Field | Description |
|-------|-------------|
| `conversation_count` | Total conversations started |
| `turn_count` | Total conversation turns |
| `provider_requests` | Total LLM/STT/TTS requests |
| `provider_failures` | Total provider errors |
| `tool_executions` | Total tool invocations |
| `memory_recalls` | Total memory retrievals |
| `knowledge_searches` | Total knowledge queries |
| `average_latency_ms` | Rolling average response latency |
| `active_sessions` | Currently active sessions |

### Metrics Persistence

Metrics are persisted every 15 minutes by the maintenance scheduler. On restart, the last snapshot is hydrated automatically.

---

## Provider Monitoring

### Provider Health Records

Provider health checks run automatically if `ENABLE_PROVIDER_HEALTH_CHECKS=true`.

Records older than `PROVIDER_HEALTH_RETENTION_DAYS` (default: 30) are automatically pruned by the maintenance scheduler.

### Switching Providers

Update `.env` and restart:

```ini
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_STT_PROVIDER=mock
DEFAULT_TTS_PROVIDER=mock
```

---

## Maintenance Tasks

The maintenance scheduler runs every 5 minutes in the background. Each task runs in isolation — one failure never blocks others.

| Task | Frequency | Description |
|------|-----------|-------------|
| Cleanup expired approvals | Every cycle | Removes tool approvals past `APPROVAL_EXPIRATION_HOURS` |
| Cleanup old health records | Every cycle | Prunes records older than `HEALTH_HISTORY_RETENTION_DAYS` |
| Cleanup abandoned sessions | Every cycle | Marks sessions inactive for > 2 hours as closed |
| Cleanup temporary memory | Every cycle | Removes transient cache entries |
| Persist metrics snapshot | Every 3rd cycle (~15 min) | Saves current metrics to `MetricsSnapshot` table |

### Verifying Maintenance Is Running

Check the maintenance scheduler log:

```bash
grep "maintenance" .taksh/logs/app.log | tail -20
```

---

## Smoke Tests

Run a full-stack validation at any time:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/smoke-test
```

This tests: Runtime · Memory · Knowledge · Providers · Conversation

---

## System Information

```bash
curl http://127.0.0.1:8000/api/v1/system/info
```

Returns uptime, active session counts, episode count, and overall health status.

---

## Log Locations

| Log | Location |
|-----|----------|
| Application log | `.taksh/logs/app.log` |
| Console output | stdout (when running with uvicorn) |

Log level is controlled by `LOG_LEVEL` (default: `INFO`). Set `LOG_LEVEL=DEBUG` for verbose output.

---

## Graceful Shutdown

Taksh handles SIGTERM gracefully. The maintenance scheduler and health monitor are stopped cleanly before the process exits.

```bash
# Send SIGTERM
kill -15 <uvicorn_pid>
```
