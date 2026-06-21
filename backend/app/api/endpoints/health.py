from fastapi import APIRouter
from app.schemas.settings import HealthCheck
from app.core.logger import api_logger

router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def check_health():
    api_logger.info("Serving health status check")
    return HealthCheck(status="OK", project="Taksh", version="0.1")
