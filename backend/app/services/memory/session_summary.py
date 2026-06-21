from datetime import datetime
from typing import List

class SessionSummaryBuilder:
    """Handles deterministic aggregation of session events for closure summary records."""

    def build_summary(self, cached_events: List[dict]) -> str:
        event_count = len(cached_events)
        modalities = [e["primary_modality"] for e in cached_events]
        modalities_summary = ", ".join(set(modalities)) if modalities else "none"
        
        timestamp = datetime.utcnow().isoformat()
        return (
            f"Session closed at {timestamp} UTC. Total events: {event_count}. "
            f"Modalities recorded: {modalities_summary}."
        )

session_summary_builder = SessionSummaryBuilder()
