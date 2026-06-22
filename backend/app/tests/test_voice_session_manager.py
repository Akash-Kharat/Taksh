import pytest
from sqlalchemy.orm import Session
from app.services.voice.session_manager import voice_session_manager
from app.models.database_models import VoiceSession
from app.core.config import settings

def test_voice_session_lifecycle_and_persistence(db_session: Session):
    # 1. Clean start
    voice_session_manager.active_sessions.clear()

    # 2. Create new session
    client_id = "ws-client-uuid-1"
    session_id = "conversation-sess-1"
    
    sess_data = voice_session_manager.create_session(client_id, session_id)
    assert sess_data is not None
    voice_session_id = sess_data["voice_session_id"]
    assert sess_data["reconnect_count"] == 0
    assert sess_data["state"] == "connected"
    assert voice_session_manager.get_active_session_count() == 1

    # 3. Simulate frame interactions
    voice_session_manager.record_frame_received(voice_session_id, size=1000, latency_ms=10.0)
    voice_session_manager.record_frame_received(voice_session_id, size=1500, latency_ms=20.0)
    voice_session_manager.record_frame_sent(voice_session_id, size=2000)

    cached_sess = voice_session_manager.active_sessions[voice_session_id]
    assert cached_sess["frames_received"] == 2
    assert cached_sess["bytes_received"] == 2500
    assert cached_sess["frames_sent"] == 1
    assert cached_sess["bytes_sent"] == 2000
    assert cached_sess["average_latency_ms"] == 15.0

    # 4. Close/Finalize session
    voice_session_manager.close_session(voice_session_id, disconnect_reason="client_disconnect")
    assert voice_session_manager.get_active_session_count() == 0

    # Verify DB persistence
    db_record = db_session.query(VoiceSession).filter(VoiceSession.voice_session_id == voice_session_id).first()
    assert db_record is not None
    assert db_record.state == "disconnected"
    assert db_record.frames_received == 2
    assert db_record.bytes_received == 2500
    assert db_record.frames_sent == 1
    assert db_record.bytes_sent == 2000
    assert db_record.average_latency_ms == 15.0
    assert db_record.disconnect_reason == "client_disconnect"
    assert db_record.ended_at is not None


def test_voice_session_reconnection(db_session: Session):
    voice_session_manager.active_sessions.clear()
    
    # 1. Establish initial session
    client_id_1 = "ws-client-original"
    session_id = "persistent-conv-id"
    sess_data = voice_session_manager.create_session(client_id_1, session_id)
    voice_session_id = sess_data["voice_session_id"]
    original_transport_id = sess_data["transport_instance_id"]
    
    # Simulate a frame received
    voice_session_manager.record_frame_received(voice_session_id, size=500, latency_ms=12.0)
    
    # Simulate client disconnect and session finalization
    voice_session_manager.close_session(voice_session_id, disconnect_reason="transport_close")
    
    # Verify in DB
    db_record_1 = db_session.query(VoiceSession).filter(VoiceSession.voice_session_id == voice_session_id).first()
    assert db_record_1.reconnect_count == 0
    assert db_record_1.state == "disconnected"

    # 2. Reconnect client using same session_id
    client_id_2 = "ws-client-new-conn"
    reconnect_data = voice_session_manager.create_session(client_id_2, session_id)
    
    assert reconnect_data is not None
    assert reconnect_data["voice_session_id"] == voice_session_id  # Continuity!
    assert reconnect_data["reconnect_count"] == 1
    assert reconnect_data["websocket_client_id"] == client_id_2
    assert reconnect_data["transport_instance_id"] != original_transport_id  # Rotated transport UUID
    assert reconnect_data["state"] == "connected"
    
    # Cleanup
    voice_session_manager.close_session(voice_session_id)


def test_max_voice_sessions_limit(db_session: Session):
    voice_session_manager.active_sessions.clear()
    
    # Create 10 sessions
    for i in range(10):
        res = voice_session_manager.create_session(f"client-{i}", f"sess-{i}")
        assert res is not None

    # The 11th creation attempt must fail (MAX_VOICE_SESSIONS = 10)
    res_fail = voice_session_manager.create_session("client-overflow", "sess-overflow")
    assert res_fail is None

    # Clean up
    for active_id in list(voice_session_manager.active_sessions.keys()):
        voice_session_manager.close_session(active_id)
