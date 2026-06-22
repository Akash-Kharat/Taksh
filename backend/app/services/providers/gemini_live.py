import logging
import json
import asyncio
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.providers.contracts import RealtimeConversationProvider, ProviderMetadata, ProviderState
from app.services.providers.registry import provider_registry
from app.services.providers.audio_validator import AudioValidator

logger = logging.getLogger("providers")


class GeminiLiveProvider(RealtimeConversationProvider):
    """Google Gemini Live realtime conversation provider client adapter."""

    def __init__(self):
        self._state = ProviderState.DISCONNECTED
        self.provider_state = "closed"
        self.websocket = None
        self.phase = "A"
        
        # Telemetry metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.audio_frames_sent = 0
        self.audio_frames_received = 0
        self.interruptions = 0
        self.db_session_id = None

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="gemini_live",
            provider_type="realtime",
            version="1.0.0",
            supports_streaming=True,
            supports_interruptions=True,
            supports_audio_input=True,
            supports_audio_output=True,
            supports_text_input=True,
            supports_text_output=True
        )

    def get_state(self) -> ProviderState:
        return self._state

    def _get_db(self, db: Optional[Session]) -> Session:
        if db is not None:
            return db
        from app.core.database import SessionLocal
        return SessionLocal()

    def _create_session_record(self, runtime_session_id: Optional[str], voice_session_id: Optional[str], db: Session) -> None:
        from app.models.database_models import ProviderSession
        session_rec = ProviderSession(
            provider_name="gemini_live",
            provider_state=self.provider_state,
            runtime_session_id=runtime_session_id,
            voice_session_id=voice_session_id,
            connected_at=datetime.utcnow(),
            messages_sent=0,
            messages_received=0,
            audio_frames_sent=0,
            audio_frames_received=0,
            interruptions=0
        )
        db.add(session_rec)
        db.commit()
        db.refresh(session_rec)
        self.db_session_id = session_rec.provider_session_id

    def _update_session_state(self, state: str, db: Session, reason: str = None) -> None:
        if not self.db_session_id:
            return
        from app.models.database_models import ProviderSession
        session_rec = db.query(ProviderSession).filter(
            ProviderSession.provider_session_id == self.db_session_id
        ).first()
        if session_rec:
            session_rec.provider_state = state
            if state in ["closed", "failed"]:
                session_rec.disconnected_at = datetime.utcnow()
                if reason:
                    session_rec.disconnect_reason = reason
            db.commit()

    def _persist_message(self, role: str, content: str, latency_ms: float = 0.0, db: Optional[Session] = None) -> None:
        if not self.db_session_id:
            return
        db_conn = db if db is not None else self._get_db(None)
        try:
            # Response budget controls: Truncate response if limits exceeded
            if len(content) > settings.MAX_PROVIDER_RESPONSE_CHARS:
                logger.warning(f"Gemini Live response exceeded character budget limit ({settings.MAX_PROVIDER_RESPONSE_CHARS} chars). Truncating.")
                content = content[:settings.MAX_PROVIDER_RESPONSE_CHARS] + "... [truncated]"

            from app.models.database_models import ProviderConversationMessage, ProviderSession
            msg = ProviderConversationMessage(
                provider_session_id=self.db_session_id,
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                latency_ms=latency_ms
            )
            db_conn.add(msg)
            
            session_rec = db_conn.query(ProviderSession).filter(
                ProviderSession.provider_session_id == self.db_session_id
            ).first()
            if session_rec:
                if role == "user":
                    session_rec.messages_sent += 1
                else:
                    session_rec.messages_received += 1
            
            if db is None:
                db_conn.commit()
            else:
                db_conn.flush()
        except Exception as e:
            logger.error(f"Failed to persist provider conversation message: {e}")
            if db is None:
                db_conn.rollback()
        finally:
            if db is None:
                db_conn.close()

    def _update_metrics(self, latency_ms: float, db: Optional[Session] = None) -> None:
        if not self.db_session_id:
            return
        db_conn = db if db is not None else self._get_db(None)
        try:
            from app.models.database_models import ProviderSession
            session_rec = db_conn.query(ProviderSession).filter(
                ProviderSession.provider_session_id == self.db_session_id
            ).first()
            if session_rec:
                # Update response latency
                if session_rec.average_response_latency_ms is None:
                    session_rec.average_response_latency_ms = latency_ms
                else:
                    session_rec.average_response_latency_ms = (session_rec.average_response_latency_ms + latency_ms) / 2
                
                if session_rec.max_response_latency_ms is None or latency_ms > session_rec.max_response_latency_ms:
                    session_rec.max_response_latency_ms = latency_ms
                
                if db is None:
                    db_conn.commit()
                else:
                    db_conn.flush()
        except Exception as e:
            logger.error(f"Failed to update provider metrics: {e}")
            if db is None:
                db_conn.rollback()
        finally:
            if db is None:
                db_conn.close()

    async def connect(self, runtime_session_id: Optional[str] = None, voice_session_id: Optional[str] = None, db: Optional[Session] = None) -> None:
        self._state = ProviderState.CONNECTING
        self.provider_state = "connecting"
        
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            self._state = ProviderState.FAILED
            self.provider_state = "failed"
            logger.error("Gemini API key is missing.")
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Create session record in database
        db_conn = self._get_db(db)
        try:
            self._create_session_record(runtime_session_id, voice_session_id, db_conn)
        finally:
            if db is None:
                db_conn.close()

        # Connect WebSocket
        url = f"{settings.GEMINI_LIVE_API_URL}?key={settings.GEMINI_API_KEY}"
        
        attempts = 0
        max_attempts = settings.MAX_PROVIDER_RECONNECT_ATTEMPTS
        delay = settings.PROVIDER_RECONNECT_DELAY_SECONDS

        while attempts < max_attempts:
            try:
                import websockets
                self.websocket = await websockets.connect(url, open_timeout=settings.GEMINI_LIVE_TIMEOUT_SECONDS)
                
                # Send setup configuration
                setup_frame = {
                    "setup": {
                        "model": f"models/{settings.GEMINI_LIVE_MODEL}",
                        "generationConfig": {
                            "responseModalities": ["text"] if self.phase in ["A", "B"] else ["audio"]
                        }
                    }
                }
                await self.websocket.send(json.dumps(setup_frame))
                
                self._state = ProviderState.CONNECTED
                self.provider_state = "active"
                
                db_conn = self._get_db(db)
                try:
                    self._update_session_state("active", db_conn)
                finally:
                    if db is None:
                        db_conn.close()
                return
            except Exception as e:
                attempts += 1
                logger.warning(f"Connection attempt {attempts} failed: {e}")
                
                from app.services.providers.manager import provider_manager
                provider_manager.record_reconnect()
                provider_manager.record_failure(e)

                if attempts < max_attempts:
                    self.provider_state = "reconnecting"
                    db_conn = self._get_db(db)
                    try:
                        self._update_session_state("reconnecting", db_conn)
                    finally:
                        if db is None:
                            db_conn.close()
                    await asyncio.sleep(delay)
                else:
                    self._state = ProviderState.FAILED
                    self.provider_state = "failed"
                    db_conn = self._get_db(db)
                    try:
                        self._update_session_state("failed", db_conn, reason=str(e))
                    finally:
                        if db is None:
                            db_conn.close()
                    raise ConnectionError(f"Failed to connect to Gemini Live after {attempts} attempts.") from e

    async def disconnect(self) -> None:
        if self.websocket:
            await self.websocket.close()
        self._state = ProviderState.DISCONNECTED
        self.provider_state = "closed"
        
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            self._update_session_state("closed", db)
        finally:
            db.close()

    def is_connected(self) -> bool:
        return self._state == ProviderState.CONNECTED

    async def start_session(self) -> None:
        if not self.is_connected():
            raise RuntimeError("Gemini Live connection is not active.")
        self.messages_sent = 0
        self.messages_received = 0
        self.audio_frames_sent = 0
        self.audio_frames_received = 0
        self.interruptions = 0
        logger.info("Started Gemini Live session.")

    async def end_session(self) -> None:
        logger.info("Ending Gemini Live session.")
        await self.disconnect()

    async def send_audio(self, audio_data: bytes, db: Optional[Session] = None) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
            
        # Audio validator codec guard check
        AudioValidator.validate_frame(audio_data)

        import base64
        encoded = base64.b64encode(audio_data).decode("utf-8")
        media_chunk = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": "audio/pcm;rate=16000",
                        "data": encoded
                    }
                ]
            }
        }
        await self.websocket.send(json.dumps(media_chunk))
        self.audio_frames_sent += 1

        # Track audio frame sent counts in DB
        db_conn = db if db is not None else self._get_db(None)
        try:
            from app.models.database_models import ProviderSession
            session_rec = db_conn.query(ProviderSession).filter(
                ProviderSession.provider_session_id == self.db_session_id
            ).first()
            if session_rec:
                session_rec.audio_frames_sent += 1
                if db is None:
                    db_conn.commit()
                else:
                    db_conn.flush()
        finally:
            if db is None:
                db_conn.close()

    async def receive_audio(self, db: Optional[Session] = None) -> bytes:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
            
        raw_frame = await self.websocket.recv()
        frame = json.loads(raw_frame)
        
        server_content = frame.get("serverContent", {})
        model_turn = server_content.get("modelTurn", {})
        parts = model_turn.get("parts", [])
        
        for part in parts:
            inline_data = part.get("inlineData", {})
            if inline_data and "data" in inline_data:
                import base64
                audio_bytes = base64.b64decode(inline_data["data"])
                self.audio_frames_received += 1
                
                # Track in DB
                db_conn = db if db is not None else self._get_db(None)
                try:
                    from app.models.database_models import ProviderSession
                    session_rec = db_conn.query(ProviderSession).filter(
                        ProviderSession.provider_session_id == self.db_session_id
                    ).first()
                    if session_rec:
                        session_rec.audio_frames_received += 1
                        if db is None:
                            db_conn.commit()
                        else:
                            db_conn.flush()
                finally:
                    if db is None:
                        db_conn.close()
                return audio_bytes
                
        return b""

    async def send_text(self, text: str, db: Optional[Session] = None) -> None:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        
        self._last_send_time = time.perf_counter()

        client_content = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": text
                            }
                        ]
                    }
                ],
                "turnComplete": True
            }
        }
        await self.websocket.send(json.dumps(client_content))
        self.messages_sent += 1
        
        self._persist_message("user", text, db=db)

    async def receive_text(self, db: Optional[Session] = None) -> str:
        if not self.is_connected():
            raise RuntimeError("Realtime session is not active.")
        
        raw_frame = await self.websocket.recv()
        frame = json.loads(raw_frame)
        
        server_content = frame.get("serverContent", {})
        model_turn = server_content.get("modelTurn", {})
        parts = model_turn.get("parts", [])
        
        text_content = ""
        segment_count = 0
        for part in parts:
            if "text" in part:
                segment_count += 1
                if segment_count > settings.MAX_PROVIDER_RESPONSE_SEGMENTS:
                    logger.warning(f"Gemini Live response exceeded segments budget limit ({settings.MAX_PROVIDER_RESPONSE_SEGMENTS}). Truncating segments.")
                    break
                text_content += part["text"]

        latency_ms = 0.0
        if hasattr(self, "_last_send_time") and self._last_send_time is not None:
            latency_ms = (time.perf_counter() - self._last_send_time) * 1000
            self._last_send_time = None
            
        self._update_metrics(latency_ms, db=db)

        if text_content:
            self._persist_message("assistant", text_content, latency_ms, db=db)
            self.messages_received += 1
            
        return text_content

    async def interrupt(self, db: Optional[Session] = None) -> None:
        """Handles session interruption by resetting buffers."""
        self.interruptions += 1
        logger.info("Interrupted Gemini Live session.")
        
        if self.db_session_id:
            db_conn = db if db is not None else self._get_db(None)
            try:
                from app.models.database_models import ProviderSession
                session_rec = db_conn.query(ProviderSession).filter(
                    ProviderSession.provider_session_id == self.db_session_id
                ).first()
                if session_rec:
                    session_rec.interruptions += 1
                    if db is None:
                        db_conn.commit()
                    else:
                        db_conn.flush()
            except Exception as e:
                logger.error(f"Failed to update provider interruptions in DB: {e}")
                if db is None:
                    db_conn.rollback()
            finally:
                if db is None:
                    db_conn.close()


# Register Gemini Live provider
provider_registry.register_realtime_provider("gemini_live", GeminiLiveProvider)
