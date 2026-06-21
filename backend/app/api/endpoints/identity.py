from fastapi import APIRouter
from app.schemas.identity import CoreIdentityResponse, CoreIdentityInfoResponse
from app.services.memory.identity import CoreIdentityManager

router = APIRouter(prefix="/identity")

@router.get("/", response_model=CoreIdentityResponse)
def get_core_identity():
    manager = CoreIdentityManager()
    return CoreIdentityResponse(identity=manager.get_identity())

@router.get("/info", response_model=CoreIdentityInfoResponse)
def get_core_identity_info():
    manager = CoreIdentityManager()
    return CoreIdentityInfoResponse(**manager.get_metadata())
