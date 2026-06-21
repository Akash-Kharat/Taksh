import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core.logger import api_logger
from app.services.cognitive.orchestrator import CognitiveOrchestrator
from app.services.llm.manager import LLMManager
from app.services.llm.contracts import LLMRequest
from app.models.database_models import AIResponse, ConversationMessage, Session
from app.repositories.session import session_repo
from app.schemas.chat import ChatGenerateRequest, ChatGenerateResponse

router = APIRouter()

@router.post("/chat/generate", response_model=ChatGenerateResponse)
async def generate_chat_response(
    payload: ChatGenerateRequest,
    db: DbSession = Depends(get_db)
):
    api_logger.info(f"Received generation request for query: '{payload.query}'")
    
    # 1. Resolve or create a session if session_id is not provided
    session_id = payload.session_id
    if not session_id:
        # Create a new session
        db_session = session_repo.create(db, Session())
        session_id = db_session.session_id
    else:
        # Check if session exists in DB, otherwise create/verify
        db_session = session_repo.get(db, session_id)
        if not db_session:
            db_session = Session(session_id=session_id)
            db.add(db_session)
            db.flush()

    # 2. Run orchestrator to compile prompt package and log CognitiveTrace
    orchestrator = CognitiveOrchestrator()
    plan = orchestrator.generate_plan(db, payload.query, session_id=session_id)
    
    trace_id = plan["decision_trace"]["trace_id"]
    prompt_pkg = plan["prompt_package"]

    # 3. Create request payload for the LLM Manager
    llm_request = LLMRequest(
        system_prompt=prompt_pkg["system_prompt"],
        user_prompt=prompt_pkg["user_prompt"]
    )

    # 4. Invoke LLM Manager (which select provider, handles retries, and catches errors)
    llm_manager = LLMManager()
    response = await llm_manager.generate(llm_request, provider_name=payload.provider)

    # 5. Persist ConversationMessage for the User query
    user_message = ConversationMessage(
        session_id=session_id,
        role="user",
        content=payload.query,
        trace_id=trace_id
    )
    db.add(user_message)

    response_id = str(uuid.uuid4())

    # 6. Handle response outcomes
    if response.status == "success":
        # Save assistant message
        assistant_message = ConversationMessage(
            session_id=session_id,
            role="assistant",
            content=response.content,
            trace_id=trace_id
        )
        db.add(assistant_message)

        # Save AIResponse
        ai_resp_record = AIResponse(
            response_id=response_id,
            trace_id=trace_id,
            content=response.content,
            provider=response.provider,
            model_name=response.model_name,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms
        )
        db.add(ai_resp_record)
    else:
        # If generation failed, save AIResponse with failure status explanation
        error_content = f"Generation failed: {response.error_message or 'unknown error'}"
        ai_resp_record = AIResponse(
            response_id=response_id,
            trace_id=trace_id,
            content=error_content,
            provider=response.provider,
            model_name=response.model_name,
            latency_ms=response.latency_ms
        )
        db.add(ai_resp_record)

    db.commit()

    return ChatGenerateResponse(
        response_id=response_id,
        trace_id=trace_id,
        content=response.content,
        provider=response.provider,
        model_name=response.model_name,
        status=response.status,
        latency_ms=response.latency_ms
    )
