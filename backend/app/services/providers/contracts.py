from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel


class ProviderState(str, Enum):
    """Supported lifecycle states for AI providers."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    FAILED = "failed"


class ProviderMetadata(BaseModel):
    """Static capability discovery metadata for providers."""
    provider_name: str
    provider_type: str
    version: str
    supports_streaming: bool
    supports_interruptions: bool
    supports_audio_input: bool
    supports_audio_output: bool
    supports_text_input: bool
    supports_text_output: bool


class SpeechToTextProvider(ABC):
    """Abstract interface defining the contract for speech recognition engines."""

    @abstractmethod
    def get_metadata(self) -> ProviderMetadata:
        """Returns capability metadata for the provider."""
        pass

    @abstractmethod
    def get_state(self) -> ProviderState:
        """Returns the current connection lifecycle state of the provider."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establishes a connection to the STT service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes the connection to the STT service."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the connection to the STT service is active."""
        pass

    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribes raw audio bytes and returns the text transcript."""
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface defining the contract for voice synthesis engines."""

    @abstractmethod
    def get_metadata(self) -> ProviderMetadata:
        """Returns capability metadata for the provider."""
        pass

    @abstractmethod
    def get_state(self) -> ProviderState:
        """Returns the current connection lifecycle state of the provider."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establishes a connection to the TTS service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes the connection to the TTS service."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the connection to the TTS service is active."""
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesizes text input into raw audio output bytes."""
        pass


class RealtimeConversationProvider(ABC):
    """Abstract interface defining the contract for realtime bidirectional AI sessions."""

    @abstractmethod
    def get_metadata(self) -> ProviderMetadata:
        """Returns capability metadata for the provider."""
        pass

    @abstractmethod
    def get_state(self) -> ProviderState:
        """Returns the current connection lifecycle state of the provider."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establishes the raw connection to the realtime server endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes the raw connection to the realtime server endpoint."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the raw realtime connection is live."""
        pass

    @abstractmethod
    async def start_session(self) -> None:
        """Starts the conversation session lifecycle."""
        pass

    @abstractmethod
    async def end_session(self) -> None:
        """Closes the conversation session lifecycle."""
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes) -> None:
        """Sends an audio frame to the realtime session."""
        pass

    @abstractmethod
    async def receive_audio(self) -> bytes:
        """Receives next pending audio frame from the session."""
        pass

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Sends a text message to the realtime session."""
        pass

    @abstractmethod
    async def receive_text(self) -> str:
        """Receives next pending text response from the session."""
        pass
