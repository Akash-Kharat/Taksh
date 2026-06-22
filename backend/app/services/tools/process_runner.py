"""
Process Runner Service (MS-11)

Handles structured subprocess execution:
- shell=False is strictly enforced (no cmd.exe, powershell.exe, bash -c).
- Timeout enforcement with SIGTERM/SIGKILL fallback.
- Output budget limitation (stdout/stderr are limited dynamically to prevent OOM).
- Structured logging using tool_logger.
"""
from __future__ import annotations

import time
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import tool_logger
from app.services.tools.policy import ExecutionPolicy


@dataclass(frozen=True)
class ExecutionRequest:
    executable_key: str              # e.g., 'git', 'pytest', 'ruff'
    args: List[str]                  # argv parameters
    cwd: Path                        # Working directory inside workspace
    timeout_seconds: float = 60.0    # Execution duration limit
    env: Optional[Dict[str, str]] = None  # Environment overrides
    tool_name: str = "unknown"
    requested_by: Optional[str] = "unknown"


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: Optional[int]
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    duration_ms: int


class ProcessRunner:
    """Safely executes whitelisted subprocesses under budget and time constraints."""

    @staticmethod
    def _read_stream(stream: Any, limit: int, output_box: List[str], truncation_box: List[bool]) -> None:
        """Reads from a stream up to the limit, setting truncation flags if exceeded."""
        chunks: List[str] = []
        total_chars = 0
        truncated = False

        try:
            while True:
                # Read chunks of bytes
                chunk = stream.read(4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                
                if total_chars < limit:
                    remaining = limit - total_chars
                    if len(text) > remaining:
                        chunks.append(text[:remaining])
                        total_chars = limit
                        truncated = True
                    else:
                        chunks.append(text)
                        total_chars += len(text)
                else:
                    truncated = True
        except Exception:
            # If the stream is closed or errors occur, stop reading
            pass

        output_box.append("".join(chunks))
        truncation_box.append(truncated)

    @classmethod
    def run(cls, request: ExecutionRequest) -> ExecutionResult:
        """
        Executes a subprocess based on the request.
        Validates executable, arguments, and sandbox CWD prior to execution.
        """
        # Validate input parameters via ExecutionPolicy
        resolved_bin = ExecutionPolicy.validate_executable(request.executable_key)
        ExecutionPolicy.validate_arguments(request.executable_key, request.args)
        resolved_cwd = ExecutionPolicy.validate_sandbox_cwd(request.cwd)

        # Build full command list (first element is the resolved absolute path)
        cmd = [resolved_bin] + request.args

        # Log Execution Started
        tool_logger.info(
            f"Execution Started: Tool={request.tool_name}, Executable={resolved_bin}, RequestedBy={request.requested_by}"
        )

        t0 = time.perf_counter()
        
        # Prepare process environment
        process_env = None
        if request.env:
            import os
            process_env = os.environ.copy()
            process_env.update(request.env)

        proc = None
        timed_out = False
        exit_code = None

        try:
            # shell=False is enforced. No cmd.exe / powershell.exe / bash -c.
            proc = subprocess.Popen(
                cmd,
                cwd=str(resolved_cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=process_env
            )

            # Lists to store thread outputs
            stdout_box: List[str] = []
            stdout_truncated_box: List[bool] = []
            stderr_box: List[str] = []
            stderr_truncated_box: List[bool] = []

            # Spawn reader threads to handle output streams asynchronously to avoid pipe deadlock
            stdout_thread = threading.Thread(
                target=cls._read_stream,
                args=(proc.stdout, settings.MAX_STDOUT_CHARS, stdout_box, stdout_truncated_box),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=cls._read_stream,
                args=(proc.stderr, settings.MAX_STDERR_CHARS, stderr_box, stderr_truncated_box),
                daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            # Wait for process completion with timeout
            try:
                proc.wait(timeout=request.timeout_seconds)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                tool_logger.warning(
                    f"Execution Timed Out: Tool={request.tool_name}, Timeout={request.timeout_seconds}s"
                )
                
                # Terminate and kill process
                try:
                    proc.terminate()
                    # Wait briefly for graceful shutdown, else force kill
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                except Exception as e:
                    tool_logger.error(f"Failed to kill timed out process: {e}")

            # Wait for reading threads to finish
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)

            # Fallback values if threads did not populate boxes
            stdout_str = stdout_box[0] if stdout_box else ""
            stdout_truncated = stdout_truncated_box[0] if stdout_truncated_box else False
            stderr_str = stderr_box[0] if stderr_box else ""
            stderr_truncated = stderr_truncated_box[0] if stderr_truncated_box else False

            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            if timed_out:
                tool_logger.warning(f"Execution Failed: Tool={request.tool_name}, Error=TimeoutExpired")
                return ExecutionResult(
                    exit_code=None,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    stdout_truncated=stdout_truncated,
                    stderr_truncated=stderr_truncated,
                    timed_out=True,
                    duration_ms=elapsed_ms
                )

            # Log Execution Completed
            tool_logger.info(
                f"Execution Completed: Tool={request.tool_name}, ExitCode={exit_code}, Duration={elapsed_ms}ms"
            )

            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                timed_out=False,
                duration_ms=elapsed_ms
            )

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            tool_logger.error(f"Execution Failed: Tool={request.tool_name}, Error={exc}")
            
            # Clean up if process was started but raised exception later
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass

            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="",
                stdout_truncated=False,
                stderr_truncated=False,
                timed_out=False,
                duration_ms=elapsed_ms
            )
