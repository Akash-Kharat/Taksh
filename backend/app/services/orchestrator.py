from typing import Optional
from fastapi import WebSocket
from app.core.logger import system_logger
from app.services.memory.manager import MemoryManager
from app.services.skills.engine import SkillsEngine
from app.services.knowledge.search import HybridSearchEngine
from app.services.voice_session import VoiceSessionManager
from app.services.memory.identity import CoreIdentityManager
from app.schemas.telemetry import ClientTelemetryMessage, ClientInterruptMessage

class Orchestrator:
    """Orchestrator for Taksh.
    
    Acts as the single point of coordination and event routing between
    the frontend client WebSocket, Memory, Skills, Knowledge Search,
    and the external Gemini Live session. Does not contain internal domain logic.
    """
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        
        self.memory_manager = MemoryManager()
        self.skills_engine = SkillsEngine()
        self.search_engine = HybridSearchEngine()
        self.voice_session = VoiceSessionManager(orchestrator=self)
        self.identity_manager = CoreIdentityManager()
        
        system_logger.info("Orchestrator instantiated with decoupled service managers.")

    async def handle_client_audio(self, raw_pcm: bytes) -> None:
        """Routes raw PCM audio frame from client to the Gemini Live session."""
        system_logger.debug(f"Routing client audio chunk of size {len(raw_pcm)} to voice session")
        await self.voice_session.send_audio_chunk(raw_pcm)

    async def handle_client_telemetry(self, telemetry: ClientTelemetryMessage) -> None:
        """Stores workspace state in memory and requests active prompt overlays from the Skills Engine."""
        system_logger.info(f"Routing telemetry update for {telemetry.payload.active_file}")
        self.memory_manager.update_sensory_memory(telemetry.payload)
        active_skills = self.skills_engine.evaluate_active_skills(telemetry.payload)
        system_logger.info(f"Evaluated active skills: {active_skills}")

    async def handle_client_interruption(self, interrupt: ClientInterruptMessage) -> None:
        """Handles user interruption by sending cancel triggers to the Gemini Live API."""
        system_logger.warning("Routing user interruption request")
        await self.voice_session.trigger_interruption()
        self.memory_manager.record_interruption()

    async def assemble_context(self, user_query: str) -> str:
        """Assembles context containing Core Identity, RAG search results, and active skills overlay."""
        system_logger.info("Assembling context for model prompt")
        core_identity = self.identity_manager.get_identity()
        search_results = self.search_engine.search(user_query)
        memory_context = self.memory_manager.get_active_context()
        skills_overlay = self.skills_engine.get_active_overlays()

        composite_context = (
            f"=== CORE IDENTITY ===\n{core_identity}\n\n"
            f"=== USER CONTEXT & HISTORY ===\n{memory_context}\n\n"
            f"=== RELEVANT ARCHITECTURAL KNOWLEDGE ===\n{search_results}\n\n"
            f"=== SKILLS DIRECTIONS ===\n{skills_overlay}\n"
        )
        return composite_context

    async def handle_gemini_output(self, response_text: str, audio_bytes: Optional[bytes] = None) -> None:
        """Forwards transcript segments and audio feedback from Gemini to the client WebSocket."""
        system_logger.debug("Routing Gemini output to client")

    async def cleanup(self) -> None:
        """Performs cleanup of session objects on disconnect."""
        system_logger.info("Cleaning up Orchestrator session")
        await self.voice_session.close()
        self.memory_manager.close_session()
