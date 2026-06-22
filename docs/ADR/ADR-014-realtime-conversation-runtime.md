Decision:
Conversation runtime implemented as a lock-guarded state machine.

States:
idle
listening
thinking
speaking
interrupted
closed

Rationale:
Deterministic runtime behavior.
Provider independence.
Support for future barge-in.
Support for Gemini Live integration.

Consequences:
Runtime events persisted.
Turn ownership enforced.
Output queue abstraction introduced.