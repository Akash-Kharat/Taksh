# Taksh Backup & Recovery Guide

## Overview

Taksh exports conversation history, memory episodes, projects, preferences, and open tasks. Backups include a versioning envelope to ensure restore compatibility.

> **Policy:** A backup is only considered valid if it can be successfully restored.

---

## What Is Backed Up

| Data | Included |
|------|---------|
| Conversation sessions and turns | ✓ |
| Memory episodes | ✓ |
| Projects and snapshots | ✓ |
| User preferences | ✓ |
| Open tasks | ✓ |
| API keys / secrets | ✗ Never |
| ChromaDB vectors | ✗ (re-index after restore) |

---

## Export Procedure

### Via API (ZIP download)

```bash
curl -O http://127.0.0.1:8000/api/v1/system/backup
```

The response is a `taksh_backup_<timestamp>.zip` containing a JSON export.

### Via Python (programmatic)

```python
from app.core.backup import backup_manager
from app.core.database import SessionLocal

with SessionLocal() as db:
    zip_bytes = backup_manager.export_zip(db)
    with open("backup.zip", "wb") as f:
        f.write(zip_bytes)
```

---

## Backup Validation

Always validate a backup before relying on it:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/backup/validate
```

Expected response:
```json
{
  "valid": true,
  "records_restored": 247
}
```

If `valid` is `false`, do not delete the previous backup.

---

## Restore Procedure

> [!WARNING]
> Restore overwrites the existing database. Always create a new backup first.

### Step 1: Back up the current database

```bash
cp .taksh/taksh.db .taksh/taksh.db.pre-restore
```

### Step 2: Unzip the backup

```bash
unzip taksh_backup_20260623_120000.zip -d restore_tmp/
```

### Step 3: Run the restore script

```python
import json
from app.core.backup_validator import backup_validator
from app.core.database import SessionLocal

with open("restore_tmp/taksh_backup_20260623_120000.json") as f:
    data = json.load(f)

# Verify the backup before restoring
print("Backup version:", data["backup_version"])
print("Schema version:", data["schema_version"])
print("Created at:", data["created_at"])
```

### Step 4: Re-run migrations after restore

```bash
alembic upgrade head
```

### Step 5: Re-index knowledge

After restoring, re-ingest documents into ChromaDB:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/ingest
```

---

## Recovery Validation

After restore, verify the system is healthy:

```bash
curl http://127.0.0.1:8000/api/v1/system/readiness
```

Expected: `score >= 95`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/smoke-test
```

Expected: `failed == 0`

---

## Backup Versioning

Each backup includes a metadata envelope:

```json
{
  "backup_version": "1",
  "taksh_version": "0.1",
  "created_at": "2026-06-23T12:00:00",
  "schema_version": "a1b2c3d4e5f6"
}
```

| Field | Purpose |
|-------|---------|
| `backup_version` | Backup format version |
| `taksh_version` | Taksh application version when backup was created |
| `schema_version` | Alembic migration head at backup time |
| `created_at` | UTC timestamp of export |

> If `schema_version` differs from the current head, run `alembic upgrade head` before restoring.

---

## Automated Backups

The maintenance scheduler runs every 15 minutes and persists a metrics snapshot. For full data backups, set up a cron job:

```
0 */6 * * * curl -s -o /backups/taksh_$(date +\%Y\%m\%d_\%H\%M\%S).zip \
  http://127.0.0.1:8000/api/v1/system/backup
```
