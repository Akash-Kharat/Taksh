# Taksh Deployment Guide

## Overview

This guide covers deploying Taksh in `lab` and `production` profiles, including profile selection, production checklist, and reverse proxy configuration.

---

## Deployment Profiles

Taksh supports three deployment profiles controlled by the `TAKSH_PROFILE` environment variable:

| Profile | Providers | Logging | Validation | Backup | Health Checks |
|---------|-----------|---------|------------|--------|---------------|
| `development` | Mock | DEBUG | Relaxed | Off | Off |
| `lab` | Live (Gemini) | INFO | Relaxed | Off | On |
| `production` | Live (Gemini) | WARNING | Strict | On | On |

### Set the Active Profile

In `.env`:
```ini
TAKSH_PROFILE=production
```

Or as an environment variable:
```bash
export TAKSH_PROFILE=production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Production Checklist

Before deploying to production, verify:

- [ ] `TAKSH_PROFILE=production` is set
- [ ] `GEMINI_API_KEY` is set and valid
- [ ] `DEFAULT_LLM_PROVIDER=gemini` (not mock)
- [ ] `ENABLE_PROVIDER_HEALTH_CHECKS=true`
- [ ] Alembic migration is current (`alembic upgrade head`)
- [ ] `.taksh/` directory is writable by the process user
- [ ] Log directory has sufficient disk space
- [ ] `GET /api/v1/system/readiness` returns `score >= 95`
- [ ] `POST /api/v1/system/smoke-test` all categories pass
- [ ] `POST /api/v1/system/backup/validate` returns `valid: true`

---

## Running as a Service (Windows)

Create a service wrapper using NSSM or a Task Scheduler entry:

```
Program: C:\miniconda3\envs\taksh311\python.exe
Arguments: -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Start in: D:\Taksh\backend
```

Set environment variable `TAKSH_PROFILE=lab` in the service's environment.

---

## Reverse Proxy (nginx)

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 120s;
}

location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TAKSH_PROFILE` | `development` | Active deployment profile |
| `GEMINI_API_KEY` | `` | Gemini API key (required for non-mock) |
| `DEFAULT_LLM_PROVIDER` | `mock` | LLM provider: `mock` or `gemini` |
| `TAKSH_DIR` | `./.taksh` | Storage root directory |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | `5` | Per-subsystem health check budget |
| `ENABLE_PROVIDER_HEALTH_CHECKS` | `true` | Run provider health monitoring |
| `MAX_PROMPT_CHARS` | `25000` | Maximum prompt length in characters |

---

## Release Verification

After deploying, verify the release is correct:

```bash
curl http://127.0.0.1:8000/api/v1/system/release
```

Expected:
```json
{
  "version": "0.1.0-rc1",
  "schema_version": "a1b2c3d4e5f6",
  "completed_milestones": ["MS-01", ..., "MS-20"]
}
```
