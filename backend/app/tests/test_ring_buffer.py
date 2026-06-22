import pytest
from sqlalchemy.orm import Session
from app.services.voice.session_manager import voice_session_manager
from app.services.voice.ring_buffer import AudioRingBuffer

def test_ring_buffer_fifo_and_overflow(db_session: Session):
    # Create active session
    client_id = "test-client-ring"
    session_id = "test-session-ring"
    voice_sess = voice_session_manager.create_session(client_id, session_id)
    assert voice_sess is not None
    voice_session_id = voice_sess["voice_session_id"]

    # Initialize ring buffer with small size of 3 for testing overflow
    buf = AudioRingBuffer(voice_session_id, max_size=3)
    assert len(buf) == 0

    # Push 3 frames
    buf.push(1, 1000, b"frame-1")
    buf.push(2, 1001, b"frame-2")
    buf.push(3, 1002, b"frame-3")
    assert len(buf) == 3

    # Verify FIFO popping order
    assert buf.pop() == (1, 1000, b"frame-1")
    assert len(buf) == 2

    # Push 2 more to trigger overflow (max_size is 3, currently has 2)
    # Pushing frame-4 (seq 4) -> size becomes 3
    is_ooo, is_missing, is_dropped = buf.push(4, 1003, b"frame-4")
    assert not is_dropped
    
    # Pushing frame-5 (seq 5) -> size exceeds 3 -> drops oldest (frame-2)
    is_ooo, is_missing, is_dropped = buf.push(5, 1004, b"frame-5")
    assert is_dropped
    assert len(buf) == 3

    # Check that frame-2 was dropped and popping yields frame-3 next
    assert buf.pop() == (3, 1002, b"frame-3")
    assert buf.pop() == (4, 1003, b"frame-4")
    assert buf.pop() == (5, 1004, b"frame-5")
    assert buf.pop() is None

    # Cleanup
    voice_session_manager.close_session(voice_session_id)


def test_ring_buffer_sequence_anomalies(db_session: Session):
    client_id = "test-client-seq"
    session_id = "test-session-seq"
    voice_sess = voice_session_manager.create_session(client_id, session_id)
    voice_session_id = voice_sess["voice_session_id"]

    buf = AudioRingBuffer(voice_session_id, max_size=10)

    # 1. Normal push (seq=1)
    is_ooo, is_missing, is_dropped = buf.push(1, 1000, b"f1")
    assert not is_ooo
    assert not is_missing

    # 2. Gap / missing frame (expected 2, got 4)
    is_ooo, is_missing, is_dropped = buf.push(4, 1003, b"f4")
    assert not is_ooo
    assert is_missing
    # In-memory stats check
    assert voice_session_manager.active_sessions[voice_session_id]["missing_frames"] == 2

    # 3. Out-of-order frame (expected 5, got 3)
    is_ooo, is_missing, is_dropped = buf.push(3, 1002, b"f3")
    assert is_ooo
    assert not is_missing
    # Out of order frame should not be buffered
    assert len(buf) == 2  # contains f1 and f4
    assert voice_session_manager.active_sessions[voice_session_id]["out_of_order_frames"] == 1

    # Cleanup
    voice_session_manager.close_session(voice_session_id)
