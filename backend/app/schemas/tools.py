"""
Pydantic validation schemas for the Tool & Action Framework REST API (MS-10).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Registered tool identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific parameters")
    trace_id: Optional[str] = Field(None, description="Optional cognitive trace to link to")


class ApprovalDecisionRequest(BaseModel):
    approved: bool = Field(..., description="True to approve, False to deny")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ToolResultResponse(BaseModel):
    tool_name: str
    status: str
    output: Optional[str] = None
    output_truncated: bool = False
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinitionResponse(BaseModel):
    name: str
    description: str
    category: str
    capability_level: str
    requires_approval: bool
    tool_version: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRecord(BaseModel):
    execution_id: str
    tool_name: str
    tool_version: str
    capability_level: str
    category: str
    status: str
    output_summary: Optional[str]
    output_truncated: bool
    error_message: Optional[str]
    duration_ms: Optional[int]
    trace_id: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestRecord(BaseModel):
    approval_id: str
    execution_id: str
    tool_name: str
    capability_level: str
    parameters: Dict[str, Any]
    reason: str
    status: str
    decided_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolsInfoResponse(BaseModel):
    total_tools: int
    category_stats: Dict[str, int]
    tools: List[ToolDefinitionResponse]
