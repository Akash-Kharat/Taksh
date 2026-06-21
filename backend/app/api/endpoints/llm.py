from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.services.llm.manager import LLMManager
from app.core.config import settings
from app.schemas.chat import LLMDiagnosticsResponse

router = APIRouter()

@router.get("/llm/info", response_model=LLMDiagnosticsResponse)
async def get_llm_diagnostics(db: DbSession = Depends(get_db)):
    llm_manager = LLMManager()
    
    # Check health on the default configured provider
    health = await llm_manager.check_health()
    
    # Key status
    key_status = "Configured" if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip() else "Missing"
    
    return {
        "configured": health["configured"],
        "reachable": health["reachable"],
        "last_successful_request": health["last_successful_request"],
        "provider": settings.DEFAULT_LLM_PROVIDER,
        "model": settings.DEFAULT_LLM_MODEL
    }
