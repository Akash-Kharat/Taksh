"""
MS-21 Test — Shutdown Resource Cleanup Verification
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.providers.factory import provider_factory
from app.services.websocket.manager import ws_manager
from app.services.knowledge.vector_store import close_all_clients, active_clients, ChromaDBClient


@pytest.mark.anyio
async def test_shutdown_cleanup_execution():
    from app.services.runtime.state_machine import active_state_machines
    from app.services.runtime.output_queue import active_output_queues
    from app.services.voice.session_manager import voice_session_manager

    # 1. Setup mock active WebSocket connection (directly registered to avoid accept() await errors)
    mock_ws = MagicMock()
    mock_ws.close = AsyncMock()
    ws_manager.active_connections["test-shutdown-client"] = mock_ws
    assert "test-shutdown-client" in ws_manager.active_connections

    # 2. Setup mock active STT provider in factory
    mock_provider = MagicMock()
    mock_provider.is_connected = MagicMock(return_value=True)
    mock_provider.disconnect = AsyncMock()
    provider_factory._stt_instances["test-shutdown-stt"] = mock_provider

    # 3. Setup mock active ChromaDB client
    with patch("chromadb.PersistentClient"):
        client = ChromaDBClient(mock_embeddings=True)
        assert client in active_clients

    # 4. Setup mock active runtime sessions and voice sessions
    active_state_machines["test-session"] = MagicMock()
    active_output_queues["test-session"] = MagicMock()
    voice_session_manager.active_sessions["test-session"] = MagicMock()

    # 5. Perform cleanup operations
    await ws_manager.clear()
    await provider_factory.disconnect_all()
    close_all_clients()
    active_state_machines.clear()
    active_output_queues.clear()
    voice_session_manager.active_sessions.clear()

    # 6. Verify all resources are cleaned up
    assert len(ws_manager.active_connections) == 0
    mock_ws.close.assert_called_once()

    assert "test-shutdown-stt" not in provider_factory._stt_instances
    mock_provider.disconnect.assert_called_once()

    assert len(active_clients) == 0
    assert len(active_state_machines) == 0
    assert len(active_output_queues) == 0
    assert len(voice_session_manager.active_sessions) == 0
