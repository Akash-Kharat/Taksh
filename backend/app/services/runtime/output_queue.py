import collections

class AudioOutputQueue:
    """FIFO Queue for storing mock playback items prior to voice rendering."""
    def __init__(self):
        self.queue = collections.deque()

    def enqueue(self, payload: dict) -> None:
        """Pushes a mock audio/speech placeholder payload."""
        self.queue.append(payload)

    def flush(self) -> list[dict]:
        """Pops and returns all enqueued payloads, clearing the queue."""
        items = list(self.queue)
        self.queue.clear()
        return items

    def clear(self) -> None:
        """Discards all enqueued items."""
        self.queue.clear()

    def size(self) -> int:
        """Returns the current length of the queue."""
        return len(self.queue)


# In-memory active output queues cache: runtime_session_id -> AudioOutputQueue
active_output_queues: dict[str, AudioOutputQueue] = {}

