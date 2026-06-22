from abc import ABC, abstractmethod

class SpeechToTextProvider(ABC):
    """Abstract interface defining the lifecycle and transcription contracts for Speech-to-Text engines."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establishes connection to the speech recognition service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes the connection to the speech recognition service."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if currently connected to the STT service."""
        pass

    @abstractmethod
    async def transcribe_audio_chunk(self, audio_data: bytes) -> str:
        """Sends raw audio chunk and returns transcription text."""
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface defining the lifecycle and synthesis contracts for Text-to-Speech engines."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establishes connection to the voice synthesis service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes the connection to the voice synthesis service."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if currently connected to the TTS service."""
        pass

    @abstractmethod
    async def synthesize_text(self, text: str) -> bytes:
        """Sends text input and returns audio stream bytes."""
        pass


class RealtimeConversationProvider(ABC):
    """Abstract interface defining the lifecycle and communication contracts for Realtime bidirectional providers (e.g. Gemini Live)."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establishes connection to the realtime server session."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes the connection to the realtime server session."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the realtime connection is live."""
        pass

    @abstractmethod
    async def connect_session(self) -> None:
        """Runs the main bidirectional session loop."""
        pass
