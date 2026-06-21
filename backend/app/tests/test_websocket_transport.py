import pytest
import json
from fastapi.testclient import TestClient
from app.services.websocket.manager import ws_manager

def test_websocket_connection_lifecycle_and_handshake(client: TestClient):
    # Ensure diagnostics starts clean
    info_res = client.get("/api/v1/ws/info")
    assert info_res.status_code == 200
    assert info_res.json()["active_connections"] == 0

    # 1. Establish connection
    with client.websocket_connect("/api/v1/ws/connect?client_id=client-test-1") as websocket:
        # Await Connection Handshake Frame
        data = websocket.receive_json()
        assert data["type"] == "connected"
        assert data["client_id"] == "client-test-1"

        # Check diagnostics while connected
        info_res = client.get("/api/v1/ws/info")
        assert info_res.status_code == 200
        assert info_res.json()["active_connections"] == 1
        assert "client-test-1" in info_res.json()["connected_client_ids"]

    # 2. Check diagnostics after disconnecting
    info_res = client.get("/api/v1/ws/info")
    assert info_res.status_code == 200
    assert info_res.json()["active_connections"] == 0
    assert "client-test-1" not in info_res.json()["connected_client_ids"]

def test_websocket_ping_pong(client: TestClient):
    with client.websocket_connect("/api/v1/ws/connect") as websocket:
        # Clear handshake
        websocket.receive_json()

        # Send Ping
        websocket.send_json({"type": "ping", "timestamp": 98765.43})
        
        # Expect Pong
        response = websocket.receive_json()
        assert response["type"] == "pong"
        assert response["timestamp"] == 98765.43

def test_websocket_echo_message(client: TestClient):
    with client.websocket_connect("/api/v1/ws/connect") as websocket:
        # Clear handshake
        websocket.receive_json()

        # Send Message
        websocket.send_json({"type": "message", "payload": "Socratic testing"})
        
        # Expect Echo
        response = websocket.receive_json()
        assert response["type"] == "message"
        assert response["payload"] == "Echo: Socratic testing"

def test_websocket_invalid_payloads(client: TestClient):
    with client.websocket_connect("/api/v1/ws/connect") as websocket:
        # Clear handshake
        websocket.receive_json()

        # 1. Send invalid JSON text
        websocket.send_text("{invalid-json}")
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "INVALID_FRAME"

        # 2. Send JSON missing 'type'
        websocket.send_json({"foo": "bar"})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "INVALID_FRAME"

        # 3. Send JSON with unknown type
        websocket.send_json({"type": "unknown_type"})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "INVALID_FRAME"

@pytest.mark.anyio
async def test_websocket_multiple_clients_and_broadcast(client: TestClient):
    # Reset ws_manager state to be absolutely sure
    ws_manager.active_connections.clear()

    # Establish Client A
    with client.websocket_connect("/api/v1/ws/connect?client_id=client-a") as ws_a:
        assert ws_a.receive_json()["type"] == "connected"

        # Establish Client B
        with client.websocket_connect("/api/v1/ws/connect?client_id=client-b") as ws_b:
            assert ws_b.receive_json()["type"] == "connected"

            # Check diagnostics counts
            info_res = client.get("/api/v1/ws/info")
            assert info_res.json()["active_connections"] == 2

            # 1. Test Broadcast
            await ws_manager.broadcast({"type": "message", "payload": "System Broadcast"})
            
            # Both should receive
            data_a = ws_a.receive_json()
            data_b = ws_b.receive_json()
            assert data_a["type"] == "message" and data_a["payload"] == "System Broadcast"
            assert data_b["type"] == "message" and data_b["payload"] == "System Broadcast"

            # 2. Test Personal Message
            await ws_manager.send_personal_message({"type": "message", "payload": "Direct to A"}, "client-a")
            
            # Client A receives, Client B should not get anything
            data_direct = ws_a.receive_json()
            assert data_direct["type"] == "message" and data_direct["payload"] == "Direct to A"
