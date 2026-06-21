import pytest
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.core.config import settings
from app.models.database_models import WorkspaceSnapshot, WorkspaceEvent, CognitiveTrace
from app.services.workspace.scanner import RepositoryScanner
from app.services.workspace.git import GitIntelligence
from app.services.workspace.manager import WorkspaceManager
from app.services.cognitive.selector import SkillSelector
from app.services.cognitive.orchestrator import CognitiveOrchestrator

def test_repository_scanner_basic(tmp_path):
    # Setup mock workspace files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Python files
    (src_dir / "main.py").write_text("import fastapi", encoding="utf-8")
    (src_dir / "utils.py").write_text("def run(): pass", encoding="utf-8")
    
    # JS file
    (tmp_path / "index.js").write_text("console.log('hello')", encoding="utf-8")
    
    # ignored directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("some git config", encoding="utf-8")

    # framework files
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi==0.100.0\npytest", encoding="utf-8")

    scanner = RepositoryScanner(workspace_dir=tmp_path)
    languages, frameworks, scan_limit_reached = scanner.scan()

    # Assertions
    lang_map = {l["language"]: l["file_count"] for l in languages}
    assert lang_map.get("Python") == 2
    assert lang_map.get("JavaScript") == 1
    assert "FastAPI" in frameworks
    assert not scan_limit_reached

def test_repository_scanner_depth_limit(tmp_path):
    # Create a deep path (more than MAX_SCAN_DEPTH)
    current_dir = tmp_path
    for i in range(5):
        current_dir = current_dir / f"depth_{i}"
        current_dir.mkdir()
    
    # Write a file in the deep path
    (current_dir / "deep_file.py").write_text("print('deep')", encoding="utf-8")

    # Set settings limits for testing
    settings.MAX_SCAN_DEPTH = 3

    scanner = RepositoryScanner(workspace_dir=tmp_path)
    languages, frameworks, scan_limit_reached = scanner.scan()

    # The deep file should be ignored since depth (5) > limit (3)
    lang_map = {l["language"]: l["file_count"] for l in languages}
    assert "Python" not in lang_map
    assert scan_limit_reached

def test_repository_scanner_file_limit(tmp_path):
    # Create many files
    for i in range(10):
        (tmp_path / f"file_{i}.py").write_text("pass", encoding="utf-8")

    # Set settings limit low
    settings.MAX_SCAN_FILES = 5

    scanner = RepositoryScanner(workspace_dir=tmp_path)
    languages, frameworks, scan_limit_reached = scanner.scan()

    assert scan_limit_reached
    total_files = sum(l["file_count"] for l in languages)
    # The scan should abort after meeting settings.MAX_SCAN_FILES
    assert total_files <= 6  # May scan 1 more on the last iteration but aborts

@patch("subprocess.run")
def test_git_intelligence_parsing(mock_run, tmp_path):
    # Mock Git rev-parse (is repo check)
    mock_is_repo = MagicMock()
    mock_is_repo.returncode = 0
    mock_is_repo.stdout = "true"

    # Mock Git branch
    mock_branch = MagicMock()
    mock_branch.returncode = 0
    mock_branch.stdout = "feature/workspace-telemetry\n"

    # Mock Git status
    mock_status = MagicMock()
    mock_status.returncode = 0
    mock_status.stdout = " M backend/app/main.py\n?? untracked_file.txt\nA  staged_file.py\n"

    # Mock Git log
    mock_log = MagicMock()
    mock_log.returncode = 0
    mock_log.stdout = (
        "commit1sha|Author Name|Commit message 1|2026-06-21 12:00:00 +0530\n"
        "commit2sha|Author Name|Commit message 2|2026-06-21 11:30:00 +0530\n"
    )

    mock_run.side_effect = [mock_is_repo, mock_branch, mock_status, mock_log]

    git_intel = GitIntelligence(workspace_dir=tmp_path)
    info = git_intel.get_git_info()

    assert info["branch"] == "feature/workspace-telemetry"
    assert "backend/app/main.py" in info["status"]["modified"]
    assert "staged_file.py" in info["status"]["staged"]
    assert "untracked_file.txt" in info["status"]["untracked"]
    
    assert len(info["recent_commits"]) == 2
    assert info["recent_commits"][0]["sha"] == "commit1sha"
    assert info["recent_commits"][0]["message"] == "Commit message 1"

def test_workspace_manager_truncation_and_hash(db_session, tmp_path):
    manager = WorkspaceManager(workspace_dir=tmp_path)
    
    # 1. Truncation test
    large_selection = "a" * 6000
    snapshot = manager.create_snapshot(
        db=db_session,
        active_file_path="main.py",
        selection_content=large_selection
    )
    assert len(snapshot.selection_content) == 5000
    assert snapshot.selection_truncated is True

    # 2. Hash consistency test
    snapshot2 = manager.create_snapshot(
        db=db_session,
        active_file_path="main.py",
        selection_content="some code"
    )
    
    # Re-creating with exact same state (but selection_content changes slightly)
    # The workspace hash checks active file path, git branch/status, framework, lang
    # If we call it again after rate-limit window or mock rate-limit to be bypassable
    settings.MIN_SNAPSHOT_INTERVAL_SECONDS = 0
    
    snapshot3 = manager.create_snapshot(
        db=db_session,
        active_file_path="main.py",
        selection_content="some code"
    )
    
    # Since all parameters are identical, it should reuse snapshot2 or generate the same hash
    assert snapshot3.workspace_hash == snapshot2.workspace_hash

def test_workspace_manager_rate_limiting(db_session, tmp_path):
    manager = WorkspaceManager(workspace_dir=tmp_path)
    settings.MIN_SNAPSHOT_INTERVAL_SECONDS = 5

    snapshot1 = manager.create_snapshot(db=db_session, active_file_path="main.py")
    
    # Call immediately again - should rate limit and return the exact same instance
    snapshot2 = manager.create_snapshot(db=db_session, active_file_path="modified.py")
    assert snapshot1.snapshot_id == snapshot2.snapshot_id
    assert snapshot2.active_file_path == "main.py"  # Reused from snapshot1

def test_workspace_events_and_retention(db_session):
    manager = WorkspaceManager()
    
    # Clear any leftover events
    db_session.query(WorkspaceEvent).delete()
    db_session.commit()

    # Create active error
    event1 = manager.log_event(
        db=db_session,
        event_type="test_failure",
        source="pytest",
        severity="error",
        message="test_llm_gateway FAILED",
        details={"traceback": "AssertionError"}
    )
    
    # Create a resolved error
    event2 = manager.log_event(
        db=db_session,
        event_type="build_failure",
        source="webpack",
        severity="critical",
        message="Webpack compilation failed",
        details={}
    )
    event2.resolved = True
    db_session.commit()

    # Create an old active error (older than retention window 30 days)
    event3 = manager.log_event(
        db=db_session,
        event_type="runtime_error",
        source="backend",
        severity="error",
        message="Old error message",
        details={}
    )
    event3.created_at = datetime.utcnow() - timedelta(days=35)
    db_session.commit()

    # Fetch active errors
    active = manager.get_active_errors(db_session)
    assert len(active) == 1
    assert active[0].event_id == event1.event_id

    # Resolve event
    manager.resolve_events(db_session, event_ids=[event1.event_id])
    assert len(manager.get_active_errors(db_session)) == 0

def test_skill_selector_workspace_boosts():
    selector = SkillSelector()
    
    # Create mock snapshot
    mock_snapshot = MagicMock()
    mock_snapshot.detected_languages = [{"language": "Python", "file_count": 5}]
    mock_snapshot.detected_frameworks = ["FastAPI"]

    # Create mock active error
    mock_error = MagicMock()
    mock_error.message = "AssertionError in django tests"
    mock_error.details = {}

    # Query with django keywords
    # Without boost
    top_skills_no_boost = selector.select_skills(query="How do I write models?", active_file="main.py")
    
    # With boost (Django matches the active error and framework matches)
    top_skills_boost = selector.select_skills(
        query="How do I write models?",
        active_file="main.py",
        workspace_snapshot=mock_snapshot,
        active_errors=[mock_error]
    )

    # Fullstack skill should have a higher score in top_skills_boost
    fullstack_no_boost = next((s for s in top_skills_no_boost if "Full-Stack" in s["skill"]), None)
    fullstack_boost = next((s for s in top_skills_boost if "Full-Stack" in s["skill"]), None)

    if fullstack_no_boost and fullstack_boost:
        # Full stack matches .py extension (+5) and query keywords (+2 * matches)
        # In boost, it matches language match (+3), and error matching keywords (+5)
        assert fullstack_boost["score"] > fullstack_no_boost["score"]

def test_api_workspace_endpoints(client, db_session):
    # Clear events
    db_session.query(WorkspaceEvent).delete()
    db_session.commit()

    # POST snapshot
    payload = {
        "session_id": "test-ws-session",
        "active_file_path": "backend/app/main.py",
        "active_file_language": "Python",
        "cursor_line": 42,
        "cursor_column": 10,
        "selection_content": "app = FastAPI()"
    }
    response = client.post("/api/v1/workspace/snapshot", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["active_file_path"] == "backend/app/main.py"
    assert data["git_branch"] != "none"
    
    # GET current
    response = client.get("/api/v1/workspace/current?session_id=test-ws-session")
    assert response.status_code == 200
    assert response.json()["snapshot_id"] == data["snapshot_id"]

    # GET info
    response = client.get("/api/v1/workspace/info?session_id=test-ws-session")
    assert response.status_code == 200
    assert response.json()["repo_name"] == data["repo_name"]

    # POST event
    event_payload = {
        "session_id": "test-ws-session",
        "event_type": "test_failure",
        "source": "pytest",
        "severity": "error",
        "message": "Mock test failure payload",
        "details": {"test_name": "test_endpoint"}
    }
    response = client.post("/api/v1/workspace/event", json=event_payload)
    assert response.status_code == 201
    event_data = response.json()
    assert event_data["message"] == "Mock test failure payload"

    # GET errors
    response = client.get("/api/v1/workspace/errors?session_id=test-ws-session")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # POST events/resolve
    resolve_payload = {"event_ids": [event_data["event_id"]]}
    response = client.post("/api/v1/workspace/events/resolve", json=resolve_payload)
    assert response.status_code == 200
    assert response.json()["count"] == 1

    # Errors list is now empty
    response = client.get("/api/v1/workspace/errors?session_id=test-ws-session")
    assert len(response.json()) == 0

def test_cognitive_orchestrator_integration(client, db_session):
    # Setup a fresh snapshot and error
    manager = WorkspaceManager()
    snap = manager.create_snapshot(db_session, session_id="test-session-co", active_file_path="backend/app/main.py")
    
    manager.log_event(
        db=db_session,
        event_type="error",
        source="pytest",
        severity="error",
        message="Active database trace error context check",
        details={},
        session_id="test-session-co",
        snapshot_id=snap.snapshot_id
    )

    orchestrator = CognitiveOrchestrator()
    plan = orchestrator.generate_plan(db_session, query="How do I register routes in FastAPI?", session_id="test-session-co")
    
    # Assert trace_id was persisted and workspace_snapshot_id linked
    trace_id = plan["decision_trace"]["trace_id"]
    trace = db_session.query(CognitiveTrace).filter(CognitiveTrace.trace_id == trace_id).first()
    assert trace is not None
    assert trace.workspace_snapshot_id == snap.snapshot_id

    # Assert prompt preview contains workspace details
    system_prompt = plan["prompt_package"]["system_prompt"]
    user_prompt = plan["prompt_package"]["user_prompt"]
    
    assert "=== WORKSPACE ENVIRONMENT STATUS ===" in user_prompt
    assert "Active File: backend/app/main.py" in user_prompt
    assert "Active database trace error context check" in user_prompt
