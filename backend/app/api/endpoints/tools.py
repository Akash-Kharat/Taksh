"""
Tool & Action Framework REST API (MS-10)

Endpoints
---------
GET  /tools/info                    — Registry info and per-category stats
POST /tools/execute                 — Execute a tool (auto or pending_approval)
GET  /tools/executions              — List recent ToolExecution records
GET  /tools/approvals               — List pending ApprovalRequest records
POST /tools/approvals/{id}/decide   — Approve or deny a pending request
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import ApprovalRequest, ToolExecution
from app.schemas.tools import (
    ApprovalDecisionRequest,
    ApprovalRequestRecord,
    ToolDefinitionResponse,
    ToolExecuteRequest,
    ToolExecutionRecord,
    ToolResultResponse,
    ToolsInfoResponse,
)
from app.services.tools.manager import ApprovalEngine, ToolManager, get_registry
from app.services.tools.base import ToolRequest

router = APIRouter(prefix="/tools", tags=["Tools"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _tool_manager(db: Session = Depends(get_db)) -> ToolManager:
    return ToolManager(db=db)


def _approval_engine(
    db: Session = Depends(get_db),
    tool_manager: ToolManager = Depends(_tool_manager),
) -> ApprovalEngine:
    return ApprovalEngine(db=db, tool_manager=tool_manager)


# ---------------------------------------------------------------------------
# GET /tools/info
# ---------------------------------------------------------------------------

@router.get("/info", response_model=ToolsInfoResponse)
def tools_info() -> ToolsInfoResponse:
    """Return registry metadata, tool list, and per-category counts."""
    registry = get_registry()
    tools = registry.list_all()
    tool_defs = [
        ToolDefinitionResponse(
            name=t.definition.name,
            description=t.definition.description,
            category=t.definition.category.value,
            capability_level=t.definition.capability_level.value,
            requires_approval=t.definition.requires_approval,
            tool_version=t.definition.tool_version,
            parameters_schema=t.definition.parameters_schema,
        )
        for t in tools
    ]
    return ToolsInfoResponse(
        total_tools=registry.total(),
        category_stats=registry.category_stats(),
        tools=tool_defs,
    )


# ---------------------------------------------------------------------------
# POST /tools/execute
# ---------------------------------------------------------------------------

@router.post("/execute", response_model=ToolResultResponse)
def execute_tool(
    body: ToolExecuteRequest,
    tool_manager: ToolManager = Depends(_tool_manager),
) -> ToolResultResponse:
    """
    Execute a registered tool.

    - READ / ANALYZE capability tools execute immediately.
    - MODIFY / EXECUTE tools return status=pending_approval and create an
      ApprovalRequest that must be resolved via the /approvals/{id}/decide endpoint.
    """
    request = ToolRequest(
        tool_name=body.tool_name,
        parameters=body.parameters,
        trace_id=body.trace_id,
    )
    result = tool_manager.execute(request)
    return ToolResultResponse(
        tool_name=result.tool_name,
        status=result.status.value,
        output=result.output,
        output_truncated=result.output_truncated,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
        metadata=result.metadata,
    )


# ---------------------------------------------------------------------------
# GET /tools/executions
# ---------------------------------------------------------------------------

@router.get("/executions", response_model=List[ToolExecutionRecord])
def list_executions(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
) -> List[ToolExecutionRecord]:
    """List recent tool execution records, newest first."""
    query = db.query(ToolExecution).order_by(ToolExecution.created_at.desc())
    if status:
        query = query.filter(ToolExecution.status == status)
    records = query.limit(limit).all()
    return [ToolExecutionRecord.model_validate(r) for r in records]


# ---------------------------------------------------------------------------
# GET /tools/approvals
# ---------------------------------------------------------------------------

@router.get("/approvals", response_model=List[ApprovalRequestRecord])
def list_approvals(
    status: Optional[str] = Query("pending", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[ApprovalRequestRecord]:
    """List approval requests filtered by status (default: pending)."""
    query = db.query(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status:
        query = query.filter(ApprovalRequest.status == status)
    records = query.limit(limit).all()
    return [ApprovalRequestRecord.model_validate(r) for r in records]


# ---------------------------------------------------------------------------
# POST /tools/approvals/{approval_id}/decide
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/decide", response_model=ToolResultResponse)
def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    engine: ApprovalEngine = Depends(_approval_engine),
) -> ToolResultResponse:
    """
    Approve or deny a pending tool execution request.

    - approved=true  → tool is executed and result is returned.
    - approved=false → request is denied; status=rejected.
    """
    result = engine.decide(approval_id=approval_id, approved=body.approved)
    return ToolResultResponse(
        tool_name=result.tool_name,
        status=result.status.value,
        output=result.output,
        output_truncated=result.output_truncated,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
        metadata=result.metadata,
    )
