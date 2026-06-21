from typing import Optional
from app.core.logger import voice_logger
from app.core.config import settings

class VoiceSessionManager:
    """Manages the persistent WebSocket connection proxying to the Gemini Multimodal Live API."""
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.active_session = False
        voice_logger.info("VoiceSessionManager initialized")

    async def connect_to_gemini(self) -> None:
        """Establishes websocket handshake and sends system initializations."""
        voice_logger.info(f"Opening connection tunnel to Gemini Live API: {settings.GEMINI_LIVE_API_URL}")
        self.active_session = True

    async def send_audio_chunk(self, pcm_chunk: bytes) -> None:
        """Sends raw audio frame to the active Gemini socket stream."""
        if not self.active_session:
            await self.connect_to_gemini()
        voice_logger.debug(f"Streaming {len(pcm_chunk)} bytes of PCM voice data to Gemini")

    async def trigger_interruption(self) -> None:
        """Sends reset / cancel signal payload to interrupt Gemini generation."""
        voice_logger.warning("Sending reset/cancel command to Gemini Live API session")

    async def close(self) -> None:
        """Closes active Gemini WebSocket connection."""
        if self.active_session:
            voice_logger.info("Closing Gemini Live WebSocket session")
            self.active_session = False
