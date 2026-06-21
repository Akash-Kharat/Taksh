from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class WorkspaceSnapshotRequest(BaseModel):
    session_id: Optional[str] = None
    active_file_path: Optional[str] = None
    active_file_language: Optional[str] = None
    cursor_line: Optional[int] = None
    cursor_column: Optional[int] = None
    selection_content: Optional[str] = None

class WorkspaceSnapshotResponse(BaseModel):
    snapshot_id: str
    session_id: Optional[str]
    repo_name: str
    repo_path: str
    active_file_path: Optional[str]
    active_file_language: Optional[str]
    cursor_line: Optional[int]
    cursor_column: Optional[int]
    selection_content: Optional[str]
    selection_truncated: bool
    git_branch: Optional[str]
    git_status: Dict[str, Any]
    git_recent_commits: List[Dict[str, Any]]
    detected_languages: List[Dict[str, Any]]
    detected_frameworks: List[str]
    scan_limit_reached: bool
    workspace_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceInfoResponse(BaseModel):
    repo_name: str
    repo_path: str
    git_branch: Optional[str]
    git_recent_commits: List[Dict[str, Any]]
    detected_languages: List[Dict[str, Any]]
    detected_frameworks: List[str]
    scan_limit_reached: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceEventCreate(BaseModel):
    session_id: Optional[str] = None
    event_type: str
    source: str
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = {}

class WorkspaceEventResponse(BaseModel):
    event_id: str
    session_id: Optional[str]
    snapshot_id: Optional[str]
    event_type: str
    source: str
    severity: str
    message: str
    details: Dict[str, Any]
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceResolveRequest(BaseModel):
    event_ids: Optional[List[str]] = None

class WorkspaceResolveResponse(BaseModel):
    status: str
    count: int
