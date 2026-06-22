"""
Tool & Action Framework — Base Contracts (MS-10)

Defines the canonical data contracts and the abstract base class that
every built-in and future third-party tool must implement.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CapabilityLevel(str, Enum):
    """Ordered capability levels used for approval gating."""
    READ = "read"
    ANALYZE = "analyze"
    MODIFY = "modify"
    EXECUTE = "execute"


class ToolCategory(str, Enum):
    """Logical grouping of tools for UI / stats display."""
    FILESYSTEM = "filesystem"
    GIT = "git"
    TESTING = "testing"
    SEARCH = "search"
    UTILITY = "utility"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    REJECTED = "rejected"
    PENDING_APPROVAL = "pending_approval"


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

@dataclass
class ToolDefinition:
    """Static metadata that describes a tool to the registry and approval engine."""
    name: str
    description: str
    category: ToolCategory
    capability_level: CapabilityLevel
    requires_approval: bool
    tool_version: str = "1.0.0"
    parameters_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolRequest:
    """Encapsulates a single tool invocation request."""
    tool_name: str
    parameters: Dict[str, Any]
    trace_id: Optional[str] = None


@dataclass
class ToolResult:
    """The normalised result produced by a tool execution."""
    tool_name: str
    status: ExecutionStatus
    output: Optional[str] = None          # raw output string (pre-truncation)
    output_truncated: bool = False
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------------
    # Convenience factories
    # -----------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        tool_name: str,
        output: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_chars: int = 10_000,
    ) -> "ToolResult":
        truncated = len(output) > max_chars
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.SUCCESS,
            output=output[:max_chars] if truncated else output,
            output_truncated=truncated,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

    @classmethod
    def error(
        cls,
        tool_name: str,
        message: str,
        duration_ms: Optional[int] = None,
    ) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.ERROR,
            error_message=message,
            duration_ms=duration_ms,
        )

    @classmethod
    def rejected(cls, tool_name: str, reason: str = "Approval denied or expired.") -> "ToolResult":
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.REJECTED,
            error_message=reason,
        )

    @classmethod
    def pending(cls, tool_name: str) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.PENDING_APPROVAL,
        )


# ---------------------------------------------------------------------------
# Abstract Tool Base
# ---------------------------------------------------------------------------

class BaseTool(ABC):
    """
    All tools inherit from this class.

    Subclasses must:
      1. Declare a class-level ``definition: ToolDefinition``.
      2. Implement ``_run(parameters) -> ToolResult``.

    The public ``execute()`` method wraps ``_run`` with timing so
    individual tools never need to handle that themselves.
    """

    definition: ToolDefinition  # declared by each concrete subclass

    @abstractmethod
    def _run(self, parameters: Dict[str, Any]) -> ToolResult:
        """Core execution logic. Raise exceptions freely — ToolManager catches them."""
        ...

    def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Public entry point: runs _run with elapsed-time measurement."""
        t0 = time.perf_counter()
        result = self._run(parameters)
        elapsed = int((time.perf_counter() - t0) * 1000)
        if result.duration_ms is None:
            result.duration_ms = elapsed
        return result
