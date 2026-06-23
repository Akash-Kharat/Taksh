"""
Taksh In-Memory Metrics Layer — MS-19

Thread-safe singleton tracking operational counters.
On startup, hydrates from the most recent MetricsSnapshot DB row.
MaintenanceScheduler persists a snapshot every 15 minutes.
"""
import threading
from typing import Optional


class TakshMetrics:
    """
    Singleton in-memory metrics store.
    All public methods are thread-safe via an internal lock.
    """

    _instance: Optional["TakshMetrics"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "TakshMetrics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._data_lock = threading.Lock()
                    inst._reset()
                    cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Reset all counters to zero (also used for test isolation)."""
        self.conversation_count: int = 0
        self.turn_count: int = 0
        self.provider_requests: int = 0
        self.provider_failures: int = 0
        self.tool_executions: int = 0
        self.memory_recalls: int = 0
        self.knowledge_searches: int = 0
        self.active_sessions: int = 0
        self._latency_total_ms: float = 0.0
        self._latency_count: int = 0

    # ------------------------------------------------------------------
    # Increment helpers
    # ------------------------------------------------------------------

    def inc_conversation(self) -> None:
        with self._data_lock:
            self.conversation_count += 1

    def inc_turn(self) -> None:
        with self._data_lock:
            self.turn_count += 1

    def inc_provider_request(self) -> None:
        with self._data_lock:
            self.provider_requests += 1

    def inc_provider_failure(self) -> None:
        with self._data_lock:
            self.provider_failures += 1

    def inc_tool_execution(self) -> None:
        with self._data_lock:
            self.tool_executions += 1

    def inc_memory_recall(self) -> None:
        with self._data_lock:
            self.memory_recalls += 1

    def inc_knowledge_search(self) -> None:
        with self._data_lock:
            self.knowledge_searches += 1

    def inc_active_session(self) -> None:
        with self._data_lock:
            self.active_sessions += 1

    def dec_active_session(self) -> None:
        with self._data_lock:
            self.active_sessions = max(0, self.active_sessions - 1)

    def record_latency(self, ms: float) -> None:
        """Record a latency sample and update the rolling average."""
        with self._data_lock:
            self._latency_total_ms += ms
            self._latency_count += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    @property
    def average_latency_ms(self) -> float:
        with self._data_lock:
            if self._latency_count == 0:
                return 0.0
            return round(self._latency_total_ms / self._latency_count, 2)

    def snapshot(self) -> dict:
        """Return current state as a serialisable dict (for persistence)."""
        with self._data_lock:
            return {
                "conversation_count": self.conversation_count,
                "turn_count": self.turn_count,
                "provider_requests": self.provider_requests,
                "provider_failures": self.provider_failures,
                "tool_executions": self.tool_executions,
                "memory_recalls": self.memory_recalls,
                "knowledge_searches": self.knowledge_searches,
                "average_latency_ms": round(
                    self._latency_total_ms / self._latency_count
                    if self._latency_count else 0.0,
                    2,
                ),
            }

    def hydrate(self, data: dict) -> None:
        """
        Load state from a persisted snapshot dict.
        Called once at startup from the most recent MetricsSnapshot row.
        """
        with self._data_lock:
            self.conversation_count   = data.get("conversation_count", 0)
            self.turn_count           = data.get("turn_count", 0)
            self.provider_requests    = data.get("provider_requests", 0)
            self.provider_failures    = data.get("provider_failures", 0)
            self.tool_executions      = data.get("tool_executions", 0)
            self.memory_recalls       = data.get("memory_recalls", 0)
            self.knowledge_searches   = data.get("knowledge_searches", 0)
            avg                       = data.get("average_latency_ms", 0.0)
            # Reconstruct totals from the persisted average using count=1
            # (precision is sufficient; exact history is not needed)
            if avg > 0:
                self._latency_total_ms = avg
                self._latency_count    = 1


# Module-level singleton
metrics = TakshMetrics()
