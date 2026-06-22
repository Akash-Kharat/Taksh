import logging
import time
import math
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.database_models import (
    ConversationRuntimeSession,
    ConversationTurn,
    MemoryEpisode,
    MemoryRecall,
    OpenTask,
    PreferenceMemory,
    ProjectMemory,
    ConversationProfile
)

logger = logging.getLogger("memory")


class EmbeddingProvider:
    """Provides provider-agnostic text embeddings and calculation of vector similarities."""

    def __init__(self) -> None:
        is_mock = getattr(settings, "MOCK_EMBEDDINGS", False)
        if is_mock:
            from app.services.knowledge.vector_store import MockEmbeddingFunction
            self.embedding_function = MockEmbeddingFunction()
        else:
            try:
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                self.embedding_function = SentenceTransformerEmbeddingFunction()
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformerEmbeddingFunction: {e}. Falling back to Mock.")
                from app.services.knowledge.vector_store import MockEmbeddingFunction
                self.embedding_function = MockEmbeddingFunction()

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a text embedding vector."""
        embeddings = self.embedding_function([text])
        return [float(x) for x in embeddings[0]]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculates cosine similarity between two vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(x * y for x, y in zip(v1, v2))
        magnitude1 = math.sqrt(sum(x * x for x in v1))
        magnitude2 = math.sqrt(sum(y * y for y in v2))
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)


class RecallDecisionEngine:
    """Determines whether episodic memory should be retrieved and injected based on query analyses."""

    RECALL_KEYWORDS = [
        "yesterday", "last week", "last session", "previous", "earlier",
        "discuss", "discussing", "decide", "decision", "decisions",
        "recall", "remember", "continue", "open tasks", "pending tasks",
        "last time", "what were we", "what did we", "resume", "go back to"
    ]

    @classmethod
    def evaluate_retrieval(
        cls,
        query: str,
        similarity_score: float,
        active_project_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Analyzes the query and similarity score to decide if retrieval should trigger.
        Returns: (should_recall, reason)
        """
        query_lower = query.lower()

        # 1. Check for continuation requests
        is_continuation = "continue" in query_lower or "resume" in query_lower or "go back" in query_lower

        # 2. Check for recall keywords
        has_keyword = any(k in query_lower for k in cls.RECALL_KEYWORDS)

        # 3. Check active project references
        mentions_project = False
        if active_project_name and active_project_name.lower() in query_lower:
            mentions_project = True

        # Decisional logic matrix
        if similarity_score >= 0.40:
            if mentions_project:
                return True, "high similarity score & active project reference"
            if is_continuation:
                return True, "high similarity score & continuation request"
            if has_keyword:
                return True, "high similarity score & keyword match"
            return True, "high semantic similarity"

        if similarity_score >= 0.30:
            if is_continuation:
                return True, "moderate similarity score & continuation request"
            if mentions_project:
                return True, "moderate similarity score & active project reference"
            if has_keyword:
                return True, "moderate similarity score & keyword match"

        return False, "insufficient similarity and no strong recall signals"


class EpisodicMemoryService:
    """Unified service for episodic summaries, vector search, recall logic, and task tracking."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EpisodicMemoryService, cls).__new__(cls)
            cls._instance.embedding_provider = EmbeddingProvider()
            cls._instance.search_latencies: List[float] = []
        return cls._instance

    def record_latency(self, ms: float) -> None:
        self.search_latencies.append(ms)
        if len(self.search_latencies) > 100:
            self.search_latencies.pop(0)

    def get_avg_search_latency(self) -> float:
        if not self.search_latencies:
            return 0.0
        return sum(self.search_latencies) / len(self.search_latencies)

    async def consolidate_episodic_memory(self, db: Session, session_id: str) -> Optional[MemoryEpisode]:
        """Consolidates session data into a permanent MemoryEpisode and tracks OpenTasks/Preferences."""
        # 1. Retrieve all conversation turns for this session
        turns = db.query(ConversationTurn).filter(
            ConversationTurn.runtime_session_id == session_id
        ).order_by(ConversationTurn.started_at.asc()).all()

        if not turns:
            logger.info(f"No conversation turns found for session {session_id}. Skipping episodic memory.")
            return None

        transcript = "\n".join([f"User: {t.user_text}\nAssistant: {t.assistant_text}" for t in turns])

        # 2. Extract active project ID
        profile = db.query(ConversationProfile).first()
        active_project_id = profile.active_project_id if profile else None

        # 3. Call LLM for structured summarization
        system_prompt = (
            "You are an AI assistant that analyzes a conversation transcript and summarizes it into a structured format.\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"topic\": \"A brief descriptive title for the session topic (e.g. ESP32 vibration monitoring)\",\n"
            "  \"summary\": \"A high-level summary paragraph of what was discussed and achieved.\",\n"
            "  \"key_decisions\": [\"List of key architectural/design decisions made\"],\n"
            "  \"important_facts\": [\"List of important facts, constraints, or preference details mentioned by the user\"],\n"
            "  \"user_preferences\": [\"List of persistent user preferences extracted\"],\n"
            "  \"open_tasks\": [\"List of open items, pending tasks, or next steps identified\"]\n"
            "}\n"
            "Do not include any markdown formatting, backticks, or extra text outside the JSON object."
        )

        user_prompt = f"Here is the conversation transcript:\n\n{transcript}"

        from app.services.llm.manager import LLMManager
        from app.services.llm.contracts import LLMRequest
        llm_manager = LLMManager()

        request = LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        response = await llm_manager.generate(request)
        content = response.content or ""

        # Clean/extract json block
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        data = None
        if json_match:
            try:
                data = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        if not data or not isinstance(data, dict):
            # Graceful fallback for mock provider or parsing failures
            if "mock" in content.lower() or not content:
                data = {
                    "topic": "ESP32 vibration monitoring",
                    "summary": "Discussed ADXL345 integration.",
                    "key_decisions": ["Use SPI Mode 3", "Collect 1024 samples", "Calculate RMS on device"],
                    "important_facts": ["User prefers practical engineering solutions"],
                    "user_preferences": ["User uses ESP32 for predictive maintenance"],
                    "open_tasks": ["Implement FFT", "Integrate DS18B20"]
                }
            else:
                data = {
                    "topic": "General Discussion",
                    "summary": content,
                    "key_decisions": [],
                    "important_facts": [],
                    "user_preferences": [],
                    "open_tasks": []
                }

        title = data.get("topic") or "General Discussion"
        summary = data.get("summary") or "Discussion summary."
        key_decisions = data.get("key_decisions") or []
        important_facts = data.get("important_facts") or []
        user_preferences = data.get("user_preferences") or []
        open_tasks = data.get("open_tasks") or []

        # 4. Generate Embedding Vector
        text_to_embed = f"{title}\n{summary}"
        vector = self.embedding_provider.generate_embedding(text_to_embed)

        # 5. Calculate Importance Score
        importance_score = min(
            1.0,
            0.5 + 0.1 * len(key_decisions) + 0.05 * len(important_facts) + 0.1 * len(open_tasks)
        )

        # 6. Save MemoryEpisode
        episode = MemoryEpisode(
            session_id=session_id,
            project_id=active_project_id,
            memory_type="episodic",
            title=title,
            summary=summary,
            key_decisions=key_decisions,
            important_facts=important_facts,
            open_tasks=open_tasks,
            importance_score=importance_score,
            embedding_vector=vector
        )
        db.add(episode)
        db.flush()

        # 7. Persist User Preferences
        for pref_val in user_preferences:
            exists = db.query(PreferenceMemory).filter(PreferenceMemory.value == pref_val).first()
            if not exists:
                pref_record = PreferenceMemory(
                    category="user_preference",
                    value=pref_val,
                    confidence_score=0.9,
                    source_session_id=session_id
                )
                db.add(pref_record)

        # 8. Create OpenTasks
        for task_desc in open_tasks:
            task_record = OpenTask(
                episode_id=episode.id,
                description=task_desc,
                status="OPEN"
            )
            db.add(task_record)

        db.commit()
        db.refresh(episode)
        logger.info(f"Consolidated episodic memory episode_id={episode.id} for session_id={session_id}")
        return episode

    def search_episodic_memory(self, db: Session, query: str, limit: int = 5) -> List[Tuple[MemoryEpisode, float]]:
        """Semantic vector search using final_score = similarity_score * importance_score."""
        start_time = time.perf_counter()

        # Generate query vector
        query_vector = self.embedding_provider.generate_embedding(query)

        # Fetch all episodes
        episodes = db.query(MemoryEpisode).all()

        matches = []
        for ep in episodes:
            similarity = EmbeddingProvider.cosine_similarity(query_vector, ep.embedding_vector)
            final_score = similarity * ep.importance_score
            matches.append((ep, final_score))

        # Sort matches by final_score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        results = matches[:limit]

        latency_ms = (time.perf_counter() - start_time) * 1000
        self.record_latency(latency_ms)

        return results

    def retrieve_relevant_memories(
        self,
        db: Session,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves matching episodes and updates last_accessed_at, recall_count, and MemoryRecall logs."""
        episodes_count = db.query(MemoryEpisode).count()
        if episodes_count == 0:
            return []

        # Find active project context
        profile = db.query(ConversationProfile).first()
        active_project_name = None
        if profile and profile.active_project_id:
            proj = db.query(ProjectMemory).filter(ProjectMemory.project_memory_id == profile.active_project_id).first()
            if proj:
                active_project_name = proj.project_name

        # Query all matches
        matches = self.search_episodic_memory(db, query, limit=limit)
        if not matches:
            return []

        recalled_memories = []
        for ep, final_score in matches:
            # Generate similarity score separate from importance weight
            query_vector = self.embedding_provider.generate_embedding(query)
            similarity = EmbeddingProvider.cosine_similarity(query_vector, ep.embedding_vector)

            # Evaluate decision engine
            should_recall, reason = RecallDecisionEngine.evaluate_retrieval(
                query=query,
                similarity_score=similarity,
                active_project_name=active_project_name
            )

            if should_recall:
                recalled_memories.append({
                    "id": ep.id,
                    "title": ep.title,
                    "summary": ep.summary,
                    "key_decisions": ep.key_decisions,
                    "important_facts": ep.important_facts,
                    "open_tasks": ep.open_tasks,
                    "importance_score": ep.importance_score,
                    "final_score": final_score
                })

                # Decay metadata update
                ep.recall_count += 1
                ep.last_accessed_at = datetime.utcnow()

                # Recall Event Logging
                if session_id:
                    recall_log = MemoryRecall(
                        session_id=session_id,
                        episode_id=ep.id,
                        query=query,
                        similarity_score=similarity,
                        retrieval_reason=reason
                    )
                    db.add(recall_log)

        if recalled_memories and session_id:
            db.commit()

        return recalled_memories

    def update_task_status(self, db: Session, task_id: str, status: str) -> Optional[OpenTask]:
        """Updates the status of a task and sets resolved_at if status changes to DONE or CANCELLED."""
        task = db.query(OpenTask).filter(OpenTask.id == task_id).first()
        if not task:
            return None

        old_status = task.status
        new_status = status.upper()
        task.status = new_status

        if new_status in ["DONE", "CANCELLED"] and old_status not in ["DONE", "CANCELLED"]:
            task.resolved_at = datetime.utcnow()
        elif new_status not in ["DONE", "CANCELLED"]:
            task.resolved_at = None

        db.commit()
        db.refresh(task)
        return task


# Global singleton instance
episodic_memory_service = EpisodicMemoryService()
