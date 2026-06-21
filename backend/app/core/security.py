from fastapi import Request, HTTPException, status
from app.core.config import settings

def enforce_local_loopback(request: Request):
    """Enforces local loopback binding.
    
    Rejects any request that does not originate from localhost (127.0.0.1 or ::1).
    """
    client_host = request.client.host if request.client else None
    
    if client_host not in ("127.0.0.1", "localhost", "::1", "testclient"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Connections are constrained to local interface loopback bindings."
        )
