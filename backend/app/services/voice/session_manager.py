import uuid
from datetime import datetime
from typing import Dict, Optional, List
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.database_models import VoiceSession
from app.core.config import settings

logger = logging.getLogger("voice")

class AudioSessionManager:
    """Manages voice transport sessions and attributes."""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AudioSessionManager, cls).__new__(cls)
            cls._instance.active_sessions = {}
        return cls._instance

    def __init__(self):
        # Initialized in __new__
        pass

    def get_active_session_count(self) -> int:
        return len(self.active_sessions)

    def create_session(self, websocket_client_id: str, session_id: Optional[str] = None) -> Optional[dict]:
        """
        Creates or updates a voice session.
        If session_id is provided and matching session exists, reuse it (increment reconnect count).
        Otherwise create new.
        Enforces MAX_VOICE_SESSIONS.
        """
        if len(self.active_sessions) >= settings.MAX_VOICE_SESSIONS:
            logger.warning("Max voice sessions limit reached")
            return None

        db: Session = SessionLocal()
        try:
            voice_sess = None
            if session_id:
                # Look up recent session for continuity
                voice_sess = db.query(VoiceSession).filter(
                    VoiceSession.session_id == session_id
                ).order_by(VoiceSession.started_at.desc()).first()

            transport_inst_id = str(uuid.uuid4())

            if voice_sess:
                # Reconnect
                voice_sess.reconnect_count += 1
                voice_sess.websocket_client_id = websocket_client_id
                voice_sess.transport_instance_id = transport_inst_id
                voice_sess.state = "connected"
                db.commit()
                db.refresh(voice_sess)
                logger.info(f"Reconnected voice session {voice_sess.voice_session_id} for session_id {session_id}")
            else:
                # Create new
                voice_sess = VoiceSession(
                    voice_session_id=str(uuid.uuid4()),
                    session_id=session_id,
                    websocket_client_id=websocket_client_id,
                    transport_instance_id=transport_inst_id,
                    reconnect_count=0,
                    state="connected",
                    started_at=datetime.utcnow()
                )
                db.add(voice_sess)
                db.commit()
                db.refresh(voice_sess)
                logger.info(f"Created new voice session {voice_sess.voice_session_id}")

            # Keep in active registry
            session_data = {
                "voice_session_id": voice_sess.voice_session_id,
                "session_id": voice_sess.session_id,
                "websocket_client_id": websocket_client_id,
                "transport_instance_id": transport_inst_id,
                "reconnect_count": voice_sess.reconnect_count,
                "state": "connected",
                "frames_received": voice_sess.frames_received,
                "frames_sent": voice_sess.frames_sent,
                "bytes_received": voice_sess.bytes_received,
                "bytes_sent": voice_sess.bytes_sent,
                "dropped_frames": voice_sess.dropped_frames,
                "missing_frames": voice_sess.missing_frames,
                "out_of_order_frames": voice_sess.out_of_order_frames,
                "average_latency_ms": voice_sess.average_latency_ms,
                "latency_sum": voice_sess.average_latency_ms * voice_sess.frames_received,
                "started_at": voice_sess.started_at,
                "last_activity": datetime.utcnow()
            }
            self.active_sessions[voice_sess.voice_session_id] = session_data
            return session_data
        except Exception as e:
            logger.error(f"Error creating voice session: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def update_activity(self, voice_session_id: str):
        if voice_session_id in self.active_sessions:
            self.active_sessions[voice_session_id]["last_activity"] = datetime.utcnow()

    def record_frame_received(self, voice_session_id: str, size: int, latency_ms: float = 0.0):
        if voice_session_id in self.active_sessions:
            sess = self.active_sessions[voice_session_id]
            sess["frames_received"] += 1
            sess["bytes_received"] += size
            sess["latency_sum"] += latency_ms
            sess["average_latency_ms"] = sess["latency_sum"] / sess["frames_received"]
            sess["last_activity"] = datetime.utcnow()

    def record_frame_sent(self, voice_session_id: str, size: int):
        if voice_session_id in self.active_sessions:
            sess = self.active_sessions[voice_session_id]
            sess["frames_sent"] += 1
            sess["bytes_sent"] += size
            sess["last_activity"] = datetime.utcnow()

    def record_dropped_frames(self, voice_session_id: str, count: int = 1):
        if voice_session_id in self.active_sessions:
            self.active_sessions[voice_session_id]["dropped_frames"] += count

    def record_missing_frames(self, voice_session_id: str, count: int):
        if voice_session_id in self.active_sessions:
            self.active_sessions[voice_session_id]["missing_frames"] += count

    def record_out_of_order_frames(self, voice_session_id: str, count: int = 1):
        if voice_session_id in self.active_sessions:
            self.active_sessions[voice_session_id]["out_of_order_frames"] += count

    def close_session(self, voice_session_id: str, disconnect_reason: Optional[str] = None):
        """Finalizes the session and saves statistics to the database."""
        sess = self.active_sessions.pop(voice_session_id, None)
        if not sess:
            return

        db: Session = SessionLocal()
        try:
            voice_sess = db.query(VoiceSession).filter(
                VoiceSession.voice_session_id == voice_session_id
            ).first()
            if voice_sess:
                voice_sess.state = "disconnected"
                voice_sess.frames_received = sess["frames_received"]
                voice_sess.frames_sent = sess["frames_sent"]
                voice_sess.bytes_received = sess["bytes_received"]
                voice_sess.bytes_sent = sess["bytes_sent"]
                voice_sess.dropped_frames = sess["dropped_frames"]
                voice_sess.missing_frames = sess["missing_frames"]
                voice_sess.out_of_order_frames = sess["out_of_order_frames"]
                voice_sess.average_latency_ms = sess["average_latency_ms"]
                voice_sess.disconnect_reason = disconnect_reason
                voice_sess.ended_at = datetime.utcnow()
                db.commit()
                logger.info(f"Finalized voice session {voice_session_id} in DB.")
        except Exception as e:
            logger.error(f"Error finalizing voice session: {e}")
            db.rollback()
        finally:
            db.close()

    def get_aggregate_diagnostics(self) -> dict:
        """Returns consolidated diagnostics across both active and closed sessions."""
        db: Session = SessionLocal()
        try:
            # Query sum of metrics for historical sessions
            closed_stats = db.query(
                VoiceSession.frames_received,
                VoiceSession.frames_sent,
                VoiceSession.dropped_frames,
                VoiceSession.missing_frames,
                VoiceSession.out_of_order_frames,
                VoiceSession.average_latency_ms
            ).filter(VoiceSession.state == "disconnected").all()

            frames_rec = sum(s[0] or 0 for s in closed_stats)
            frames_sent = sum(s[1] or 0 for s in closed_stats)
            dropped = sum(s[2] or 0 for s in closed_stats)
            missing = sum(s[3] or 0 for s in closed_stats)
            ooo = sum(s[4] or 0 for s in closed_stats)
            
            # Weighted average latency for closed sessions
            latency_weight_sum = sum((s[5] or 0.0) * (s[0] or 0) for s in closed_stats)
            total_closed_frames = sum(s[0] or 0 for s in closed_stats)

            # Add active sessions stats
            active_count = len(self.active_sessions)
            for sess in self.active_sessions.values():
                frames_rec += sess["frames_received"]
                frames_sent += sess["frames_sent"]
                dropped += sess["dropped_frames"]
                missing += sess["missing_frames"]
                ooo += sess["out_of_order_frames"]
                latency_weight_sum += sess["latency_sum"]
                total_closed_frames += sess["frames_received"]

            avg_latency = (
                latency_weight_sum / total_closed_frames
                if total_closed_frames > 0
                else 0.0
            )

            return {
                "active_sessions": active_count,
                "frames_received": frames_rec,
                "frames_sent": frames_sent,
                "dropped_frames": dropped,
                "missing_frames": missing,
                "out_of_order_frames": ooo,
                "average_latency_ms": avg_latency
            }
        except Exception as e:
            logger.error(f"Error gathering diagnostics: {e}")
            return {
                "active_sessions": len(self.active_sessions),
                "frames_received": 0,
                "frames_sent": 0,
                "dropped_frames": 0,
                "missing_frames": 0,
                "out_of_order_frames": 0,
                "average_latency_ms": 0.0
            }
        finally:
            db.close()

voice_session_manager = AudioSessionManager()
