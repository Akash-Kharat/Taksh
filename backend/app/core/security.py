from fastapi import Request, WebSocket, HTTPException, status
from app.core.config import settings

def enforce_local_loopback(request: Request = None, websocket: WebSocket = None):
    """Enforces local loopback binding.
    
    Rejects any request that does not originate from localhost (127.0.0.1 or ::1).
    Works for both HTTP Requests and WebSockets.
    """
    client_host = None
    if request is not None:
        client_host = request.client.host if request.client else None
    elif websocket is not None:
        client_host = websocket.client.host if websocket.client else None
        
    if client_host not in ("127.0.0.1", "localhost", "::1", "testclient"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Connections are constrained to local interface loopback bindings."
        )
