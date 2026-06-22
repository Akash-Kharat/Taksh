import pytest
from app.services.runtime.turn_manager import TurnManager


def test_turn_manager_get_owner():
    assert TurnManager.get_owner_for_state("idle") == "none"
    assert TurnManager.get_owner_for_state("listening") == "user"
    assert TurnManager.get_owner_for_state("thinking") == "none"
    assert TurnManager.get_owner_for_state("speaking") == "assistant"
    assert TurnManager.get_owner_for_state("interrupted") == "user"
    assert TurnManager.get_owner_for_state("closed") == "none"
    assert TurnManager.get_owner_for_state("unknown_state") == "none"


def test_turn_manager_validate_owner_transition():
    # Same owner transitions are always valid
    assert TurnManager.validate_owner_transition("none", "none") is True
    assert TurnManager.validate_owner_transition("user", "user") is True
    assert TurnManager.validate_owner_transition("assistant", "assistant") is True

    # Valid transitions
    assert TurnManager.validate_owner_transition("none", "user") is True
    assert TurnManager.validate_owner_transition("none", "assistant") is True
    assert TurnManager.validate_owner_transition("user", "none") is True
    assert TurnManager.validate_owner_transition("user", "assistant") is True
    assert TurnManager.validate_owner_transition("assistant", "user") is True
    assert TurnManager.validate_owner_transition("assistant", "none") is True

    # Invalid / warning-logged transitions
    # In v0.1, the validation doesn't return False or raise exceptions (it just returns bool, let's verify if it actually returns False for invalid keys)
    # The code:
    # valid_transitions = {
    #     "none": ["user", "assistant"],
    #     "user": ["none", "assistant"],
    #     "assistant": ["user", "none"]
    # }
    # is_valid = to_owner in valid_transitions.get(from_owner, [])
    # Let's test with an invalid target owner
    assert TurnManager.validate_owner_transition("none", "invalid_owner") is False
    assert TurnManager.validate_owner_transition("invalid_owner", "user") is False
