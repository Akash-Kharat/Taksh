from typing import Optional
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.schemas.websocket import ConnectedMessage
from app.services.websocket.manager import ws_manager
from app.services.websocket.message_router import message_router
from app.core.logger import ws_logger

router = APIRouter(prefix="/ws")

@router.websocket("/connect")
async def websocket_connect(websocket: WebSocket, client_id: Optional[str] = Query(None)):
    if not client_id:
        client_id = str(uuid.uuid4())
        
    await ws_manager.connect(websocket, client_id)
    
    # Send Connection Handshake Event
    handshake = ConnectedMessage(client_id=client_id).model_dump()
    await websocket.send_json(handshake)
    
    try:
        while True:
            # Await incoming text frame
            raw_data = await websocket.receive_text()
            
            # Delegate validation and routing logic
            response = await message_router.route_message(raw_data)
            if response:
                await websocket.send_json(response)
                
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as ex:
        ws_logger.error(f"Error in WebSocket lifecycle for {client_id}: {ex}")
        ws_manager.disconnect(client_id)

@router.get("/info")
def get_ws_info():
    return ws_manager.get_diagnostics()
