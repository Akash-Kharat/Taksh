from enum import Enum

class ProviderEvent(str, Enum):
    """Event types published during provider session life cycles."""
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_RECONNECTED = "provider_reconnected"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RESPONSE_RECEIVED = "provider_response_received"
    PROVIDER_INTERRUPTED = "provider_interrupted"
