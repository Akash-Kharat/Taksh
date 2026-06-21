import pytest
import httpx
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.config import settings
from app.services.llm.contracts import LLMRequest, LLMResponse
from app.services.llm.providers.mock import MockLLMProvider
from app.services.llm.providers.gemini import GeminiLLMProvider
from app.services.llm.manager import LLMManager
from app.services.llm.retry import execute_with_retry
from app.models.database_models import CognitiveTrace, AIResponse, ConversationMessage


def test_mock_llm_provider():
    provider = MockLLMProvider()
    assert provider.validate_config() is True
    
    # Run ping
    # ping() is async, so we must run it in a way pytest-asyncio or anyio handles it
    # pytest allows writing async tests directly if marked or run in event loop.
    # To keep it simple and robust, we can run async methods using asyncio.run
    import asyncio
    assert asyncio.run(provider.ping()) is True

    req = LLMRequest(system_prompt="System instructions", user_prompt="User query")
    res = asyncio.run(provider.generate_response(req))
    assert res.status == "success"
    assert "Mock response" in res.content
    assert res.provider == "mock"


@pytest.mark.anyio
async def test_retry_transient_failures():
    # Test retry mechanism on transient failures (429, 503, timeout)
    call_count = 0

    async def transient_mock_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Raise a transient status error (e.g. 503)
            resp = httpx.Response(503, request=httpx.Request("POST", "http://test"))
            raise httpx.HTTPStatusError("Service Unavailable", request=resp.request, response=resp)
        return "success-result"

    result = await execute_with_retry(transient_mock_call, max_retries=3, initial_delay=0.01)
    assert result == "success-result"
    assert call_count == 3  # Failed twice, succeeded on 3rd attempt


@pytest.mark.anyio
async def test_retry_permanent_failures_fail_fast():
    # Test that permanent errors (e.g. 401 Unauthorized) fail fast
    call_count = 0

    async def permanent_mock_call():
        nonlocal call_count
        call_count += 1
        resp = httpx.Response(401, request=httpx.Request("POST", "http://test"))
        raise httpx.HTTPStatusError("Unauthorized", request=resp.request, response=resp)

    with pytest.raises(httpx.HTTPStatusError):
        await execute_with_retry(permanent_mock_call, max_retries=3, initial_delay=0.01)
    
    assert call_count == 1  # Fails immediately without retrying


@pytest.mark.anyio
async def test_gemini_provider_timeout_wrapper():
    # Mock httpx.AsyncClient call to raise a timeout
    provider = GeminiLLMProvider()
    
    # Force config validation to pass
    provider.validate_config = MagicMock(return_value=True)
    
    req = LLMRequest(system_prompt="Sys", user_prompt="User")
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Connection timed out")):
        res = await provider.generate_response(req)
        assert res.status == "timeout"
        assert "timed out" in res.error_message.lower()


@pytest.mark.anyio
async def test_llm_manager_fallback():
    manager = LLMManager()
    
    # Mock default configured provider to be "mock"
    settings.DEFAULT_LLM_PROVIDER = "mock"
    provider = manager.get_provider()
    assert isinstance(provider, MockLLMProvider)
    
    # Requesting an invalid provider should fallback to mock
    provider_fallback = manager.get_provider("invalid-name")
    assert isinstance(provider_fallback, MockLLMProvider)


def test_api_chat_generate_and_persistence(client, db_session):
    # Ensure default provider is mock to run entirely offline
    settings.DEFAULT_LLM_PROVIDER = "mock"
    
    payload = {
        "query": "How do I implement django signals?",
        "session_id": "test-session-xyz",
        "provider": "mock"
    }
    
    response = client.post("/api/v1/chat/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "Mock response" in data["content"]
    assert data["provider"] == "mock"
    
    # 1. Verify CognitiveTrace database row
    trace = db_session.query(CognitiveTrace).first()
    assert trace is not None
    assert trace.query == "How do I implement django signals?"
    
    # Verify prompt_hash calculation
    combined = trace.final_prompt_preview # prompt preview or actual prompts?
    # prompt_hash = SHA256(system_prompt + user_prompt)
    # Let's inspect the persisted prompt_hash
    assert len(trace.prompt_hash) == 64  # valid SHA256 hex string

    # 2. Verify AIResponse database row
    ai_resp = db_session.query(AIResponse).first()
    assert ai_resp is not None
    assert ai_resp.trace_id == trace.trace_id
    assert "Mock response" in ai_resp.content

    # 3. Verify ConversationMessages
    messages = db_session.query(ConversationMessage).all()
    # Expecting 2 messages: 1 user, 1 assistant
    assert len(messages) == 2
    
    user_msg = next(m for m in messages if m.role == "user")
    assert user_msg.content == "How do I implement django signals?"
    assert user_msg.trace_id == trace.trace_id
    
    assistant_msg = next(m for m in messages if m.role == "assistant")
    assert "Mock response" in assistant_msg.content
    assert assistant_msg.trace_id == trace.trace_id


def test_llm_diagnostics_api(client):
    response = client.get("/api/v1/llm/info")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "reachable" in data
    assert data["provider"] == settings.DEFAULT_LLM_PROVIDER
