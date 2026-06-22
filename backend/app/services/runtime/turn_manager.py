import logging
from typing import Dict

logger = logging.getLogger("runtime")

class TurnManager:
    """Manages conversational turn ownership transitions and invariants."""
    
    # State to Owner mapping
    STATE_OWNERS: Dict[str, str] = {
        "idle": "none",
        "listening": "user",
        "thinking": "none",
        "speaking": "assistant",
        "interrupted": "user",
        "closed": "none"
    }

    @classmethod
    def get_owner_for_state(cls, state: str) -> str:
        """Resolves turn owner for a given conversation state."""
        owner = cls_owner = cls.STATE_OWNERS.get(state, "none")
        logger.debug(f"Resolved owner '{owner}' for state '{state}'")
        return owner

    @classmethod
    def validate_owner_transition(cls, from_owner: str, to_owner: str) -> bool:
        """
        Validates transition between turn owners.
        Transitions should typically move: user -> none -> assistant -> user (or assistant -> user directly on interrupt).
        """
        # Transitions to same owner are always valid
        if from_owner == to_owner:
            return True
        
        # Valid transition paths
        valid_transitions = {
            "none": ["user", "assistant"],
            "user": ["none", "assistant"],  # User can yield turn to thinking/assistant
            "assistant": ["user", "none"]   # Assistant can yield to user (interrupted/finished) or thinking
        }

        is_valid = to_owner in valid_transitions.get(from_owner, [])
        if not is_valid:
            logger.warning(f"Unusual turn transition detected: from '{from_owner}' to '{to_owner}'")
        return is_valid
