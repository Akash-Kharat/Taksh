import logging
import uuid
import time
import asyncio
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.database_models import (
    ConversationRuntimeSession,
    ConversationTurn,
    ConversationMetrics,
    CognitiveTrace,
    AIResponse,
    Session as MemorySession,
    MemoryEvent,
    TextPayload
)
from app.services.runtime.state_machine import RealtimeStateMachine, active_state_machines
from app.services.runtime.output_queue import AudioOutputQueue, active_output_queues
from app.services.providers.manager import provider_manager
from app.services.cognitive.orchestrator import CognitiveOrchestrator
from app.services.llm.manager import LLMManager
from app.services.llm.contracts import LLMRequest
from app.services.conversation.playback import playback_controller

logger = logging.getLogger("conversation")

class ConversationCoordinator:
    """Master orchestrator for End-to-End Voice Conversation sessions and pipelines."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConversationCoordinator, cls).__new__(cls)
            cls._instance.cognitive_orchestrator = CognitiveOrchestrator()
            cls._instance.llm_manager = LLMManager()
            # Cache to track provider fallback count per session
            cls._instance.provider_fallbacks: Dict[str, int] = {}
        return cls._instance

    async def start_conversation(self, db: Session, voice_session_id: Optional[str] = None) -> ConversationRuntimeSession:
        """
        Creates a new conversation session, including both Runtime and correlated long-term memory Session records.
        Transitions the runtime state to 'listening'.
        """
        v_sess_id = voice_session_id or f"voice-session-{uuid.uuid4()}"
        
        # 1. Create long-term memory Session record (correlated with runtime session ID)
        memory_session_id = f"rt-session-{uuid.uuid4()}"
        mem_session = MemorySession(session_id=memory_session_id)
        db.add(mem_session)
        
        # 2. Create runtime session record
        runtime_session = ConversationRuntimeSession(
            runtime_session_id=memory_session_id,
            voice_session_id=v_sess_id,
            conversation_state="idle",
            conversation_session_state="active",
            current_turn_owner="none",
        )
        db.add(runtime_session)
        
        # 3. Create conversation metrics record
        metrics = ConversationMetrics(
            runtime_session_id=memory_session_id,
            total_turns=0,
            average_turn_latency_ms=0.0,
            average_stt_latency_ms=0.0,
            average_llm_latency_ms=0.0,
            average_tts_latency_ms=0.0,
            total_interruptions=0,
            playback_dropped_chunks=0
        )
        db.add(metrics)
        
        db.commit()
        db.refresh(runtime_session)

        # 4. Cache state machine and output queue in-memory
        sm = RealtimeStateMachine(memory_session_id)
        active_state_machines[memory_session_id] = sm
        active_output_queues[memory_session_id] = AudioOutputQueue()

        # 5. Initialize fallback cache
        self.provider_fallbacks[memory_session_id] = 0

        # 6. Immediately transition state machine to listening
        await sm.transition_to("listening", db)

        logger.info(f"Started continuous voice conversation session {memory_session_id} correlated with voice session {v_sess_id}")
        return runtime_session

    async def process_message(
        self,
        db: Session,
        runtime_session_id: str,
        user_text: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        provider_name: Optional[str] = None
    ) -> ConversationTurn:
        """
        Coordinates full conversational execution pipeline:
        User Input -> STT -> Context -> Plan -> LLM -> TTS -> Audio playback.
        """
        start_time = time.perf_counter()
        
        # 1. Resolve runtime session and state machine
        session_rec = db.query(ConversationRuntimeSession).filter(
            ConversationRuntimeSession.runtime_session_id == runtime_session_id
        ).first()
        if not session_rec:
            raise ValueError(f"Runtime session '{runtime_session_id}' not found.")
        
        # Ensure session is active
        if session_rec.conversation_session_state != "active":
            raise RuntimeError(f"Conversation session '{runtime_session_id}' is closed or failed.")

        sm = active_state_machines.get(runtime_session_id)
        if not sm:
            sm = RealtimeStateMachine(runtime_session_id)
            active_state_machines[runtime_session_id] = sm

        # 2. Convert Audio to Text (STT) if audio_bytes provided
        stt_start = time.perf_counter()
        stt_latency = 0.0
        
        if audio_bytes:
            # Transition state machine to thinking
            await sm.transition_to("thinking", db)
            try:
                resolved_stt = provider_name
                if provider_manager.fallback_active and settings.ENABLE_PROVIDER_FALLBACK:
                    resolved_stt = "mock"
                user_text = await provider_manager.transcribe_audio(
                    runtime_session_id=runtime_session_id,
                    audio_bytes=audio_bytes,
                    provider_name=resolved_stt,
                    db=db
                )
                stt_latency = (time.perf_counter() - stt_start) * 1000
            except Exception as e:
                # Session remains alive (Revision 6)
                logger.error(f"STT generation failed: {e}. Falling back to mock/text-only mode.")
                self.provider_fallbacks[runtime_session_id] = self.provider_fallbacks.get(runtime_session_id, 0) + 1
                
                # Fallback to mock transcription
                user_text = "STT Error fallback text"
                stt_latency = (time.perf_counter() - stt_start) * 1000

        # Ensure user_text is present
        if not user_text:
            user_text = ""

        # Auto-generate title if not present (Revision 1)
        if not session_rec.conversation_title and user_text:
            session_rec.conversation_title = user_text[:80]

        # 3. Assemble context & invoke Cognitive Orchestrator
        # ContextBuilder will load last 10 turns (budget limit)
        plan = self.cognitive_orchestrator.generate_plan(db, user_text, session_id=runtime_session_id)
        prompt_package = plan["prompt_package"]
        decision_trace = plan["decision_trace"]
        cognitive_trace_id = decision_trace.get("trace_id")
        
        # 4. Generate LLM response
        llm_start = time.perf_counter()
        llm_request = LLMRequest(
            system_prompt=prompt_package["system_prompt"],
            user_prompt=prompt_package["user_prompt"]
        )
        
        llm_provider = settings.DEFAULT_LLM_PROVIDER
        llm_response = await self.llm_manager.generate(llm_request, provider_name=llm_provider)
        llm_latency = (time.perf_counter() - llm_start) * 1000
        
        assistant_text = llm_response.content or "No response content generated."
        
        # 5. Persist AIResponse record
        ai_resp_id = f"ai-resp-{uuid.uuid4()}"
        ai_resp_record = AIResponse(
            response_id=ai_resp_id,
            trace_id=cognitive_trace_id if cognitive_trace_id != "failed-to-save" else None,
            content=assistant_text,
            provider=llm_response.provider,
            model_name=llm_response.model_name,
            prompt_tokens=llm_response.prompt_tokens or 0,
            completion_tokens=llm_response.completion_tokens or 0,
            latency_ms=llm_response.latency_ms
        )
        db.add(ai_resp_record)
        db.flush()

        # 6. Streaming TTS responses and budget controls (Revision 2 & 4)
        # Split text into segments (sentence/punctuation chunking)
        import re
        segments = [s.strip() for s in re.split(r"([.!?\n]+)", assistant_text) if s.strip()]
        # Recombine delimiters back to sentences
        recombined = []
        i = 0
        while i < len(segments):
            seg = segments[i]
            if i + 1 < len(segments) and re.match(r"^[.!?\n]+$", segments[i + 1]):
                seg += segments[i + 1]
                i += 1
            recombined.append(seg)
            i += 1

        accumulated_chars = 0
        segment_count = 0
        response_truncated = False
        tts_start = time.perf_counter()
        
        for segment in recombined:
            if accumulated_chars + len(segment) > settings.MAX_RESPONSE_CHARS:
                response_truncated = True
                logger.warning(f"Response character budget exceeded limit ({settings.MAX_RESPONSE_CHARS} chars). Truncating.")
                break
            if segment_count >= settings.MAX_RESPONSE_SEGMENTS:
                response_truncated = True
                logger.warning(f"Response segment budget exceeded limit ({settings.MAX_RESPONSE_SEGMENTS} segments). Truncating.")
                break

            accumulated_chars += len(segment)
            segment_count += 1

            # Invoke TTS chunk synthesis (Revision 4)
            try:
                resolved_tts = provider_name
                if provider_manager.fallback_active and settings.ENABLE_PROVIDER_FALLBACK:
                    resolved_tts = "mock"
                audio_chunk = await provider_manager.synthesize_speech(
                    runtime_session_id=runtime_session_id,
                    text=segment,
                    provider_name=resolved_tts,
                    db=db
                )
                # Queue synthesized audio chunk to playback controller
                await playback_controller.enqueue_audio(runtime_session_id, audio_chunk, db=db)
            except Exception as e:
                logger.error(f"TTS synthesis chunk failed for segment '{segment}': {e}")
                self.provider_fallbacks[runtime_session_id] = self.provider_fallbacks.get(runtime_session_id, 0) + 1

        tts_latency = (time.perf_counter() - tts_start) * 1000
        total_latency = (time.perf_counter() - start_time) * 1000

        # If truncated, slice assistant_text to matches the budget
        if response_truncated:
            assistant_text = assistant_text[:accumulated_chars] + "... [truncated]"

        # 7. Create ConversationTurn record
        prompt_hash = plan["prompt_package"]["preview"]
        import hashlib
        prompt_hash = hashlib.sha256(prompt_hash.encode("utf-8")).hexdigest()
        
        turn = ConversationTurn(
            runtime_session_id=runtime_session_id,
            voice_session_id=session_rec.voice_session_id,
            user_text=user_text,
            assistant_text=assistant_text,
            prompt_hash=prompt_hash,
            provider_name=provider_name or settings.DEFAULT_REALTIME_PROVIDER,
            latency_ms=total_latency,
            started_at=datetime.fromtimestamp(start_time),
            completed_at=datetime.utcnow(),
            cognitive_trace_id=cognitive_trace_id if cognitive_trace_id != "failed-to-save" else None,
            ai_response_id=ai_resp_id,
            segment_count=segment_count,
            response_truncated=response_truncated,
            message_version=1
        )
        db.add(turn)
        db.flush()

        # 8. Create memory event records for SessionConsolidator
        mem_event_id = f"mem-ev-{uuid.uuid4()}"
        ev = MemoryEvent(
            event_id=mem_event_id,
            session_id=runtime_session_id,
            primary_modality="text"
        )
        tp = TextPayload(
            event_id=mem_event_id,
            transcript=f"User: {user_text}\nAssistant: {assistant_text}"
        )
        db.add_all([ev, tp])

        # 9. Update ConversationMetrics
        metrics_rec = db.query(ConversationMetrics).filter(
            ConversationMetrics.runtime_session_id == runtime_session_id
        ).first()
        if metrics_rec:
            # Recompute rolling averages
            n = metrics_rec.total_turns
            metrics_rec.total_turns += 1
            metrics_rec.average_turn_latency_ms = (metrics_rec.average_turn_latency_ms * n + total_latency) / (n + 1)
            metrics_rec.average_stt_latency_ms = (metrics_rec.average_stt_latency_ms * n + stt_latency) / (n + 1)
            metrics_rec.average_llm_latency_ms = (metrics_rec.average_llm_latency_ms * n + llm_latency) / (n + 1)
            metrics_rec.average_tts_latency_ms = (metrics_rec.average_tts_latency_ms * n + tts_latency) / (n + 1)
            metrics_rec.total_interruptions = session_rec.interruption_count
        
        db.commit()
        db.refresh(turn)

        # 10. Start audio playback simulation in background (asynchronous)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(playback_controller.simulate_playback(runtime_session_id, db))
        
        logger.info(f"Processed turn: user='{user_text}', assistant='{assistant_text}' (latency={total_latency:.1f}ms)")
        return turn

    async def stop_conversation(self, db: Session, runtime_session_id: str) -> None:
        """
        Closes the active conversation session.
        Invokes SessionConsolidator wrapped in isolated try-except to prevent shutdown failures.
        """
        session_rec = db.query(ConversationRuntimeSession).filter(
            ConversationRuntimeSession.runtime_session_id == runtime_session_id
        ).first()
        if not session_rec:
            logger.warning(f"Runtime session '{runtime_session_id}' not found for stop.")
            return

        session_rec.conversation_session_state = "closed"
        session_rec.ended_at = datetime.utcnow()
        db.commit()

        # Update runtime state machine to closed
        sm = active_state_machines.get(runtime_session_id)
        if sm:
            await sm.transition_to("closed", db)

        # Clear playback queue
        playback_controller.flush(runtime_session_id)

        # Invoke SessionConsolidator safely (Revision 6)
        try:
            from app.services.conversation.consolidation import SessionConsolidator
            SessionConsolidator.consolidate_session(db, runtime_session_id)
            session_rec.session_summary_status = "completed"
            db.commit()
            logger.info(f"Successfully consolidated long-term memory for session {runtime_session_id}")
        except Exception as e:
            logger.error(f"Long-term memory consolidation failed for session {runtime_session_id}: {e}")
            session_rec.session_summary_status = "failed"
            db.commit()

        # Invoke Episodic Memory Consolidation safely (Milestone-18)
        try:
            from app.services.conversation.episodic_memory_service import episodic_memory_service
            await episodic_memory_service.consolidate_episodic_memory(db, runtime_session_id)
            logger.info(f"Successfully consolidated episodic memory for session {runtime_session_id}")
        except Exception as e:
            logger.error(f"Episodic memory consolidation failed for session {runtime_session_id}: {e}")


# Global conversation coordinator singleton instance
conversation_coordinator = ConversationCoordinator()
