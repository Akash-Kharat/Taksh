import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.models.database_models import ConversationRuntimeSession, ConversationRuntimeTrace
from app.schemas.runtime import (
    RuntimeStartRequest,
    RuntimeStartResponse,
    RuntimeInterruptRequest,
    RuntimeInterruptResponse,
    RuntimeCloseRequest,
    RuntimeCloseResponse,
    RuntimeInfoResponse,
    RuntimeSessionDiagnosticsResponse,
)
from app.services.runtime.state_machine import RealtimeStateMachine, active_state_machines, TransitionError
from app.services.runtime.output_queue import AudioOutputQueue, active_output_queues
from app.services.runtime.interruption import InterruptionController

logger = logging.getLogger("runtime")

router = APIRouter(prefix="/runtime")


@router.post("/start", response_model=RuntimeStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(start_req: RuntimeStartRequest, db: DbSession = Depends(get_db)):
    """
    Initializes a new conversation runtime session in 'idle' state,
    registers state machine/output queue caches, and transitions to 'listening'.
    """
    logger.info("Initializing new runtime session")
    try:
        # 1. Create runtime session record
        db_session = ConversationRuntimeSession(
            voice_session_id=start_req.voice_session_id,
            conversation_state="idle",
            current_turn_owner="none",
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)

        # 2. Cache runtime state machine and output queue in-memory
        runtime_session_id = db_session.runtime_session_id
        sm = RealtimeStateMachine(runtime_session_id)
        active_state_machines[runtime_session_id] = sm
        active_output_queues[runtime_session_id] = AudioOutputQueue()

        # 3. Transition immediately to listening
        await sm.transition_to("listening", db)
        
        # Refresh to get latest state details
        db.refresh(db_session)
        return db_session
    except Exception as e:
        logger.error(f"Failed to start runtime session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session: {str(e)}"
        )


@router.post("/interrupt", response_model=RuntimeInterruptResponse)
async def interrupt_session(interrupt_req: RuntimeInterruptRequest, db: DbSession = Depends(get_db)):
    """
    Triggers an interruption for an active session, flushing the audio queue,
    transitioning state to 'interrupted', and incrementing interruption count.
    """
    runtime_session_id = interrupt_req.runtime_session_id
    logger.info(f"Received interruption request for session {runtime_session_id}")

    # Fetch session from DB to verify it exists
    session_rec = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.runtime_session_id == runtime_session_id
    ).first()
    if not session_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runtime session '{runtime_session_id}' not found."
        )

    sm = active_state_machines.get(runtime_session_id)
    if not sm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Runtime session '{runtime_session_id}' is not active or already closed."
        )

    try:
        await InterruptionController.trigger_interruption(runtime_session_id, db)
        db.refresh(session_rec)
        return RuntimeInterruptResponse(
            runtime_session_id=session_rec.runtime_session_id,
            conversation_state=session_rec.conversation_state,
            current_turn_owner=session_rec.current_turn_owner
        )
    except TransitionError as te:
        logger.warning(f"Failed transition during interrupt: {te}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(te)
        )
    except Exception as e:
        logger.error(f"Error during interruption handling: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/close", response_model=RuntimeCloseResponse)
async def close_session(close_req: RuntimeCloseRequest, db: DbSession = Depends(get_db)):
    """
    Closes the session, transitions state to 'closed', sets completion timestamp,
    and removes session cached resources from memory.
    """
    runtime_session_id = close_req.runtime_session_id
    logger.info(f"Received close request for session {runtime_session_id}")

    # Fetch session from DB
    session_rec = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.runtime_session_id == runtime_session_id
    ).first()
    if not session_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runtime session '{runtime_session_id}' not found."
        )

    sm = active_state_machines.get(runtime_session_id)
    if not sm:
        # If it exists in DB but is already closed
        if session_rec.conversation_state == "closed":
            return RuntimeCloseResponse(
                runtime_session_id=session_rec.runtime_session_id,
                conversation_state=session_rec.conversation_state,
                current_turn_owner=session_rec.current_turn_owner,
                ended_at=session_rec.ended_at
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Runtime session '{runtime_session_id}' state machine is inactive but database state is not 'closed'."
        )

    try:
        await sm.transition_to("closed", db)
        
        # Evict from active cache
        active_state_machines.pop(runtime_session_id, None)
        active_output_queues.pop(runtime_session_id, None)

        db.refresh(session_rec)
        return RuntimeCloseResponse(
            runtime_session_id=session_rec.runtime_session_id,
            conversation_state=session_rec.conversation_state,
            current_turn_owner=session_rec.current_turn_owner,
            ended_at=session_rec.ended_at
        )
    except TransitionError as te:
        logger.warning(f"Failed transition during close: {te}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(te)
        )
    except Exception as e:
        logger.error(f"Error during close handling: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/info", response_model=RuntimeInfoResponse)
def get_runtime_info(db: DbSession = Depends(get_db)):
    """
    Aggregates runtime statistics across all sessions.
    """
    logger.info("Aggregating runtime metrics")
    try:
        # Query total aggregations from database
        stats = db.query(
            func.count(ConversationRuntimeSession.runtime_session_id),
            func.sum(ConversationRuntimeSession.total_listening_ms),
            func.sum(ConversationRuntimeSession.total_thinking_ms),
            func.sum(ConversationRuntimeSession.total_speaking_ms),
            func.sum(ConversationRuntimeSession.interruption_count)
        ).first()

        active_count = len(active_state_machines)
        
        total_sessions = stats[0] or 0
        total_listening = stats[1] or 0
        total_thinking = stats[2] or 0
        total_speaking = stats[3] or 0
        total_interruption = stats[4] or 0

        return RuntimeInfoResponse(
            active_sessions_count=active_count,
            total_sessions_count=total_sessions,
            total_listening_ms=total_listening,
            total_thinking_ms=total_thinking,
            total_speaking_ms=total_speaking,
            total_interruption_count=total_interruption
        )
    except Exception as e:
        logger.error(f"Failed to query runtime info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/session/{runtime_session_id}", response_model=RuntimeSessionDiagnosticsResponse)
def get_session_diagnostics(runtime_session_id: str, db: DbSession = Depends(get_db)):
    """
    Fetches detailed diagnostics, state timers, and event tracing counts for a specific session.
    """
    logger.info(f"Fetching diagnostics for session {runtime_session_id}")
    session_rec = db.query(ConversationRuntimeSession).filter(
        ConversationRuntimeSession.runtime_session_id == runtime_session_id
    ).first()
    
    if not session_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runtime session '{runtime_session_id}' not found."
        )

    try:
        # Query event trace log count
        event_count = db.query(ConversationRuntimeTrace).filter(
            ConversationRuntimeTrace.runtime_session_id == runtime_session_id
        ).count()

        return RuntimeSessionDiagnosticsResponse(
            runtime_session_id=session_rec.runtime_session_id,
            voice_session_id=session_rec.voice_session_id,
            current_state=session_rec.conversation_state,
            turn_owner=session_rec.current_turn_owner,
            interruption_count=session_rec.interruption_count,
            event_count=event_count,
            total_listening_ms=session_rec.total_listening_ms,
            total_thinking_ms=session_rec.total_thinking_ms,
            total_speaking_ms=session_rec.total_speaking_ms,
            started_at=session_rec.started_at,
            ended_at=session_rec.ended_at
        )
    except Exception as e:
        logger.error(f"Failed to compile session diagnostics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
