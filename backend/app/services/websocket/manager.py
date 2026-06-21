import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("websocket")

class ConnectionManager:
    """Manages real-time WebSocket connections and broadcasts."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance

    def __init__(self):
        # Initialized in __new__
        pass

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections.values()):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

    def get_active_clients(self) -> List[str]:
        return list(self.active_connections.keys())

    def get_diagnostics(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "connected_client_ids": self.get_active_clients()
        }

ws_manager = ConnectionManager()
