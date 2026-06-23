from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.logger import api_logger
from app.models.database_models import (
    ConversationProfile,
    PreferenceMemory,
    ProjectMemory,
    ProjectSnapshot,
    ConversationRuntimeSession,
    ConversationTurn,
    ConversationMetrics,
    ProviderSession
)
from app.schemas.conversation import (
    ConversationInfoResponse,
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationMessageRequest,
    ConversationMessageResponse,
    ConversationStopRequest,
    ConversationSessionDetailResponse,
    ConversationTurnSchema,
    ConversationMetricsSchema,
    ConversationSessionResponse,
    PaginatedConversationSessionsResponse
)
from app.services.conversation.coordinator import conversation_coordinator
from app.services.conversation.playback import playback_controller

router = APIRouter(prefix="/conversation", tags=["Conversation Intelligence"])


@router.get("/info", response_model=ConversationInfoResponse)
def conversation_info(db: Session = Depends(get_db)) -> ConversationInfoResponse:
    """Return counts and metadata summarizing current long-term continuity state."""
    profiles_count = db.query(ConversationProfile).count()
    preferences_count = db.query(PreferenceMemory).count()
    projects_count = db.query(ProjectMemory).count()
    snapshots_count = db.query(ProjectSnapshot).count()

    active_project_name = None
    profile = db.query(ConversationProfile).first()
    if profile and profile.active_project_id:
        active_project = (
            db.query(ProjectMemory)
            .filter(ProjectMemory.project_memory_id == profile.active_project_id)
            .first()
        )
        if active_project:
            active_project_name = active_project.project_name

    # Pipeline diagnostics (MS-17)
    active_sessions = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.conversation_session_state == "active"
    ).count()

    total_turns = db.query(func.sum(ConversationMetrics.total_turns)).scalar()
    total_turns = int(total_turns) if total_turns is not None else 0

    avg_turn = db.query(func.avg(ConversationMetrics.average_turn_latency_ms)).scalar()
    avg_turn_latency_ms = float(avg_turn) if avg_turn is not None else 0.0

    avg_stt = db.query(func.avg(ConversationMetrics.average_stt_latency_ms)).scalar()
    avg_stt_latency_ms = float(avg_stt) if avg_stt is not None else 0.0

    avg_llm = db.query(func.avg(ConversationMetrics.average_llm_latency_ms)).scalar()
    avg_llm_latency_ms = float(avg_llm) if avg_llm is not None else 0.0

    avg_tts = db.query(func.avg(ConversationMetrics.average_tts_latency_ms)).scalar()
    avg_tts_latency_ms = float(avg_tts) if avg_tts is not None else 0.0

    # Aggregate fallbacks and playback queue depths
    provider_fallbacks = sum(conversation_coordinator.provider_fallbacks.values())
    playback_queue_depth = sum(len(q) for q in playback_controller.playback_queues.values())

    return ConversationInfoResponse(
        profiles=profiles_count,
        preferences=preferences_count,
        projects=projects_count,
        snapshots=snapshots_count,
        active_project=active_project_name,
        active_sessions=active_sessions,
        total_turns=total_turns,
        avg_turn_latency_ms=avg_turn_latency_ms,
        avg_stt_latency_ms=avg_stt_latency_ms,
        avg_llm_latency_ms=avg_llm_latency_ms,
        avg_tts_latency_ms=avg_tts_latency_ms,
        provider_fallbacks=provider_fallbacks,
        playback_queue_depth=playback_queue_depth
    )


@router.post("/start", response_model=ConversationStartResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    req: ConversationStartRequest,
    db: Session = Depends(get_db)
) -> ConversationStartResponse:
    """Creates a new runtime session and correlated memory session."""
    runtime_session = await conversation_coordinator.start_conversation(db, req.voice_session_id)
    return ConversationStartResponse(
        runtime_session_id=runtime_session.runtime_session_id,
        voice_session_id=runtime_session.voice_session_id,
        conversation_state=runtime_session.conversation_state,
        conversation_session_state=runtime_session.conversation_session_state
    )


@router.post("/message", response_model=ConversationMessageResponse)
async def send_message(
    req: ConversationMessageRequest,
    db: Session = Depends(get_db)
) -> ConversationMessageResponse:
    """Injects a text message directly into the conversation pipeline for execution."""
    try:
        turn = await conversation_coordinator.process_message(db, req.runtime_session_id, user_text=req.message)
        return ConversationMessageResponse(
            assistant_text=turn.assistant_text,
            turn_id=turn.turn_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@router.post("/stop")
async def stop_conversation(
    req: ConversationStopRequest,
    db: Session = Depends(get_db)
):
    """Gracefully terminates a session and executes long-term memory consolidation."""
    await conversation_coordinator.stop_conversation(db, req.runtime_session_id)
    return {"status": "stopped", "runtime_session_id": req.runtime_session_id}


@router.get("/session/{id}", response_model=ConversationSessionDetailResponse)
def get_session_details(
    id: str,
    db: Session = Depends(get_db)
) -> ConversationSessionDetailResponse:
    """Returns detailed turns history, metrics, providers, and summary status of a session."""
    session_rec = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.runtime_session_id == id
    ).first()
    if not session_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{id}' not found."
        )

    turns = db.query(ConversationTurn).filter(
        ConversationTurn.runtime_session_id == id
    ).order_by(ConversationTurn.started_at.asc()).all()

    metrics = db.query(ConversationMetrics).filter(
        ConversationMetrics.runtime_session_id == id
    ).first()

    # Query provider session details linked to runtime session
    prov_session = db.query(ProviderSession).filter(
        ProviderSession.runtime_session_id == id
    ).order_by(ProviderSession.connected_at.desc()).first()

    provider_info = None
    if prov_session:
        provider_info = {
            "provider_name": prov_session.provider_name,
            "provider_state": prov_session.provider_state,
            "messages_sent": prov_session.messages_sent,
            "messages_received": prov_session.messages_received,
            "audio_frames_sent": prov_session.audio_frames_sent,
            "audio_frames_received": prov_session.audio_frames_received,
            "average_response_latency_ms": prov_session.average_response_latency_ms,
            "max_response_latency_ms": prov_session.max_response_latency_ms
        }

    turn_schemas = []
    for t in turns:
        schema = ConversationTurnSchema.model_validate(t)
        # Fetch prompt/completion tokens
        schema.prompt_tokens = t.ai_response.prompt_tokens if t.ai_response else None
        schema.completion_tokens = t.ai_response.completion_tokens if t.ai_response else None
        
        # Fetch memory/knowledge hits
        schema.knowledge_hits = len(t.cognitive_trace.knowledge_chunks) if (t.cognitive_trace and t.cognitive_trace.knowledge_chunks) else 0
        
        schema.memory_hits = 0
        if t.cognitive_trace and t.cognitive_trace.memory_items:
            m_items = t.cognitive_trace.memory_items
            schema.memory_hits = len(m_items.get("active_goals", [])) + len(m_items.get("recent_events", []))
            
        schema.message_version = t.message_version if t.message_version else 1
        turn_schemas.append(schema)

    return ConversationSessionDetailResponse(
        turns=turn_schemas,
        metrics=ConversationMetricsSchema.model_validate(metrics) if metrics else None,
        provider_info=provider_info,
        interruptions=session_rec.interruption_count,
        session_summary=session_rec.session_summary_status
    )


@router.get("/sessions", response_model=PaginatedConversationSessionsResponse)
def list_conversation_sessions(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db)
) -> PaginatedConversationSessionsResponse:
    """Returns a paginated list of conversation sessions with metadata and last message preview."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 25

    total = db.query(ConversationRuntimeSession).count()
    offset = (page - 1) * page_size

    sessions = (
        db.query(ConversationRuntimeSession)
        .order_by(ConversationRuntimeSession.started_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for s in sessions:
        last_turn = (
            db.query(ConversationTurn)
            .filter(ConversationTurn.runtime_session_id == s.runtime_session_id)
            .order_by(ConversationTurn.started_at.desc())
            .first()
        )
        
        last_message = last_turn.user_text if last_turn else None
        
        items.append(
            ConversationSessionResponse(
                runtime_session_id=s.runtime_session_id,
                conversation_title=s.conversation_title,
                conversation_session_state=s.conversation_session_state,
                started_at=s.started_at,
                ended_at=s.ended_at,
                last_message=last_message
            )
        )

    return PaginatedConversationSessionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
