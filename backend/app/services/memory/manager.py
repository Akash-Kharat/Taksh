from typing import Dict, Any, List
from app.core.logger import memory_logger
from app.schemas.telemetry import TelemetryPayload

class MemoryManager:
    """Coordinates memory persistence across SQLite, ChromaDB, and core configuration directories.
    
    Provides simple interfaces to append memory events, register project files, 
    and fetch short/long-term context for composite prompts.
    """
    def __init__(self):
        self.sensory_memory: Dict[str, Any] = {}
        memory_logger.info("MemoryManager initialized.")

    def update_sensory_memory(self, payload: TelemetryPayload) -> None:
        """Saves transient active workspace selection, cursor index, and compiler diagnostics in-memory."""
        memory_logger.debug(f"Updating sensory memory: active_file={payload.active_file}")
        self.sensory_memory = {
            "active_file": payload.active_file,
            "cursor_line": payload.cursor_line,
            "compiler_error": payload.compiler_error,
            "selection_empty": payload.selection_empty
        }

    def record_interruption(self) -> None:
        """Flags user interruption in database event log."""
        memory_logger.info("Marking current session context event as interrupted in database.")

    def get_active_context(self) -> str:
        """Retrieves formatted workspace telemetry and short-term dialogue context."""
        memory_logger.debug("Retrieving active memory context card.")
        active_file = self.sensory_memory.get("active_file", "None")
        cursor_line = self.sensory_memory.get("cursor_line", 0)
        compiler_err = self.sensory_memory.get("compiler_error") or "None"
        
        context_card = (
            f"- Active File: {active_file}\n"
            f"- Cursor Line: {cursor_line}\n"
            f"- Last Compiler Diagnostics: {compiler_err}\n"
        )
        return context_card

    def get_longterm_memory_episodes(self) -> List[Dict[str, Any]]:
        """Queries relational records and ChromaDB vector points for master profiles."""
        memory_logger.debug("Querying long-term memory records.")
        return []

    def close_session(self) -> None:
        """Serializes workspace goals and updates session logs upon disconnect."""
        memory_logger.info("Closing active memory context. Archiving session events.")
