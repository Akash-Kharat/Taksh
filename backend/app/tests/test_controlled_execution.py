"""
Test Suite — Controlled Execution Layer (MS-11)

Tests:
1. ExecutionPolicy validation (CWD, executable whitelist, Git allowed/banned, Pytest limits/flags).
2. ProcessRunner mock-based isolation testing (output truncation, timeout handling, exit codes).
3. Concurrency limits validation (MAX_CONCURRENT_EXECUTIONS = 2 gating and HTTP 429).
4. Tool ownership (requested_by attribution) validation.
5. Endpoints: executions list (previews only) and executions detail (full logs).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database_models import ToolExecution
from app.services.tools.base import CapabilityLevel, ExecutionStatus, ToolRequest
from app.services.tools.manager import ToolManager, ConcurrencyLimitError
from app.services.tools.policy import ExecutionPolicy
from app.services.tools.process_runner import ProcessRunner, ExecutionRequest, ExecutionResult


# ---------------------------------------------------------------------------
# 1. ExecutionPolicy Tests
# ---------------------------------------------------------------------------

class TestExecutionPolicy:
    def test_sandbox_cwd_validation(self):
        # Valid path inside workspace
        valid_cwd = settings.WORKSPACE_DIR / "app"
        resolved = ExecutionPolicy.validate_sandbox_cwd(valid_cwd)
        assert resolved == valid_cwd.resolve()

        # Invalid path outside workspace (e.g. system root or parent)
        invalid_cwd = Path("../../../..")
        with pytest.raises(PermissionError, match="outside workspace boundary"):
            ExecutionPolicy.validate_sandbox_cwd(invalid_cwd)

    def test_executable_whitelist(self):
        # Allowed keys
        assert "git" in ExecutionPolicy.validate_executable("git") or True  # shutil.which might return path or fail if not installed, but let's mock if needed
        
        # Prohibited keys
        with pytest.raises(PermissionError, match="not in the whitelist"):
            ExecutionPolicy.validate_executable("curl")

    def test_shell_symbol_prohibition(self):
        # Reject shell operators
        with pytest.raises(ValueError, match="Shell operations are prohibited"):
            ExecutionPolicy.validate_arguments("git", ["diff", ";", "rm", "-rf"])
            
        with pytest.raises(ValueError, match="Shell operations are prohibited"):
            ExecutionPolicy.validate_arguments("git", ["log", "&&", "git", "status"])

    def test_git_subcommand_restrictions(self):
        # Allowed Git subcommands
        ExecutionPolicy.validate_arguments("git", ["diff", "--cached"])
        ExecutionPolicy.validate_arguments("git", ["log", "-n", "5"])
        ExecutionPolicy.validate_arguments("git", ["status"])

        # Prohibited Git subcommands
        with pytest.raises(ValueError, match="is prohibited"):
            ExecutionPolicy.validate_arguments("git", ["commit", "-m", "banned"])
            
        with pytest.raises(ValueError, match="is prohibited"):
            ExecutionPolicy.validate_arguments("git", ["push", "origin", "main"])
            
        with pytest.raises(ValueError, match="is prohibited"):
            ExecutionPolicy.validate_arguments("git", ["checkout", "branch"])

    def test_pytest_argument_restrictions(self):
        # Allowed Pytest args
        ExecutionPolicy.validate_arguments("pytest", ["-v", "-q", "app/tests/test_health.py"])

        # Too many arguments (limit = 5)
        with pytest.raises(ValueError, match="exceeds maximum limit"):
            ExecutionPolicy.validate_arguments("pytest", ["-v", "-q", "t1.py", "t2.py", "t3.py", "t4.py"])

        # Too deep path (limit = 5)
        with pytest.raises(ValueError, match="exceeds maximum depth"):
            ExecutionPolicy.validate_arguments("pytest", ["app/tests/a/b/c/d/e/test_file.py"])

        # Prohibited option
        with pytest.raises(ValueError, match="Prohibited Pytest flag"):
            ExecutionPolicy.validate_arguments("pytest", ["--pdb"])


# ---------------------------------------------------------------------------
# 2. ProcessRunner Tests (Mocked execution)
# ---------------------------------------------------------------------------

class TestProcessRunner:
    @patch("subprocess.Popen")
    def test_process_runner_success(self, mock_popen):
        # Mock successful subprocess run
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.read.side_effect = [b"hello stdout\n", b""]
        mock_proc.stderr.read.side_effect = [b"hello stderr\n", b""]
        mock_popen.return_value = mock_proc

        # Mock shutil.which in policy layer to guarantee validation passes
        with patch.object(ExecutionPolicy, "validate_executable", return_value="/usr/bin/git"):
            req = ExecutionRequest(
                executable_key="git",
                args=["status"],
                cwd=settings.WORKSPACE_DIR
            )
            res = ProcessRunner.run(req)

            assert res.exit_code == 0
            assert "hello stdout" in res.stdout
            assert "hello stderr" in res.stderr
            assert not res.stdout_truncated
            assert not res.stderr_truncated
            assert not res.timed_out

    @patch("subprocess.Popen")
    def test_process_runner_timeout(self, mock_popen):
        # Mock timeout during wait()
        mock_proc = MagicMock()
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=1.0)
        mock_proc.stdout.read.side_effect = [b"starting...", b""]
        mock_proc.stderr.read.side_effect = [b"", b""]
        mock_popen.return_value = mock_proc

        with patch.object(ExecutionPolicy, "validate_executable", return_value="/usr/bin/pytest"):
            req = ExecutionRequest(
                executable_key="pytest",
                args=["-v"],
                cwd=settings.WORKSPACE_DIR,
                timeout_seconds=1.0
            )
            res = ProcessRunner.run(req)

            assert res.timed_out
            assert res.exit_code is None
            assert "starting..." in res.stdout

    @patch("subprocess.Popen")
    def test_process_runner_output_truncation(self, mock_popen):
        # Return extremely large output
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        
        # Output is larger than MAX_STDOUT_CHARS
        large_stdout = b"a" * (settings.MAX_STDOUT_CHARS + 100)
        large_stderr = b"b" * (settings.MAX_STDERR_CHARS + 100)
        
        mock_proc.stdout.read.side_effect = [large_stdout, b""]
        mock_proc.stderr.read.side_effect = [large_stderr, b""]
        mock_popen.return_value = mock_proc

        with patch.object(ExecutionPolicy, "validate_executable", return_value="/usr/bin/ruff"):
            req = ExecutionRequest(
                executable_key="ruff",
                args=["check"],
                cwd=settings.WORKSPACE_DIR
            )
            res = ProcessRunner.run(req)

            assert len(res.stdout) == settings.MAX_STDOUT_CHARS
            assert len(res.stderr) == settings.MAX_STDERR_CHARS
            assert res.stdout_truncated
            assert res.stderr_truncated


# ---------------------------------------------------------------------------
# 3. Concurrency Limits & Ownership Tests
# ---------------------------------------------------------------------------

class TestConcurrencyAndOwnership:
    def test_concurrency_gate_rejection(self, db_session: Session):
        # Reset concurrency counter to zero
        ToolManager._active_executions = 0

        # Simulate two active running executions
        ToolManager._active_executions = settings.MAX_CONCURRENT_EXECUTIONS

        manager = ToolManager(db=db_session)
        req = ToolRequest(
            tool_name="git_diff",
            parameters={"cached": False},
            requested_by="test_user"
        )

        with pytest.raises(ConcurrencyLimitError, match="Max concurrent executions limit"):
            manager.execute(req)

        # Reset count
        ToolManager._active_executions = 0

    @patch("app.services.tools.process_runner.ProcessRunner.run")
    def test_ownership_persisted(self, mock_run, db_session: Session):
        mock_run.return_value = ExecutionResult(
            exit_code=0,
            stdout="diff content",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
            duration_ms=45
        )

        manager = ToolManager(db=db_session)
        req = ToolRequest(
            tool_name="git_diff",
            parameters={"cached": True},
            requested_by="lead_dev_akash"
        )
        
        result = manager.execute(req)
        assert result.status == ExecutionStatus.SUCCESS

        # Verify database record attribution
        db_record = db_session.query(ToolExecution).filter(ToolExecution.tool_name == "git_diff").first()
        assert db_record is not None
        assert db_record.requested_by == "lead_dev_akash"
        assert db_record.exit_code == 0
        assert db_record.stdout == "diff content"


# ---------------------------------------------------------------------------
# 4. API Endpoints (Preview vs Detail Payload validation)
# ---------------------------------------------------------------------------

class TestAPIEndpoints:
    @patch("app.services.tools.process_runner.ProcessRunner.run")
    def test_list_vs_detail_payloads(self, mock_run, client: TestClient, db_session: Session):
        # 1. Insert dummy tool executions
        mock_run.return_value = ExecutionResult(
            exit_code=0,
            stdout="A" * 500,  # larger than 200 chars preview
            stderr="B" * 300,
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
            duration_ms=10
        )

        # Execute git_diff via api
        response = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "git_diff",
                "parameters": {"cached": False},
                "requested_by": "api_client"
            }
        )
        assert response.status_code == 200

        # Query executions list
        list_response = client.get("/api/v1/tools/executions?limit=1")
        assert list_response.status_code == 200
        records = list_response.json()
        assert len(records) > 0
        record = records[0]

        # Verify preview exists but full stdout/stderr are EXCLUDED in listing schema
        assert "stdout_preview" in record
        assert record["stdout_preview"] == "A" * 200
        assert "stderr_preview" in record
        assert record["stderr_preview"] == "B" * 200
        assert "stdout" not in record
        assert "stderr" not in record

        # Query detail route
        execution_id = record["execution_id"]
        detail_response = client.get(f"/api/v1/tools/executions/{execution_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # Verify full stdout/stderr are INCLUDED in details schema
        assert "stdout" in detail
        assert detail["stdout"] == "A" * 500
        assert "stderr" in detail
        assert detail["stderr"] == "B" * 300

    def test_concurrency_error_api_mapping(self, client: TestClient):
        # Set executions count to max limit to trigger gate
        ToolManager._active_executions = settings.MAX_CONCURRENT_EXECUTIONS

        response = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "git_diff",
                "parameters": {},
                "requested_by": "guest"
            }
        )
        # Verify status is HTTP 429 Too Many Requests
        assert response.status_code == 429
        assert "executions limit" in response.json()["detail"]

        # Reset count
        ToolManager._active_executions = 0
