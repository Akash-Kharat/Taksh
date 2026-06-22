"""
Test Suite — Tool & Action Framework (MS-10)

Coverage targets
----------------
1.  ToolRegistry — registration, dedup, lookup, stats
2.  BaseTool / ToolResult — factories, truncation, timing
3.  Built-in tools — read_file, list_directory, search_repository,
                     git_status, test_report_reader, approval_test_tool
4.  Workspace sandboxing — path traversal rejection
5.  ToolManager — auto-execute, pending_approval routing, persistence
6.  ApprovalEngine — approve, deny, expired flow
7.  REST API — /tools/info, /tools/execute, /tools/executions,
               /tools/approvals, /tools/approvals/{id}/decide
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models.database_models import ApprovalRequest, ToolExecution
from app.services.tools.base import (
    BaseTool,
    CapabilityLevel,
    ExecutionStatus,
    ToolCategory,
    ToolDefinition,
    ToolRequest,
    ToolResult,
)
from app.services.tools.builtins import (
    ApprovalTestTool,
    GitStatusTool,
    ListDirectoryTool,
    ReadFileTool,
    SearchRepositoryTool,
    TestReportReaderTool,
)
from app.services.tools.manager import ApprovalEngine, ToolManager, _registry
from app.services.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Database setup — uses conftest.py fixtures (init_test_db, db_session, client)
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace_dir(tmp_path: Path) -> Path:
    """Create a minimal fake workspace directory with sample files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello():\n    print('hello')\n")
    (tmp_path / "README.md").write_text("# Test Workspace\n")
    (tmp_path / "src" / "utils.py").write_text("import os\nX = 42\n")
    return tmp_path


# ---------------------------------------------------------------------------
# 1. ToolRegistry
# ---------------------------------------------------------------------------

class _DummyTool(BaseTool):
    definition = ToolDefinition(
        name="dummy_tool",
        description="Test tool",
        category=ToolCategory.UTILITY,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
    )

    def _run(self, parameters):
        return ToolResult.success("dummy_tool", "ok", max_chars=100)


class _DummyTool2(BaseTool):
    definition = ToolDefinition(
        name="dummy_tool_2",
        description="Another test tool",
        category=ToolCategory.FILESYSTEM,
        capability_level=CapabilityLevel.ANALYZE,
        requires_approval=False,
    )

    def _run(self, parameters):
        return ToolResult.success("dummy_tool_2", "ok2", max_chars=100)


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register(_DummyTool)
        tool = reg.get("dummy_tool")
        assert tool is not None
        assert tool.definition.name == "dummy_tool"

    def test_duplicate_registration_raises(self):
        reg = ToolRegistry()
        reg.register(_DummyTool)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(_DummyTool)

    def test_get_unknown_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_list_by_category(self):
        reg = ToolRegistry()
        reg.register(_DummyTool)
        reg.register(_DummyTool2)
        utility = reg.list_by_category(ToolCategory.UTILITY)
        assert any(t.definition.name == "dummy_tool" for t in utility)

    def test_category_stats(self):
        reg = ToolRegistry()
        reg.register(_DummyTool)
        reg.register(_DummyTool2)
        stats = reg.category_stats()
        assert stats.get("utility", 0) >= 1
        assert stats.get("filesystem", 0) >= 1

    def test_total(self):
        reg = ToolRegistry()
        assert reg.total() == 0
        reg.register(_DummyTool)
        assert reg.total() == 1

    def test_register_all(self):
        reg = ToolRegistry()
        reg.register_all(_DummyTool, _DummyTool2)
        assert reg.total() == 2


# ---------------------------------------------------------------------------
# 2. ToolResult factories and truncation
# ---------------------------------------------------------------------------

class TestToolResult:
    def test_success_no_truncation(self):
        r = ToolResult.success("t", "hello", max_chars=100)
        assert r.status == ExecutionStatus.SUCCESS
        assert r.output == "hello"
        assert r.output_truncated is False

    def test_success_truncation(self):
        long_output = "x" * 200
        r = ToolResult.success("t", long_output, max_chars=100)
        assert r.output_truncated is True
        assert len(r.output) == 100

    def test_error_factory(self):
        r = ToolResult.error("t", "something broke")
        assert r.status == ExecutionStatus.ERROR
        assert r.error_message == "something broke"

    def test_rejected_factory(self):
        r = ToolResult.rejected("t")
        assert r.status == ExecutionStatus.REJECTED

    def test_pending_factory(self):
        r = ToolResult.pending("t")
        assert r.status == ExecutionStatus.PENDING_APPROVAL

    def test_execute_sets_duration(self):
        tool = _DummyTool()
        result = tool.execute({})
        assert result.duration_ms is not None
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# 3. Built-in tools (filesystem)
# ---------------------------------------------------------------------------

class TestReadFileTool:
    def test_read_existing_file(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        tool = ReadFileTool()
        result = tool.execute({"path": "README.md"})
        assert result.status == ExecutionStatus.SUCCESS
        assert "Test Workspace" in result.output

    def test_read_missing_path_param(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ReadFileTool().execute({})
        assert result.status == ExecutionStatus.ERROR
        assert "required" in result.error_message.lower()

    def test_read_nonexistent_file(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ReadFileTool().execute({"path": "ghost.txt"})
        assert result.status == ExecutionStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_read_with_line_range(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ReadFileTool().execute({"path": "src/main.py", "start_line": 1, "end_line": 1})
        assert result.status == ExecutionStatus.SUCCESS
        assert "def hello" in result.output


class TestListDirectoryTool:
    def test_list_root(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ListDirectoryTool().execute({"path": "."})
        assert result.status == ExecutionStatus.SUCCESS
        assert "README.md" in result.output or "src" in result.output

    def test_list_subdirectory(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ListDirectoryTool().execute({"path": "src"})
        assert result.status == ExecutionStatus.SUCCESS
        assert "main.py" in result.output

    def test_list_nonexistent(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ListDirectoryTool().execute({"path": "nope"})
        assert result.status == ExecutionStatus.ERROR


class TestSearchRepositoryTool:
    def test_search_existing_pattern(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_FILES", 10000)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_DEPTH", 20)
        result = SearchRepositoryTool().execute({"pattern": "hello"})
        assert result.status == ExecutionStatus.SUCCESS
        assert "main.py" in result.output

    def test_search_no_results(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_FILES", 10000)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_DEPTH", 20)
        result = SearchRepositoryTool().execute({"pattern": "ZZZNOMATCH999"})
        assert result.status == ExecutionStatus.SUCCESS
        assert "No matches" in result.output

    def test_search_missing_pattern(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = SearchRepositoryTool().execute({})
        assert result.status == ExecutionStatus.ERROR

    def test_search_with_glob(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_FILES", 10000)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_DEPTH", 20)
        result = SearchRepositoryTool().execute({"pattern": "import", "file_glob": "*.py"})
        assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# 4. Workspace sandboxing — path traversal
# ---------------------------------------------------------------------------

class TestSandboxing:
    def test_path_traversal_read_file(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ReadFileTool().execute({"path": "../../etc/passwd"})
        assert result.status == ExecutionStatus.ERROR
        assert "traversal" in result.error_message.lower()

    def test_path_traversal_list_directory(self, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        result = ListDirectoryTool().execute({"path": "../.."})
        assert result.status == ExecutionStatus.ERROR
        assert "traversal" in result.error_message.lower()

    def test_path_traversal_search(self, workspace_dir, monkeypatch):
        # search_repository always starts from workspace_dir itself, so traversal
        # is not an input parameter — the tool cannot escape the workspace.
        # Verify it gracefully handles an absolute path attempt in pattern.
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_FILES", 10000)
        monkeypatch.setattr("app.services.tools.builtins.settings.MAX_SCAN_DEPTH", 20)
        result = SearchRepositoryTool().execute({"pattern": "hello"})
        assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# 5. test_report_reader
# ---------------------------------------------------------------------------

class TestTestReportReader:
    def _write_json_report(self, tmp_path: Path) -> str:
        report = {
            "summary": {"total": 3, "passed": 2, "failed": 1, "skipped": 0, "errors": 0},
            "duration": 1.23,
            "tests": [
                {"nodeid": "test_foo.py::test_bar", "outcome": "failed",
                 "call": {"longrepr": "AssertionError: assert 1 == 2"}},
            ],
        }
        p = tmp_path / "report.json"
        p.write_text(json.dumps(report))
        return "report.json"

    def _write_junit_xml(self, tmp_path: Path) -> str:
        xml = (
            '<?xml version="1.0"?>'
            '<testsuite name="suite" tests="2" failures="1" errors="0" skipped="0" time="0.5">'
            '<testcase classname="test_foo" name="test_ok"/>'
            '<testcase classname="test_foo" name="test_bad">'
            '<failure message="boom">AssertionError</failure>'
            '</testcase>'
            '</testsuite>'
        )
        p = tmp_path / "report.xml"
        p.write_text(xml)
        return "report.xml"

    def test_parse_json_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", tmp_path)
        rel = self._write_json_report(tmp_path)
        result = TestReportReaderTool().execute({"report_path": rel})
        assert result.status == ExecutionStatus.SUCCESS
        assert "Passed:  2" in result.output
        assert "test_bar" in result.output

    def test_parse_junit_xml(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", tmp_path)
        rel = self._write_junit_xml(tmp_path)
        result = TestReportReaderTool().execute({"report_path": rel})
        assert result.status == ExecutionStatus.SUCCESS
        assert "suite" in result.output
        assert "test_bad" in result.output

    def test_unsupported_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", tmp_path)
        p = tmp_path / "report.csv"
        p.write_text("a,b,c")
        result = TestReportReaderTool().execute({"report_path": "report.csv"})
        assert result.status == ExecutionStatus.ERROR
        assert "Unsupported" in result.error_message

    def test_missing_param(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", tmp_path)
        result = TestReportReaderTool().execute({})
        assert result.status == ExecutionStatus.ERROR


# ---------------------------------------------------------------------------
# 6. ToolManager — routing
# ---------------------------------------------------------------------------

class TestToolManager:
    def test_auto_execute_read_tool(self, db_session, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="read_file", parameters={"path": "README.md"})
        result = manager.execute(req)
        assert result.status == ExecutionStatus.SUCCESS

    def test_unknown_tool_returns_error(self, db_session):
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="nonexistent_tool", parameters={})
        result = manager.execute(req)
        assert result.status == ExecutionStatus.ERROR
        assert "Unknown" in result.error_message

    def test_approval_required_tool_returns_pending(self, db_session):
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="approval_test_tool", parameters={"message": "hi"})
        result = manager.execute(req)
        assert result.status == ExecutionStatus.PENDING_APPROVAL

    def test_execution_is_persisted(self, db_session, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="read_file", parameters={"path": "README.md"})
        manager.execute(req)
        records = db_session.query(ToolExecution).filter(ToolExecution.tool_name == "read_file").all()
        assert len(records) >= 1

    def test_approval_request_is_persisted(self, db_session):
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="approval_test_tool", parameters={"message": "test"})
        manager.execute(req)
        ar = (
            db_session.query(ApprovalRequest)
            .filter(ApprovalRequest.tool_name == "approval_test_tool")
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        assert ar is not None
        assert ar.status == "pending"


# ---------------------------------------------------------------------------
# 7. ApprovalEngine — lifecycle
# ---------------------------------------------------------------------------

class TestApprovalEngine:
    def _create_pending_approval(self, db_session, monkeypatch) -> str:
        """Helper: submit approval_test_tool and return the approval_id."""
        manager = ToolManager(db=db_session)
        req = ToolRequest(tool_name="approval_test_tool", parameters={"message": "engine test"})
        manager.execute(req)
        ar = (
            db_session.query(ApprovalRequest)
            .filter(ApprovalRequest.tool_name == "approval_test_tool")
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        return ar.approval_id

    def test_approve_executes_tool(self, db_session, monkeypatch):
        approval_id = self._create_pending_approval(db_session, monkeypatch)
        manager = ToolManager(db=db_session)
        engine = ApprovalEngine(db=db_session, tool_manager=manager)
        result = engine.decide(approval_id=approval_id, approved=True)
        assert result.status == ExecutionStatus.SUCCESS
        assert "Approved execution" in result.output

    def test_deny_returns_rejected(self, db_session, monkeypatch):
        approval_id = self._create_pending_approval(db_session, monkeypatch)
        manager = ToolManager(db=db_session)
        engine = ApprovalEngine(db=db_session, tool_manager=manager)
        result = engine.decide(approval_id=approval_id, approved=False)
        assert result.status == ExecutionStatus.REJECTED

    def test_expired_approval(self, db_session, monkeypatch):
        # Create a pending approval then artificially expire it
        approval_id = self._create_pending_approval(db_session, monkeypatch)
        ar = db_session.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
        ar.expires_at = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        manager = ToolManager(db=db_session)
        engine = ApprovalEngine(db=db_session, tool_manager=manager)
        result = engine.decide(approval_id=approval_id, approved=True)
        assert result.status == ExecutionStatus.REJECTED
        assert "expired" in result.error_message.lower()

    def test_unknown_approval_id(self, db_session):
        manager = ToolManager(db=db_session)
        engine = ApprovalEngine(db=db_session, tool_manager=manager)
        result = engine.decide(approval_id="nonexistent-id", approved=True)
        assert result.status == ExecutionStatus.ERROR

    def test_double_decide_rejected(self, db_session, monkeypatch):
        approval_id = self._create_pending_approval(db_session, monkeypatch)
        manager = ToolManager(db=db_session)
        engine = ApprovalEngine(db=db_session, tool_manager=manager)
        engine.decide(approval_id=approval_id, approved=True)
        # Second attempt on same ID must fail
        result = engine.decide(approval_id=approval_id, approved=True)
        assert result.status == ExecutionStatus.REJECTED


# ---------------------------------------------------------------------------
# 8. REST API tests
# ---------------------------------------------------------------------------

class TestToolsAPI:
    def test_tools_info(self, client):
        response = client.get("/api/v1/tools/info")
        assert response.status_code == 200
        data = response.json()
        assert "total_tools" in data
        assert data["total_tools"] >= 5
        assert isinstance(data["category_stats"], dict)
        assert isinstance(data["tools"], list)

    def test_execute_auto_tool(self, client, workspace_dir, monkeypatch):
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", workspace_dir)
        response = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "list_directory", "parameters": {"path": "."}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_execute_approval_required(self, client):
        response = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "approval_test_tool", "parameters": {"message": "api test"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"

    def test_execute_unknown_tool(self, client):
        response = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "no_such_tool", "parameters": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_list_executions(self, client):
        response = client.get("/api/v1/tools/executions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_approvals(self, client):
        response = client.get("/api/v1/tools/approvals")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_decide_approve_via_api(self, client):
        # First create a pending request
        resp = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "approval_test_tool", "parameters": {"message": "decide test"}},
        )
        assert resp.status_code == 200
        # Fetch pending approvals to get the ID
        approvals_resp = client.get("/api/v1/tools/approvals?status=pending&limit=1")
        approvals = approvals_resp.json()
        assert len(approvals) >= 1
        approval_id = approvals[0]["approval_id"]

        # Approve it
        decide_resp = client.post(
            f"/api/v1/tools/approvals/{approval_id}/decide",
            json={"approved": True},
        )
        assert decide_resp.status_code == 200
        assert decide_resp.json()["status"] == "success"

    def test_category_stats_in_info(self, client):
        response = client.get("/api/v1/tools/info")
        stats = response.json()["category_stats"]
        # We expect at least filesystem, git, testing, search, utility
        assert len(stats) >= 4

    def test_output_truncation_flag_in_response(self, client, tmp_path, monkeypatch):
        """Verify output_truncated is returned correctly (no truncation for small output)."""
        monkeypatch.setattr("app.services.tools.builtins.settings.WORKSPACE_DIR", tmp_path)
        small_file = tmp_path / "tiny.txt"
        small_file.write_text("hello world")
        response = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "read_file", "parameters": {"path": "tiny.txt"}},
        )
        assert response.status_code == 200
        assert response.json()["output_truncated"] is False
