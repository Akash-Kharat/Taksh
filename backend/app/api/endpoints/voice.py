from fastapi import APIRouter
from app.schemas.audio import VoiceDiagnostics
from app.services.voice.session_manager import voice_session_manager

router = APIRouter(prefix="/voice", tags=["voice"])

@router.get("/info", response_model=VoiceDiagnostics)
def get_voice_diagnostics():
    """
    Returns aggregated transport statistics for voice sessions,
    combining database aggregates and currently active in-memory sessions.
    """
    stats = voice_session_manager.get_aggregate_diagnostics()
    return stats
