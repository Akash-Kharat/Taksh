from app.services.memory.manager import MemoryManager
from app.schemas.telemetry import TelemetryPayload

def test_sensory_memory_update():
    mgr = MemoryManager()
    payload = TelemetryPayload(
        active_file="src/main.c",
        cursor_line=42,
        selection_empty=True,
        compiler_error="conflicting types for 'init'"
    )
    mgr.update_sensory_memory(payload)
    context = mgr.get_active_context()
    
    assert "src/main.c" in context
    assert "42" in context
    assert "conflicting types for 'init'" in context
