from app.services.runtime.state_machine import RealtimeStateMachine

def test_runtime_state_machine_is_provider_free():
    """Verifies the guardrail that the runtime state machine does not possess provider methods."""
    assert not hasattr(RealtimeStateMachine, "transcribe")
    assert not hasattr(RealtimeStateMachine, "synthesize")
    assert not hasattr(RealtimeStateMachine, "get_realtime_provider")
