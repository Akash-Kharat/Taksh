import time
from app.services.llm.base import BaseLLMProvider
from app.services.llm.contracts import LLMRequest, LLMResponse

class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider for local development and testing."""

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        
        # Simulate local computation time
        content = f"Mock response output matching your system and user prompt directives. Request query details: user_prompt length = {len(request.user_prompt)}."
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return LLMResponse(
            status="success",
            content=content,
            provider="mock",
            model_name="mock-model",
            prompt_tokens=len(request.system_prompt.split()) + len(request.user_prompt.split()),
            completion_tokens=len(content.split()),
            latency_ms=latency_ms
        )

    def validate_config(self) -> bool:
        return True

    async def ping(self) -> bool:
        return True
