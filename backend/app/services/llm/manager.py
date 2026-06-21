import time
import threading
from datetime import datetime
from typing import Dict, Optional, Any

from app.core.config import settings
from app.core.logger import system_logger
from app.services.llm.base import BaseLLMProvider
from app.services.llm.contracts import LLMRequest, LLMResponse
from app.services.llm.providers.mock import MockLLMProvider
from app.services.llm.providers.gemini import GeminiLLMProvider

class LLMManager:
    """Manager service coordinating standard LLM client provider lifecycles. Thread-safe Singleton."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LLMManager, cls).__new__(cls)
                    cls._instance._providers = {
                        "mock": MockLLMProvider(),
                        "gemini": GeminiLLMProvider()
                    }
                    cls._instance.last_successful_request: Optional[datetime] = None
        return cls._instance

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """Resolves provider name to instance, falling back to configuration default."""
        provider_name = name or settings.DEFAULT_LLM_PROVIDER
        provider = self._providers.get(provider_name.lower())
        if not provider:
            system_logger.warning(f"Requested LLM provider '{provider_name}' not found. Falling back to 'mock'.")
            return self._providers["mock"]
        return provider

    async def generate(self, request: LLMRequest, provider_name: Optional[str] = None) -> LLMResponse:
        """Executes LLM request against the selected provider and logs metrics."""
        provider = self.get_provider(provider_name)
        
        system_logger.info(f"Dispatching LLM generation to provider: {type(provider).__name__}")
        start_time = time.perf_counter()
        
        try:
            response = await provider.generate_response(request)
            
            # Record last successful request time if successful
            if response.status == "success":
                self.last_successful_request = datetime.utcnow()
                
            return response
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            system_logger.error(f"LLM Manager encountered error: {e}")
            return LLMResponse(
                status="provider_error",
                provider=provider_name or settings.DEFAULT_LLM_PROVIDER,
                model_name=getattr(provider, "model_name", "unknown"),
                latency_ms=latency_ms,
                error_message=f"LLM Manager unhandled execution error: {e}"
            )
            
    async def check_health(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Runs diagnostics on the selected provider."""
        provider = self.get_provider(provider_name)
        
        configured = provider.validate_config()
        reachable = False
        if configured:
            reachable = await provider.ping()
            
        return {
            "configured": configured,
            "reachable": reachable,
            "last_successful_request": self.last_successful_request
        }
