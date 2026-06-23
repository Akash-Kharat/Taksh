from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logger import api_logger
from app.services.health.manager import health_manager
from app.schemas.system import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health(db: Session = Depends(get_db)):
    """
    Unified health check endpoint.
    Aggregates status from all subsystems with per-check timeout protection.
    Returns 'healthy', 'degraded', or 'unhealthy' with per-component detail.
    """
    api_logger.info("Serving unified health status check")
    result = await health_manager.get_health(db)
    return result
