"""
Built-in Read-Only Tools (MS-10)

All tools here are observation-only: they read the workspace filesystem or
git state. They NEVER write, execute tests, modify files, or make network calls.

Tools
-----
- read_file           : Return UTF-8 content of a file inside WORKSPACE_DIR
- list_directory      : List entries in a directory inside WORKSPACE_DIR
- search_repository   : Search for a pattern in workspace files (grep-like)
- git_status          : Summarise the git working-tree status
- test_report_reader  : Parse and summarise pytest-json-report / junit.xml outputs
- approval_test_tool  : Deliberately requires_approval = True; used for testing

Sandboxing
----------
Every filesystem operation resolves the target path and verifies it remains
within settings.WORKSPACE_DIR.  Path-traversal attempts are rejected with an
informative error.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree

from app.core.config import settings
from app.services.tools.base import (
    BaseTool,
    CapabilityLevel,
    ExecutionStatus,
    ToolCategory,
    ToolDefinition,
    ToolResult,
)
from app.services.tools.process_runner import ProcessRunner, ExecutionRequest

# ---------------------------------------------------------------------------
# Sandbox helper
# ---------------------------------------------------------------------------

def _resolve_safe(raw_path: str, workspace: Path) -> Path:
    """
    Resolve *raw_path* relative to *workspace* and verify it stays inside.

    Raises
    ------
    ValueError
        If the resolved path escapes the workspace root.
    """
    resolved = (workspace / raw_path).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError:
        raise ValueError(
            f"Path traversal detected: '{raw_path}' resolves outside workspace."
        )
    return resolved


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class ReadFileTool(BaseTool):
    definition = ToolDefinition(
        name="read_file",
        description="Return the UTF-8 text content of a workspace file.",
        category=ToolCategory.FILESYSTEM,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "path": {"type": "string", "description": "Relative path inside workspace"},
            "start_line": {"type": "integer", "description": "Optional 1-based start line"},
            "end_line": {"type": "integer", "description": "Optional 1-based end line"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        raw_path: str = parameters.get("path", "")
        if not raw_path:
            return ToolResult.error("read_file", "Parameter 'path' is required.")
        workspace = settings.WORKSPACE_DIR.resolve()
        try:
            target = _resolve_safe(raw_path, workspace)
        except ValueError as e:
            return ToolResult.error("read_file", str(e))

        if not target.exists():
            return ToolResult.error("read_file", f"File not found: {raw_path}")
        if not target.is_file():
            return ToolResult.error("read_file", f"Path is not a file: {raw_path}")

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        except OSError as exc:
            return ToolResult.error("read_file", f"Cannot read file: {exc}")

        start = parameters.get("start_line")
        end = parameters.get("end_line")
        if start is not None or end is not None:
            s = max(1, int(start or 1)) - 1
            e = int(end) if end is not None else len(lines)
            lines = lines[s:e]

        output = "".join(lines)
        return ToolResult.success(
            "read_file",
            output,
            metadata={"path": str(target), "total_lines": len(lines)},
            max_chars=settings.MAX_TOOL_OUTPUT_CHARS,
        )


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------

class ListDirectoryTool(BaseTool):
    definition = ToolDefinition(
        name="list_directory",
        description="List files and subdirectories inside a workspace directory.",
        category=ToolCategory.FILESYSTEM,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "path": {"type": "string", "description": "Relative directory path (default '.')"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        raw_path = parameters.get("path", ".")
        workspace = settings.WORKSPACE_DIR.resolve()
        try:
            target = _resolve_safe(raw_path, workspace)
        except ValueError as e:
            return ToolResult.error("list_directory", str(e))

        if not target.exists():
            return ToolResult.error("list_directory", f"Directory not found: {raw_path}")
        if not target.is_dir():
            return ToolResult.error("list_directory", f"Path is not a directory: {raw_path}")

        entries: List[str] = []
        try:
            for entry in sorted(target.iterdir()):
                kind = "DIR " if entry.is_dir() else "FILE"
                entries.append(f"{kind}  {entry.name}")
        except OSError as exc:
            return ToolResult.error("list_directory", f"Cannot list directory: {exc}")

        output = f"Contents of {raw_path}:\n" + "\n".join(entries)
        return ToolResult.success(
            "list_directory",
            output,
            metadata={"path": str(target), "entry_count": len(entries)},
            max_chars=settings.MAX_TOOL_OUTPUT_CHARS,
        )


# ---------------------------------------------------------------------------
# search_repository
# ---------------------------------------------------------------------------

class SearchRepositoryTool(BaseTool):
    definition = ToolDefinition(
        name="search_repository",
        description="Search for a text pattern in workspace source files.",
        category=ToolCategory.SEARCH,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "pattern": {"type": "string", "description": "Text or regex pattern to search"},
            "file_glob": {"type": "string", "description": "Optional glob filter, e.g. '*.py'"},
            "max_results": {"type": "integer", "description": "Max number of matches (default 50)"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        pattern: str = parameters.get("pattern", "")
        if not pattern:
            return ToolResult.error("search_repository", "Parameter 'pattern' is required.")
        file_glob: str = parameters.get("file_glob", "*")
        max_results: int = int(parameters.get("max_results", 50))
        workspace = settings.WORKSPACE_DIR.resolve()

        matches: List[str] = []
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return ToolResult.error("search_repository", f"Invalid regex: {exc}")

        file_count = 0
        for root, dirs, files in os.walk(workspace):
            # Respect scan depth limit
            depth = len(Path(root).relative_to(workspace).parts)
            if depth >= settings.MAX_SCAN_DEPTH:
                dirs.clear()
                continue
            # Skip hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for fname in files:
                if file_count >= settings.MAX_SCAN_FILES:
                    break
                if file_glob != "*":
                    if not Path(fname).match(file_glob):
                        continue
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        rel = fpath.relative_to(workspace)
                        matches.append(f"{rel}:{lineno}: {line.rstrip()}")
                        if len(matches) >= max_results:
                            break
                file_count += 1
                if len(matches) >= max_results:
                    break

        if not matches:
            output = f"No matches found for pattern: {pattern}"
        else:
            output = "\n".join(matches)
        return ToolResult.success(
            "search_repository",
            output,
            metadata={"match_count": len(matches), "pattern": pattern},
            max_chars=settings.MAX_TOOL_OUTPUT_CHARS,
        )


# ---------------------------------------------------------------------------
# git_status
# ---------------------------------------------------------------------------

class GitStatusTool(BaseTool):
    definition = ToolDefinition(
        name="git_status",
        description="Return the current git working-tree status for the workspace.",
        category=ToolCategory.GIT,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={},
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        workspace = settings.WORKSPACE_DIR.resolve()
        try:
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return ToolResult.error("git_status", result.stderr.strip() or "git status failed.")
            output = result.stdout.strip() or "Working tree clean."
        except FileNotFoundError:
            return ToolResult.error("git_status", "git binary not found.")
        except subprocess.TimeoutExpired:
            return ToolResult.error("git_status", "git status timed out.")
        except OSError as exc:
            return ToolResult.error("git_status", str(exc))

        return ToolResult.success("git_status", output, max_chars=settings.MAX_TOOL_OUTPUT_CHARS)


# ---------------------------------------------------------------------------
# test_report_reader
# ---------------------------------------------------------------------------

class TestReportReaderTool(BaseTool):
    """
    Reads and summarises *existing* test report files.
    Does NOT execute pytest or any test runner.
    """
    definition = ToolDefinition(
        name="test_report_reader",
        description=(
            "Read and summarise an existing pytest-json-report (.json) or "
            "JUnit XML (.xml) test report. Does NOT run tests."
        ),
        category=ToolCategory.TESTING,
        capability_level=CapabilityLevel.ANALYZE,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "report_path": {
                "type": "string",
                "description": "Relative path to a .json or .xml test report file",
            }
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        raw_path: str = parameters.get("report_path", "")
        if not raw_path:
            return ToolResult.error("test_report_reader", "Parameter 'report_path' is required.")
        workspace = settings.WORKSPACE_DIR.resolve()
        try:
            target = _resolve_safe(raw_path, workspace)
        except ValueError as e:
            return ToolResult.error("test_report_reader", str(e))

        if not target.exists():
            return ToolResult.error("test_report_reader", f"Report not found: {raw_path}")

        suffix = target.suffix.lower()
        try:
            if suffix == ".json":
                output = self._parse_json_report(target)
            elif suffix == ".xml":
                output = self._parse_junit_xml(target)
            else:
                return ToolResult.error(
                    "test_report_reader",
                    f"Unsupported report format '{suffix}'. Expected .json or .xml.",
                )
        except Exception as exc:
            return ToolResult.error("test_report_reader", f"Failed to parse report: {exc}")

        return ToolResult.success(
            "test_report_reader",
            output,
            metadata={"report_path": str(target)},
            max_chars=settings.MAX_TOOL_OUTPUT_CHARS,
        )

    def _parse_json_report(self, path: Path) -> str:
        data = json.loads(path.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        lines = [
            "=== pytest-json-report summary ===",
            f"Total:   {summary.get('total', '?')}",
            f"Passed:  {summary.get('passed', 0)}",
            f"Failed:  {summary.get('failed', 0)}",
            f"Skipped: {summary.get('skipped', 0)}",
            f"Errors:  {summary.get('errors', 0)}",
            f"Duration: {data.get('duration', '?')}s",
        ]
        tests = data.get("tests", [])
        failures = [t for t in tests if t.get("outcome") in ("failed", "error")]
        if failures:
            lines.append("\n--- Failures ---")
            for t in failures[:10]:  # cap at 10
                lines.append(f"FAIL  {t.get('nodeid', '?')}")
                call = t.get("call", {})
                if call.get("longrepr"):
                    lines.append(f"      {str(call['longrepr'])[:300]}")
        return "\n".join(lines)

    def _parse_junit_xml(self, path: Path) -> str:
        tree = ElementTree.parse(path)
        root = tree.getroot()
        # Handle both <testsuites> and <testsuite> at root
        if root.tag == "testsuites":
            suites = list(root)
        else:
            suites = [root]

        lines = ["=== JUnit XML summary ==="]
        for suite in suites:
            name = suite.get("name", "unnamed")
            tests = suite.get("tests", "?")
            failures = suite.get("failures", "0")
            errors = suite.get("errors", "0")
            skipped = suite.get("skipped", "0")
            time_ = suite.get("time", "?")
            lines.append(
                f"Suite: {name} | tests={tests} failures={failures} "
                f"errors={errors} skipped={skipped} time={time_}s"
            )
            for tc in suite.findall("testcase"):
                fail = tc.find("failure")
                err = tc.find("error")
                if fail is not None or err is not None:
                    elem = fail if fail is not None else err
                    msg = (elem.get("message") or "")[:200]
                    lines.append(f"  FAIL {tc.get('classname', '')}.{tc.get('name', '')} — {msg}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# approval_test_tool (requires_approval=True — for testing the approval flow)
# ---------------------------------------------------------------------------

class ApprovalTestTool(BaseTool):
    definition = ToolDefinition(
        name="approval_test_tool",
        description=(
            "A harmless tool that always requires human approval. "
            "Used exclusively for testing the ApprovalEngine."
        ),
        category=ToolCategory.UTILITY,
        capability_level=CapabilityLevel.MODIFY,
        requires_approval=True,
        tool_version="1.0.0",
        parameters_schema={
            "message": {"type": "string", "description": "Any test message string"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        msg = parameters.get("message", "approval granted")
        return ToolResult.success(
            "approval_test_tool",
            f"Approved execution: {msg}",
            max_chars=settings.MAX_TOOL_OUTPUT_CHARS,
        )


# ---------------------------------------------------------------------------
# GitDiffTool
# ---------------------------------------------------------------------------

class GitDiffTool(BaseTool):
    definition = ToolDefinition(
        name="git_diff",
        description="Run git diff in the workspace to view changes.",
        category=ToolCategory.GIT,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "cached": {"type": "boolean", "description": "Show staged changes if True", "default": False},
            "path": {"type": "string", "description": "Optional file path to restrict diff"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        args = ["diff"]
        if parameters.get("cached"):
            args.append("--cached")
        path = parameters.get("path")
        if path:
            args.extend(["--", path])

        req = ExecutionRequest(
            executable_key="git",
            args=args,
            cwd=settings.WORKSPACE_DIR,
            tool_name="git_diff",
            requested_by=parameters.get("_requested_by", "unknown")
        )
        res = ProcessRunner.run(req)

        if res.timed_out:
            return ToolResult(
                tool_name="git_diff",
                status=ExecutionStatus.ERROR,
                error_message="Process timed out.",
                duration_ms=res.duration_ms,
                timed_out=True
            )

        if res.exit_code is not None and res.exit_code != 0:
            return ToolResult(
                tool_name="git_diff",
                status=ExecutionStatus.ERROR,
                error_message=res.stderr or f"Git diff exited with code {res.exit_code}",
                exit_code=res.exit_code,
                stdout=res.stdout,
                stderr=res.stderr,
                stdout_truncated=res.stdout_truncated,
                stderr_truncated=res.stderr_truncated,
                duration_ms=res.duration_ms
            )

        return ToolResult(
            tool_name="git_diff",
            status=ExecutionStatus.SUCCESS,
            output=res.stdout,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            stdout_truncated=res.stdout_truncated,
            stderr_truncated=res.stderr_truncated,
            duration_ms=res.duration_ms
        )


# ---------------------------------------------------------------------------
# GitLogTool
# ---------------------------------------------------------------------------

class GitLogTool(BaseTool):
    definition = ToolDefinition(
        name="git_log",
        description="Run git log in the workspace to view commit history.",
        category=ToolCategory.GIT,
        capability_level=CapabilityLevel.READ,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "max_count": {"type": "integer", "description": "Limit the number of commits (default 10)", "default": 10},
            "revision": {"type": "string", "description": "Optional revision range filter (e.g. main..HEAD)"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        max_count = parameters.get("max_count", 10)
        args = ["log", "-n", str(max_count)]
        revision = parameters.get("revision")
        if revision:
            args.append(revision)

        req = ExecutionRequest(
            executable_key="git",
            args=args,
            cwd=settings.WORKSPACE_DIR,
            tool_name="git_log",
            requested_by=parameters.get("_requested_by", "unknown")
        )
        res = ProcessRunner.run(req)

        if res.timed_out:
            return ToolResult(
                tool_name="git_log",
                status=ExecutionStatus.ERROR,
                error_message="Process timed out.",
                duration_ms=res.duration_ms,
                timed_out=True
            )

        if res.exit_code is not None and res.exit_code != 0:
            return ToolResult(
                tool_name="git_log",
                status=ExecutionStatus.ERROR,
                error_message=res.stderr or f"Git log exited with code {res.exit_code}",
                exit_code=res.exit_code,
                stdout=res.stdout,
                stderr=res.stderr,
                stdout_truncated=res.stdout_truncated,
                stderr_truncated=res.stderr_truncated,
                duration_ms=res.duration_ms
            )

        return ToolResult(
            tool_name="git_log",
            status=ExecutionStatus.SUCCESS,
            output=res.stdout,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            stdout_truncated=res.stdout_truncated,
            stderr_truncated=res.stderr_truncated,
            duration_ms=res.duration_ms
        )


# ---------------------------------------------------------------------------
# RuffRunnerTool
# ---------------------------------------------------------------------------

class RuffRunnerTool(BaseTool):
    definition = ToolDefinition(
        name="ruff_runner",
        description="Run ruff linter on the workspace.",
        category=ToolCategory.TESTING,
        capability_level=CapabilityLevel.ANALYZE,
        requires_approval=False,
        tool_version="1.0.0",
        parameters_schema={
            "paths": {"type": "array", "items": {"type": "string"}, "description": "Relative paths to run ruff check on"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        paths = parameters.get("paths") or []
        args = ["check"]
        args.extend(paths)

        req = ExecutionRequest(
            executable_key="ruff",
            args=args,
            cwd=settings.WORKSPACE_DIR,
            tool_name="ruff_runner",
            requested_by=parameters.get("_requested_by", "unknown")
        )
        res = ProcessRunner.run(req)

        if res.timed_out:
            return ToolResult(
                tool_name="ruff_runner",
                status=ExecutionStatus.ERROR,
                error_message="Process timed out.",
                duration_ms=res.duration_ms,
                timed_out=True
            )

        status = ExecutionStatus.SUCCESS if res.exit_code in (0, 1) else ExecutionStatus.ERROR
        error_msg = None if status == ExecutionStatus.SUCCESS else (res.stderr or f"Ruff failed with exit code {res.exit_code}")

        return ToolResult(
            tool_name="ruff_runner",
            status=status,
            output=res.stdout or res.stderr,
            error_message=error_msg,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            stdout_truncated=res.stdout_truncated,
            stderr_truncated=res.stderr_truncated,
            duration_ms=res.duration_ms
        )


# ---------------------------------------------------------------------------
# PytestRunnerTool
# ---------------------------------------------------------------------------

class PytestRunnerTool(BaseTool):
    definition = ToolDefinition(
        name="pytest_runner",
        description="Run pytest test suite in the workspace.",
        category=ToolCategory.TESTING,
        capability_level=CapabilityLevel.EXECUTE,
        requires_approval=True,
        tool_version="1.0.0",
        parameters_schema={
            "test_path": {"type": "string", "description": "Optional relative path to a specific test file/directory"},
            "filter_expr": {"type": "string", "description": "Optional expression to filter tests by name (maps to -k)"},
        },
    )

    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        args = []
        test_path = parameters.get("test_path")
        if test_path:
            args.append(test_path)
        filter_expr = parameters.get("filter_expr")
        if filter_expr:
            args.extend(["-k", filter_expr])

        req = ExecutionRequest(
            executable_key="pytest",
            args=args,
            cwd=settings.WORKSPACE_DIR,
            timeout_seconds=120.0,
            tool_name="pytest_runner",
            requested_by=parameters.get("_requested_by", "unknown")
        )
        res = ProcessRunner.run(req)

        if res.timed_out:
            return ToolResult(
                tool_name="pytest_runner",
                status=ExecutionStatus.ERROR,
                error_message="Process timed out.",
                duration_ms=res.duration_ms,
                timed_out=True
            )

        status = ExecutionStatus.SUCCESS if res.exit_code in (0, 1) else ExecutionStatus.ERROR
        error_msg = None if status == ExecutionStatus.SUCCESS else (res.stderr or f"Pytest failed with exit code {res.exit_code}")

        return ToolResult(
            tool_name="pytest_runner",
            status=status,
            output=res.stdout or res.stderr,
            error_message=error_msg,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            stdout_truncated=res.stdout_truncated,
            stderr_truncated=res.stderr_truncated,
            duration_ms=res.duration_ms
        )

