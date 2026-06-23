"""
Tests for MS-19 Error Registry.
"""
import pytest
from app.core.errors import (
    ALL_ERRORS, TakshError, TakshErrorResponse,
    RUNTIME_SESSION_NOT_FOUND, PROVIDER_CONNECTION_FAILED,
    MEMORY_RECALL_FAILED, KNOWLEDGE_SEARCH_FAILED, TOOL_EXECUTION_FAILED,
)


def test_all_error_codes_are_unique():
    codes = list(ALL_ERRORS.keys())
    assert len(codes) == len(set(codes)), "Duplicate error codes detected"


def test_error_ranges_do_not_overlap():
    for code in ALL_ERRORS:
        prefix, num = code.split("-")
        assert prefix == "TAKSH"
        n = int(num)
        assert n >= 1000, f"{code} is below minimum range"


def test_runtime_errors_in_1000_range():
    code_num = int(RUNTIME_SESSION_NOT_FOUND.code.split("-")[1])
    assert 1000 <= code_num < 2000


def test_provider_errors_in_4000_range():
    code_num = int(PROVIDER_CONNECTION_FAILED.code.split("-")[1])
    assert 4000 <= code_num < 5000


def test_memory_errors_in_2000_range():
    code_num = int(MEMORY_RECALL_FAILED.code.split("-")[1])
    assert 2000 <= code_num < 3000


def test_knowledge_errors_in_3000_range():
    code_num = int(KNOWLEDGE_SEARCH_FAILED.code.split("-")[1])
    assert 3000 <= code_num < 4000


def test_tool_errors_in_5000_range():
    code_num = int(TOOL_EXECUTION_FAILED.code.split("-")[1])
    assert 5000 <= code_num < 6000


def test_taksh_error_is_frozen():
    with pytest.raises((AttributeError, TypeError)):
        RUNTIME_SESSION_NOT_FOUND.code = "changed"  # type: ignore


def test_error_response_serialization():
    resp = TakshErrorResponse(
        code="TAKSH-4002",
        message="Provider connection failed",
        detail="timeout after 5s",
    )
    data = resp.model_dump()
    assert data["code"] == "TAKSH-4002"
    assert data["message"] == "Provider connection failed"
    assert data["detail"] == "timeout after 5s"


def test_error_response_detail_optional():
    resp = TakshErrorResponse(code="TAKSH-1001", message="Not found")
    assert resp.detail is None


def test_all_errors_have_nonempty_message():
    for code, err in ALL_ERRORS.items():
        assert err.message, f"{code} has empty message"
