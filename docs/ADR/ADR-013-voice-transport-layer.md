Decision:
Use binary websocket frames for audio transport.

Rationale:
Lower latency.
No base64 inflation.
Future Gemini Live compatibility.

Consequences:
Requires binary frame parser.
Requires transport diagnostics.
Requires heartbeat support.