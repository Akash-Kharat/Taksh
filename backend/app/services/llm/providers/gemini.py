import time
import httpx
from typing import Optional
from app.core.config import settings
from app.core.logger import system_logger
from app.services.llm.base import BaseLLMProvider
from app.services.llm.contracts import LLMRequest, LLMResponse
from app.services.llm.retry import execute_with_retry

class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini REST API provider executing via HTTP client."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_LLM_MODEL

    def _get_api_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={settings.GEMINI_API_KEY}"

    def validate_config(self) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    async def ping(self) -> bool:
        if not self.validate_config():
            return False
        
        # Cheap, fast endpoint generation ping test
        url = self._get_api_url()
        payload = {
            "contents": [{"parts": [{"text": "ping"}]}],
            "generationConfig": {"maxOutputTokens": 1}
        }
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(url, json=payload)
                return response.status_code == 200
        except Exception as e:
            system_logger.warning(f"Gemini API ping check failed: {e}")
            return False

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        
        if not self.validate_config():
            return LLMResponse(
                status="provider_error",
                provider="gemini",
                model_name=self.model_name,
                latency_ms=0,
                error_message="GEMINI_API_KEY is not configured."
            )

        # Prepare request payload
        temperature = request.temperature if request.temperature is not None else settings.DEFAULT_TEMPERATURE
        max_tokens = request.max_tokens if request.max_tokens is not None else settings.DEFAULT_MAX_TOKENS

        payload = {
            "contents": [
                {
                    "parts": [{"text": request.user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": request.system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        url = self._get_api_url()
        
        async def make_api_call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        try:
            # Wrap the HTTP call inside the retry strategy
            res_json = await execute_with_retry(make_api_call)
            
            # Parse responses
            candidates = res_json.get("candidates", [])
            if not candidates:
                return LLMResponse(
                    status="invalid_response",
                    provider="gemini",
                    model_name=self.model_name,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    error_message="Gemini API returned empty candidates list."
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                return LLMResponse(
                    status="invalid_response",
                    provider="gemini",
                    model_name=self.model_name,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    error_message="Gemini API returned invalid response layout format."
                )

            content = parts[0]["text"]
            
            # Usage metadata parsing
            usage = res_json.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount")
            completion_tokens = usage.get("candidatesTokenCount")
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            return LLMResponse(
                status="success",
                content=content,
                provider="gemini",
                model_name=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms
            )

        except httpx.TimeoutException as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return LLMResponse(
                status="timeout",
                provider="gemini",
                model_name=self.model_name,
                latency_ms=latency_ms,
                error_message=f"Gemini API request timed out: {e}"
            )
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return LLMResponse(
                status="provider_error",
                provider="gemini",
                model_name=self.model_name,
                latency_ms=latency_ms,
                error_message=f"Gemini API failure: {e}"
            )
