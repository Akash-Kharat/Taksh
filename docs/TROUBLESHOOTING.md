# Taksh Troubleshooting Guide

## Quick Diagnostic Checklist

When something is wrong, run these first:

```bash
# 1. Health status
curl http://127.0.0.1:8000/api/v1/health

# 2. Startup report
curl http://127.0.0.1:8000/api/v1/system/startup-report

# 3. Readiness score
curl http://127.0.0.1:8000/api/v1/system/readiness

# 4. Smoke tests
curl -X POST http://127.0.0.1:8000/api/v1/system/smoke-test
```

---

## Common Issues

### Server Won't Start — `RuntimeError: Taksh startup aborted`

**Cause:** A critical startup check failed.

**Fix:**
1. Check the console output for the failing check name.
2. Run `GET /api/v1/system/startup-report` after fixing and restarting.

Common critical checks:
- `Database` — TAKSH_DIR is not writable or SQLite is not accessible.
- `Alembic Migration` — Run `alembic upgrade head`.
- `ChromaDB` — ChromaDB cannot be initialised. Check `CHROMA_DIR`.
- `Identity File` — `docs/Vision/taksh_identity.md` is missing.

---

### `ModuleNotFoundError` on Startup

**Cause:** Package not installed.

**Fix:**
```bash
pip install -r requirements.txt
```

Run the installer check:
```bash
python -c "
from app.core.installer_check import installer_checker
for r in installer_checker.run_all():
    if r.status != 'PASS':
        print(f'[{r.status}] {r.name}: {r.detail}')
"
```

---

### Health Returns `unhealthy` for `database`

**Cause:** SQLite file is locked, deleted, or permissions changed.

**Fix:**
1. Check `.taksh/taksh.db` exists and is not locked by another process.
2. Check file permissions.
3. If corrupted, restore from backup: see [BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md).

---

### Health Returns `degraded` for `knowledge`

**Cause:** ChromaDB cannot be reached or is initialising.

**Fix:**
1. Check `CHROMA_DIR` is set and the directory exists.
2. Restart the server — ChromaDB may need to reinitialise its index.
3. If the index is corrupt, delete `CHROMA_DIR` and re-ingest documents.

---

### `POST /system/smoke-test` Shows Failed Provider Tests

**Cause:** Mock providers not importable, or live provider key missing.

**Fix:**
- For `development` profile: Ensure `DEFAULT_LLM_PROVIDER=mock`.
- For `lab`/`production`: Set `GEMINI_API_KEY` in `.env`.

---

### `POST /system/backup/validate` Returns `valid: false`

**Cause:** Export or restore failed.

**Fix:**
1. Check the application log: `grep backup .taksh/logs/app.log | tail -20`
2. Ensure the database is not locked during the export.
3. Verify enough disk space is available.

---

### Alembic `Multiple head revisions` Error

**Cause:** Two migration branches exist.

**Fix:**
```bash
# Check heads
alembic heads

# Merge (replace <rev1> <rev2> with actual revision IDs)
alembic merge -m "merge_heads" <rev1> <rev2>

# Apply
alembic upgrade head
```

---

### Maintenance Tasks Not Running

**Cause:** Maintenance scheduler failed to start or crashed.

**Check:**
```bash
grep "maintenance" .taksh/logs/app.log | grep -E "ERROR|FAIL"
```

**Fix:** Restart the server. The scheduler starts automatically in the lifespan.

---

### ChromaDB `PermissionError` on Windows

**Cause:** ChromaDB holds a lock on `chroma.sqlite3` and another process is trying to delete it.

**Fix:** This is a known ChromaDB behaviour on Windows. It is non-fatal — the test runner will display a warning but tests complete successfully. Do not terminate mid-run.

---

## Diagnostic Commands

| Command | Purpose |
|---------|---------|
| `alembic current` | Show current migration revision |
| `alembic heads` | Show all migration heads |
| `alembic history` | Show migration history |
| `python -m pytest app/tests/ -v` | Run full test suite |
| `curl http://127.0.0.1:8000/api/v1/health` | Check health |
| `curl http://127.0.0.1:8000/api/v1/metrics` | Check metrics |
| `curl http://127.0.0.1:8000/api/v1/system/readiness` | Check readiness score |
| `curl http://127.0.0.1:8000/api/v1/system/info` | Check system info |

---

## Log Locations

| Log | Path |
|-----|------|
| Application | `.taksh/logs/app.log` |
| Console | stdout |

To increase log verbosity:
```ini
LOG_LEVEL=DEBUG
```

---

## Getting More Help

1. Check the startup report: `GET /api/v1/system/startup-report`
2. Check the readiness report: `GET /api/v1/system/readiness`
3. Run the installer check: see the Python snippet above
4. Run smoke tests: `POST /api/v1/system/smoke-test`
