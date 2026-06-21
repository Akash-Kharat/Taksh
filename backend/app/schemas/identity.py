from pydantic import BaseModel

class CoreIdentityResponse(BaseModel):
    identity: str

class CoreIdentityInfoResponse(BaseModel):
    loaded: bool
    source: str
    cache_initialized: bool
    identity_hash: str
