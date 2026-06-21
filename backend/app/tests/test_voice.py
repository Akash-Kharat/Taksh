import pytest
from fastapi.testclient import TestClient

def test_websocket_stream_connection(client):
    with client.websocket_connect("/api/v1/voice/stream") as websocket:
        websocket.send_text('{"type": "telemetry", "timestamp": "2026-06-21T11:42:00Z", "payload": {"active_file": "src/main.c", "cursor_line": 10, "selection_empty": true}}')
        websocket.send_bytes(b"\x00" * 100)
        websocket.send_text('{"type": "interrupt", "timestamp": "2026-06-21T11:42:02Z"}')
