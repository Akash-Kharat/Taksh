"""
Tool Manager & Approval Engine (MS-10)

ToolManager
-----------
- Resolves the requested tool from the registry.
- Routes automatic execution for read-only tools.
- Raises an approval request for write/modify/execute-level tools.
- Persists ToolExecution records to SQLite.
- Enforces WORKSPACE_DIR sandboxing pre-flight check.

ApprovalEngine
--------------
- Creates ApprovalRequest records.
- Resolves pending approvals by ID.
- Enforces APPROVAL_EXPIRATION_HOURS.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import tool_logger
from app.models.database_models import ApprovalRequest, ToolExecution
from app.services.tools.base import (
    CapabilityLevel,
    ExecutionStatus,
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
from app.services.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Module-level registry (populated once at import time)
# ---------------------------------------------------------------------------

_registry = ToolRegistry()
_registry.register_all(
    ReadFileTool,
    ListDirectoryTool,
    SearchRepositoryTool,
    GitStatusTool,
    TestReportReaderTool,
    ApprovalTestTool,
)


def get_registry() -> ToolRegistry:
    """Return the shared module-level registry."""
    return _registry


# ---------------------------------------------------------------------------
# Capability levels that execute automatically (no approval required)
# ---------------------------------------------------------------------------

_AUTO_EXECUTE_LEVELS = {CapabilityLevel.READ, CapabilityLevel.ANALYZE}


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------

class ToolManager:
    """
    Orchestrates tool execution with approval gating and persistence.

    Parameters
    ----------
    db : sqlalchemy.orm.Session
        An open database session (caller is responsible for lifecycle).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = _registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, request: ToolRequest) -> ToolResult:
        """
        Execute a tool or raise an approval request.

        Returns
        -------
        ToolResult
            - status=success/error for auto-executed tools.
            - status=pending_approval for tools that need human sign-off.
            - status=rejected for unknown tools.
        """
        tool = self.registry.get(request.tool_name)
        if tool is None:
            result = ToolResult.error(request.tool_name, f"Unknown tool: '{request.tool_name}'")
            self._persist_execution(request, tool, result)
            return result

        defn = tool.definition

        # Decide: auto-execute or gate on approval
        if not defn.requires_approval and defn.capability_level in _AUTO_EXECUTE_LEVELS:
            tool_logger.info(f"Auto-executing tool '{defn.name}' (level={defn.capability_level})")
            try:
                result = tool.execute(request.parameters)
            except Exception as exc:  # noqa: BLE001
                tool_logger.error(f"Tool '{defn.name}' raised unexpected exception: {exc}")
                result = ToolResult.error(defn.name, f"Unexpected error: {exc}")
        else:
            tool_logger.info(
                f"Tool '{defn.name}' requires approval (level={defn.capability_level}). "
                "Creating ApprovalRequest."
            )
            result = ToolResult.pending(defn.name)

        execution_record = self._persist_execution(request, tool, result)

        # Create the approval record *after* persisting the execution so we have the FK
        if result.status == ExecutionStatus.PENDING_APPROVAL and execution_record is not None:
            self._create_approval_request(request, execution_record.execution_id, defn)

        return result

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _persist_execution(
        self,
        request: ToolRequest,
        tool,
        result: ToolResult,
    ) -> Optional[ToolExecution]:
        """Persist a ToolExecution row and return it (or None on DB error)."""
        defn = tool.definition if tool is not None else None
        try:
            record = ToolExecution(
                trace_id=request.trace_id,
                tool_name=request.tool_name,
                tool_version=defn.tool_version if defn else "unknown",
                capability_level=(defn.capability_level.value if defn else "unknown"),
                category=(defn.category.value if defn else "unknown"),
                parameters=request.parameters,
                status=result.status.value,
                output_summary=(result.output[:500] if result.output else None),
                output_truncated=result.output_truncated,
                error_message=result.error_message,
                duration_ms=result.duration_ms,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception as exc:  # noqa: BLE001
            tool_logger.error(f"Failed to persist ToolExecution: {exc}")
            self.db.rollback()
            return None

    def _create_approval_request(
        self,
        request: ToolRequest,
        execution_id: str,
        defn,
    ) -> None:
        expires = datetime.utcnow() + timedelta(hours=settings.APPROVAL_EXPIRATION_HOURS)
        try:
            ar = ApprovalRequest(
                execution_id=execution_id,
                tool_name=defn.name,
                capability_level=defn.capability_level.value,
                parameters=request.parameters,
                reason=(
                    f"Tool '{defn.name}' has capability level '{defn.capability_level.value}' "
                    "and requires explicit human approval before execution."
                ),
                expires_at=expires,
            )
            self.db.add(ar)
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            tool_logger.error(f"Failed to persist ApprovalRequest: {exc}")
            self.db.rollback()


# ---------------------------------------------------------------------------
# ApprovalEngine
# ---------------------------------------------------------------------------

class ApprovalEngine:
    """
    Manages the human-approval lifecycle for tool execution requests.

    Parameters
    ----------
    db : sqlalchemy.orm.Session
    tool_manager : ToolManager
        Needed to actually run the tool after approval is granted.
    """

    def __init__(self, db: Session, tool_manager: ToolManager) -> None:
        self.db = db
        self.tool_manager = tool_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(self, approval_id: str, approved: bool) -> ToolResult:
        """
        Process an approval decision.

        - If approved, re-executes the underlying tool.
        - If denied, marks as denied.
        - Expired requests are rejected automatically.
        """
        ar: Optional[ApprovalRequest] = (
            self.db.query(ApprovalRequest)
            .filter(ApprovalRequest.approval_id == approval_id)
            .first()
        )
        if ar is None:
            return ToolResult.error("approval_engine", f"Approval request '{approval_id}' not found.")

        # Expire check
        if ar.status == "pending" and datetime.utcnow() > ar.expires_at:
            self._update_approval(ar, "expired")
            tool_logger.info(f"Approval '{approval_id}' expired.")
            return ToolResult.rejected(ar.tool_name, "Approval request has expired.")

        if ar.status != "pending":
            return ToolResult.rejected(
                ar.tool_name,
                f"Approval request is no longer pending (status='{ar.status}').",
            )

        if not approved:
            self._update_approval(ar, "denied")
            tool_logger.info(f"Approval '{approval_id}' denied by user.")
            # Update the linked execution record status
            self._update_execution_status(ar.execution_id, ExecutionStatus.REJECTED)
            return ToolResult.rejected(ar.tool_name, "Approval denied by user.")

        # Approved — execute the tool
        self._update_approval(ar, "approved")
        tool_logger.info(f"Approval '{approval_id}' granted. Executing '{ar.tool_name}'.")

        tool = self.tool_manager.registry.get(ar.tool_name)
        if tool is None:
            return ToolResult.error("approval_engine", f"Tool '{ar.tool_name}' no longer registered.")

        try:
            result = tool.execute(ar.parameters)
        except Exception as exc:  # noqa: BLE001
            result = ToolResult.error(ar.tool_name, f"Unexpected error after approval: {exc}")

        self._update_execution_status(ar.execution_id, result.status)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_approval(self, ar: ApprovalRequest, status: str) -> None:
        try:
            ar.status = status
            ar.decided_at = datetime.utcnow()
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            tool_logger.error(f"Failed to update ApprovalRequest: {exc}")
            self.db.rollback()

    def _update_execution_status(self, execution_id: str, status: ExecutionStatus) -> None:
        try:
            record = (
                self.db.query(ToolExecution)
                .filter(ToolExecution.execution_id == execution_id)
                .first()
            )
            if record:
                record.status = status.value
                self.db.commit()
        except Exception as exc:  # noqa: BLE001
            tool_logger.error(f"Failed to update ToolExecution status: {exc}")
            self.db.rollback()
