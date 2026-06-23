# Taksh Installation Guide

## Overview

Taksh is a local AI assistant backend built with FastAPI, SQLAlchemy, ChromaDB, and Gemini Live. This guide covers a fresh installation from source.

---

## Prerequisites

| Requirement | Minimum Version |
|-------------|----------------|
| Python | 3.11 |
| SQLite | 3.35 (with FTS5) |
| ChromaDB | 0.4.x |
| Git | 2.x |

---

## 1. Clone the Repository

```bash
git clone <repo-url> Taksh
cd Taksh/backend
```

---

## 2. Create a Python Environment

```bash
conda create -n taksh311 python=3.11
conda activate taksh311
pip install -r requirements.txt
```

Or with virtualenv:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

---

## 3. Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```ini
# Required for live Gemini provider
GEMINI_API_KEY=your_key_here

# Deployment profile: development | lab | production
TAKSH_PROFILE=development

# Paths (defaults work for local development)
TAKSH_DIR=./.taksh
CHROMA_DIR=./.taksh/chroma
LOG_DIR=./.taksh/logs

# Provider selection
DEFAULT_LLM_PROVIDER=mock        # Use 'gemini' with a valid API key
DEFAULT_STT_PROVIDER=mock
DEFAULT_TTS_PROVIDER=mock
DEFAULT_REALTIME_PROVIDER=gemini_live
```

> **Note:** Never commit `.env` to version control.

---

## 4. Database Migration

Run Alembic migrations to set up the database schema:

```bash
# Ensure you are in backend/
alembic upgrade head
```

Verify the migration succeeded:

```bash
alembic current
```

Expected output: `a1b2c3d4e5f6 (head)`

---

## 5. Verify Installation

Run the installation checker:

```bash
python -c "
from app.core.installer_check import installer_checker
results = installer_checker.run_all()
for r in results:
    print(f'[{r.status}] {r.name}: {r.detail}')
"
```

All critical checks should show `PASS`. `WARN` items are non-blocking.

---

## 6. First Startup

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify the server is running:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status": "healthy", "components": {...}}
```

---

## 7. Running Tests

```bash
python -m pytest app/tests/ -v
```

---

## Troubleshooting First Startup

- **`RuntimeError: Taksh startup aborted`** — A critical startup check failed. Run the startup report: `GET /api/v1/system/startup-report`.
- **`ModuleNotFoundError: No module named 'chromadb'`** — Run `pip install chromadb`.
- **`alembic: No such file or directory: alembic.ini`** — You must run commands from the `backend/` directory.
