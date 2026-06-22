import collections
import logging
from typing import Dict, Optional, Tuple, Any
from app.core.config import settings
from app.services.voice.session_manager import voice_session_manager

logger = logging.getLogger("voice")

class AudioRingBuffer:
    """FIFO buffer for incoming audio frames, supporting jitter absorption and quality metrics."""
    
    def __init__(self, voice_session_id: str, max_size: int = settings.VOICE_BUFFER_SIZE_FRAMES):
        self.voice_session_id = voice_session_id
        self.max_size = max_size
        self.buffer = collections.deque(maxlen=max_size)
        self.expected_sequence_number = None

    def push(self, sequence_number: int, timestamp_ms: int, payload: bytes) -> Tuple[bool, bool, bool]:
        """
        Pushes a new frame into the FIFO.
        Returns (is_ooo, is_missing, is_dropped).
        """
        is_ooo = False
        is_missing = False
        is_dropped = False

        if self.expected_sequence_number is None:
            self.expected_sequence_number = sequence_number

        if sequence_number == self.expected_sequence_number:
            self.expected_sequence_number = sequence_number + 1
        elif sequence_number > self.expected_sequence_number:
            # Missing frames detected
            gap = sequence_number - self.expected_sequence_number
            voice_session_manager.record_missing_frames(self.voice_session_id, gap)
            is_missing = True
            logger.warning(f"Detected {gap} missing frame(s) in session {self.voice_session_id}. Expected {self.expected_sequence_number}, got {sequence_number}.")
            self.expected_sequence_number = sequence_number + 1
        else:
            # Out-of-order frame
            voice_session_manager.record_out_of_order_frames(self.voice_session_id, 1)
            is_ooo = True
            logger.warning(f"Detected out-of-order frame in session {self.voice_session_id}. Expected {self.expected_sequence_number}, got {sequence_number}.")
            # Do not buffer out-of-order frame
            return is_ooo, is_missing, is_dropped

        # Check for overflow/drop
        if len(self.buffer) >= self.max_size:
            # Deque with maxlen automatically drops the oldest item when pushing beyond maxlen.
            # But we want to explicitly record the drop count.
            voice_session_manager.record_dropped_frames(self.voice_session_id, 1)
            is_dropped = True
            logger.warning(f"Audio buffer overflow in session {self.voice_session_id}. Dropping oldest frame.")

        self.buffer.append((sequence_number, timestamp_ms, payload))
        return is_ooo, is_missing, is_dropped

    def pop(self) -> Optional[Tuple[int, int, bytes]]:
        """Pops the oldest frame from the FIFO."""
        if self.buffer:
            return self.buffer.popleft()
        return None

    def clear(self):
        """Clears the buffer."""
        self.buffer.clear()
        self.expected_sequence_number = None

    def __len__(self) -> int:
        return len(self.buffer)
