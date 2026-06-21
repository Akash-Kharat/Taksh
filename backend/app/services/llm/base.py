from app.services.llm.contracts import LLMRequest, LLMResponse

class BaseLLMProvider:
    """Base class defining standard interface for LLM client providers."""
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
        
    def validate_config(self) -> bool:
        raise NotImplementedError
        
    async def ping(self) -> bool:
        raise NotImplementedError
