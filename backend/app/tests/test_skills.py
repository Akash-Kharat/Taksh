from app.services.skills.engine import SkillsEngine
from app.schemas.telemetry import TelemetryPayload

def test_skills_engine_trigger():
    engine = SkillsEngine()
    
    payload = TelemetryPayload(
        active_file="src/main.c",
        cursor_line=10,
        selection_empty=True,
        compiler_error="xQueueCreate failed"
    )
    
    active_skills = engine.evaluate_active_skills(payload)
    assert "Embedded Systems Architect" in active_skills
    
    overlay = engine.get_active_overlays()
    assert "Embedded Systems Architect" in overlay
