"""
Taksh Smoke Test Framework — MS-20

Deployment-level validation that exercises the entire Taksh stack.
Each test is isolated — one failure never prevents others from running.

Categories covered:
  - Runtime    (session create / close)
  - Memory     (episode create / retrieve)
  - Knowledge  (ingest / search)
  - Provider   (mock generate / mock STT / mock TTS)
  - Conversation (start / message / stop)

Usage:
  runner = SmokeTestRunner()
  report = runner.run_all(db)
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import List

from sqlalchemy.orm import Session

logger = logging.getLogger("smoke_tests")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SmokeTestResult:
    category:    str
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str = ""


@dataclass
class SmokeTestReport:
    results:          List[SmokeTestResult]
    total:            int
    passed:           int
    failed:           int
    total_duration_ms: float


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class SmokeTestRunner:
    """Runs the full deployment smoke test suite."""

    def run_all(self, db: Session) -> SmokeTestReport:
        t0 = time.perf_counter()
        results: List[SmokeTestResult] = []

        results += self._run_runtime_tests(db)
        results += self._run_memory_tests(db)
        results += self._run_knowledge_tests(db)
        results += self._run_provider_tests(db)
        results += self._run_conversation_tests(db)

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        total    = len(results)
        passed   = sum(1 for r in results if r.passed)
        failed   = total - passed

        logger.info(
            f"[smoke_tests] Completed {total} tests: "
            f"{passed} passed, {failed} failed in {total_ms}ms"
        )

        return SmokeTestReport(
            results           = results,
            total             = total,
            passed            = passed,
            failed            = failed,
            total_duration_ms = total_ms,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run(self, category: str, name: str, fn) -> SmokeTestResult:
        """Execute a single smoke test, catching all exceptions."""
        t0 = time.perf_counter()
        try:
            detail = fn() or "OK"
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            return SmokeTestResult(
                category=category, name=name,
                passed=True, duration_ms=dur_ms, detail=str(detail),
            )
        except Exception as exc:
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.warning(f"[smoke_tests] FAIL {category}/{name}: {exc}")
            return SmokeTestResult(
                category=category, name=name,
                passed=False, duration_ms=dur_ms, detail=str(exc),
            )

    # ------------------------------------------------------------------
    # Category: Runtime
    # ------------------------------------------------------------------

    def _run_runtime_tests(self, db: Session) -> List[SmokeTestResult]:
        results = []
        session_id: List[str] = []

        def create_session():
            from app.models.database_models import ConversationRuntimeSession
            sid = f"smoke-{uuid.uuid4().hex[:8]}"
            s = ConversationRuntimeSession(
                runtime_session_id         = sid,
                conversation_state         = "listening",
                conversation_session_state = "active",
                current_turn_owner         = "none",
            )
            db.add(s)
            db.flush()
            session_id.append(sid)
            return f"session_id={sid}"

        def close_session():
            if not session_id:
                raise RuntimeError("No session to close")
            from app.models.database_models import ConversationRuntimeSession
            from datetime import datetime
            s = db.query(ConversationRuntimeSession).filter(
                ConversationRuntimeSession.runtime_session_id == session_id[0]
            ).first()
            if not s:
                raise RuntimeError("Session not found after create")
            s.conversation_session_state = "closed"
            s.ended_at = datetime.utcnow()
            db.flush()
            return f"closed session_id={session_id[0]}"

        results.append(self._run("Runtime", "Create session", create_session))
        results.append(self._run("Runtime", "Close session", close_session))
        return results

    # ------------------------------------------------------------------
    # Category: Memory
    # ------------------------------------------------------------------

    def _run_memory_tests(self, db: Session) -> List[SmokeTestResult]:
        results = []
        episode_id: List[int] = []

        def create_episode():
            from app.models.database_models import MemoryEpisode
            ep = MemoryEpisode(
                session_id      = f"smoke-{uuid.uuid4().hex[:8]}",
                memory_type     = "episodic",
                title           = "Smoke test episode",
                summary         = "Created by MS-20 smoke test",
                key_decisions   = [],
                important_facts = [],
                open_tasks      = [],
                importance_score = 0.5,
            )
            db.add(ep)
            db.flush()
            db.refresh(ep)
            episode_id.append(ep.id)
            return f"episode_id={ep.id}"

        def retrieve_episode():
            if not episode_id:
                raise RuntimeError("No episode to retrieve")
            from app.models.database_models import MemoryEpisode
            ep = db.query(MemoryEpisode).filter(
                MemoryEpisode.id == episode_id[0]
            ).first()
            if not ep:
                raise RuntimeError("Episode not found after create")
            return f"retrieved title='{ep.title}'"

        results.append(self._run("Memory", "Create episode", create_episode))
        results.append(self._run("Memory", "Retrieve episode", retrieve_episode))
        return results

    # ------------------------------------------------------------------
    # Category: Knowledge
    # ------------------------------------------------------------------

    def _run_knowledge_tests(self, db: Session) -> List[SmokeTestResult]:
        results = []

        def ingest_chunk():
            from app.services.knowledge.vector_store import ChromaDBClient
            client = ChromaDBClient()
            col = client.client.get_or_create_collection("smoke_test_col")
            doc_id = f"smoke-{uuid.uuid4().hex[:8]}"
            col.add(
                documents=["Smoke test knowledge chunk for MS-20 validation"],
                ids=[doc_id],
            )
            return f"ingested doc_id={doc_id}"

        def search_chunk():
            from app.services.knowledge.vector_store import ChromaDBClient
            client = ChromaDBClient()
            col = client.client.get_or_create_collection("smoke_test_col")
            results_q = col.query(
                query_texts=["smoke test knowledge"],
                n_results=1,
            )
            count = len(results_q.get("ids", [[]])[0])
            return f"found {count} result(s)"

        results.append(self._run("Knowledge", "Ingest chunk", ingest_chunk))
        results.append(self._run("Knowledge", "Search chunk", search_chunk))
        return results

    # ------------------------------------------------------------------
    # Category: Provider
    # ------------------------------------------------------------------

    def _run_provider_tests(self, db: Session) -> List[SmokeTestResult]:
        results = []

        def mock_generate():
            import asyncio
            from app.services.llm.providers.mock import MockLLMProvider
            from app.services.llm.contracts import LLMRequest
            provider = MockLLMProvider()
            request = LLMRequest(
                system_prompt="You are Taksh.",
                user_prompt="Smoke test ping",
            )
            response = asyncio.get_event_loop().run_until_complete(
                provider.generate_response(request)
            )
            if not response.content:
                raise RuntimeError("Empty content from mock LLM")
            return f"status={response.status} tokens={response.completion_tokens}"

        def mock_stt():
            import asyncio
            from app.services.providers.mock_stt import MockSTTProvider
            provider = MockSTTProvider()
            asyncio.get_event_loop().run_until_complete(provider.connect())
            frame = bytes(320)  # 160 samples × 2 bytes silence
            transcript = asyncio.get_event_loop().run_until_complete(
                provider.transcribe_audio(frame)
            )
            asyncio.get_event_loop().run_until_complete(provider.disconnect())
            return f"transcript='{transcript}'"

        def mock_tts():
            import asyncio
            from app.services.providers.mock_tts import MockTTSProvider
            provider = MockTTSProvider()
            asyncio.get_event_loop().run_until_complete(provider.connect())
            audio = asyncio.get_event_loop().run_until_complete(
                provider.synthesize("Hello from smoke test")
            )
            asyncio.get_event_loop().run_until_complete(provider.disconnect())
            if audio is None:
                raise RuntimeError("Mock TTS returned None")
            return f"audio bytes={len(audio)}"

        results.append(self._run("Provider", "Mock generate", mock_generate))
        results.append(self._run("Provider", "Mock STT", mock_stt))
        results.append(self._run("Provider", "Mock TTS", mock_tts))
        return results


    # ------------------------------------------------------------------
    # Category: Conversation
    # ------------------------------------------------------------------

    def _run_conversation_tests(self, db: Session) -> List[SmokeTestResult]:
        results = []
        conv_state: dict = {}

        def start_conversation():
            from app.models.database_models import ConversationRuntimeSession
            sid = f"smoke-conv-{uuid.uuid4().hex[:8]}"
            s = ConversationRuntimeSession(
                runtime_session_id         = sid,
                conversation_state         = "listening",
                conversation_session_state = "active",
                current_turn_owner         = "none",
            )
            db.add(s)
            db.flush()
            conv_state["session_id"] = sid
            return f"started session_id={sid}"

        def send_message():
            sid = conv_state.get("session_id")
            if not sid:
                raise RuntimeError("No conversation to send message to")
            from app.models.database_models import ConversationTurn
            turn = ConversationTurn(
                runtime_session_id = sid,
                user_text          = "Smoke test message",
                assistant_text     = "Acknowledged",
                provider_name      = "mock",
                latency_ms         = 0,
            )
            db.add(turn)
            db.flush()
            return f"turn created in session={sid}"

        def stop_conversation():
            sid = conv_state.get("session_id")
            if not sid:
                raise RuntimeError("No conversation to stop")
            from app.models.database_models import ConversationRuntimeSession
            from datetime import datetime
            s = db.query(ConversationRuntimeSession).filter(
                ConversationRuntimeSession.runtime_session_id == sid
            ).first()
            if not s:
                raise RuntimeError("Conversation session not found")
            s.conversation_session_state = "closed"
            s.ended_at = datetime.utcnow()
            db.flush()
            return f"stopped session_id={sid}"

        results.append(self._run("Conversation", "Start", start_conversation))
        results.append(self._run("Conversation", "Message", send_message))
        results.append(self._run("Conversation", "Stop", stop_conversation))
        return results


# Module-level singleton
smoke_test_runner = SmokeTestRunner()
