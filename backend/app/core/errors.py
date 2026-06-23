"""
Taksh Structured Error Registry — MS-19
All API error responses use codes from this module.

Ranges:
  TAKSH-1000  Runtime Errors
  TAKSH-2000  Memory Errors
  TAKSH-3000  Knowledge Errors
  TAKSH-4000  Provider Errors
  TAKSH-5000  Tool Errors
"""
from dataclasses import dataclass
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Error data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TakshError:
    code: str
    message: str


class TakshErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# TAKSH-1000  Runtime Errors
# ---------------------------------------------------------------------------

RUNTIME_SESSION_NOT_FOUND       = TakshError("TAKSH-1001", "Runtime session not found")
RUNTIME_SESSION_ALREADY_ACTIVE  = TakshError("TAKSH-1002", "Runtime session already active")
RUNTIME_STATE_INVALID           = TakshError("TAKSH-1003", "Invalid runtime state transition")
RUNTIME_PIPELINE_FAILED         = TakshError("TAKSH-1004", "Conversation pipeline failed")
RUNTIME_TIMEOUT                 = TakshError("TAKSH-1005", "Runtime operation timed out")

# ---------------------------------------------------------------------------
# TAKSH-2000  Memory Errors
# ---------------------------------------------------------------------------

MEMORY_SESSION_NOT_FOUND        = TakshError("TAKSH-2001", "Memory session not found")
MEMORY_EPISODE_NOT_FOUND        = TakshError("TAKSH-2002", "Memory episode not found")
MEMORY_RECALL_FAILED            = TakshError("TAKSH-2003", "Memory recall failed")
MEMORY_CONSOLIDATION_FAILED     = TakshError("TAKSH-2004", "Memory consolidation failed")
MEMORY_LIMIT_EXCEEDED           = TakshError("TAKSH-2005", "Memory item limit exceeded")

# ---------------------------------------------------------------------------
# TAKSH-3000  Knowledge Errors
# ---------------------------------------------------------------------------

KNOWLEDGE_DOCUMENT_NOT_FOUND    = TakshError("TAKSH-3001", "Knowledge document not found")
KNOWLEDGE_INGESTION_FAILED      = TakshError("TAKSH-3002", "Knowledge ingestion failed")
KNOWLEDGE_SEARCH_FAILED         = TakshError("TAKSH-3003", "Knowledge search failed")
KNOWLEDGE_CHROMA_UNAVAILABLE    = TakshError("TAKSH-3004", "ChromaDB is unavailable")
KNOWLEDGE_CHUNK_LIMIT_EXCEEDED  = TakshError("TAKSH-3005", "Knowledge chunk limit exceeded")

# ---------------------------------------------------------------------------
# TAKSH-4000  Provider Errors
# ---------------------------------------------------------------------------

PROVIDER_NOT_FOUND              = TakshError("TAKSH-4001", "Provider not found")
PROVIDER_CONNECTION_FAILED      = TakshError("TAKSH-4002", "Provider connection failed")
PROVIDER_REQUEST_FAILED         = TakshError("TAKSH-4003", "Provider request failed")
PROVIDER_TIMEOUT                = TakshError("TAKSH-4004", "Provider request timed out")
PROVIDER_FALLBACK_EXHAUSTED     = TakshError("TAKSH-4005", "All provider fallbacks exhausted")
PROVIDER_INVALID_RESPONSE       = TakshError("TAKSH-4006", "Provider returned invalid response")

# ---------------------------------------------------------------------------
# TAKSH-5000  Tool Errors
# ---------------------------------------------------------------------------

TOOL_NOT_FOUND                  = TakshError("TAKSH-5001", "Tool not found")
TOOL_EXECUTION_FAILED           = TakshError("TAKSH-5002", "Tool execution failed")
TOOL_APPROVAL_REQUIRED          = TakshError("TAKSH-5003", "Tool requires user approval")
TOOL_APPROVAL_EXPIRED           = TakshError("TAKSH-5004", "Tool approval request expired")
TOOL_APPROVAL_REJECTED          = TakshError("TAKSH-5005", "Tool approval was rejected")
TOOL_OUTPUT_TRUNCATED           = TakshError("TAKSH-5006", "Tool output was truncated")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def raise_taksh_error(error: TakshError, detail: Optional[str] = None, status_code: int = 400) -> None:
    """Raise an HTTPException with a structured Taksh error payload."""
    raise HTTPException(
        status_code=status_code,
        detail=TakshErrorResponse(
            code=error.code,
            message=error.message,
            detail=detail,
        ).model_dump(),
    )


# Convenience lookup: code string → TakshError
ALL_ERRORS: dict[str, TakshError] = {
    v.code: v
    for v in globals().values()
    if isinstance(v, TakshError)
}
