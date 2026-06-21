from fastapi import APIRouter
from app.schemas.settings import AppSettings
from app.core.logger import api_logger

router = APIRouter()

@router.get("/settings", response_model=AppSettings)
async def get_settings():
    api_logger.info("Fetching application configurations")
    return AppSettings()

@router.post("/settings", response_model=AppSettings)
async def update_settings(new_settings: AppSettings):
    api_logger.info(f"Updating application configurations: Mode={new_settings.personality_mode}")
    return new_settings
