import logging
from app.core.config import settings

logger = logging.getLogger("providers")

class AudioValidationError(ValueError):
    """Raised when an audio frame fails codec validation."""
    pass

class AudioValidator:
    """Validator layer protecting providers from malformed audio frames."""

    @staticmethod
    def validate_frame(
        audio_bytes: bytes,
        sample_rate: int = None,
        channels: int = None,
        encoding: str = "pcm16"
    ) -> None:
        """
        Validates raw audio frame properties before sending to the AI provider.
        Raises AudioValidationError if any property is invalid.
        """
        if sample_rate is None:
            sample_rate = settings.VOICE_SAMPLE_RATE
        if channels is None:
            channels = settings.VOICE_CHANNELS

        # 1. Validate payload size
        if len(audio_bytes) > settings.MAX_AUDIO_FRAME_BYTES:
            raise AudioValidationError(
                f"Audio payload size ({len(audio_bytes)} bytes) exceeds maximum "
                f"allowed limit ({settings.MAX_AUDIO_FRAME_BYTES} bytes)."
            )

        if len(audio_bytes) == 0:
            raise AudioValidationError("Audio payload is empty.")

        # 2. Validate encoding and channels byte alignment
        if encoding.lower() in ["pcm16", "pcm_s16le"]:
            bytes_per_sample = 2
            expected_alignment = bytes_per_sample * channels
            if len(audio_bytes) % expected_alignment != 0:
                raise AudioValidationError(
                    f"Audio payload length ({len(audio_bytes)} bytes) is not aligned "
                    f"with format {encoding} and channels count {channels}."
                )
        else:
            raise AudioValidationError(f"Unsupported audio encoding: {encoding}")

        # 3. Validate sample rate
        supported_rates = [16000, 24000, 48000]
        if sample_rate not in supported_rates:
            raise AudioValidationError(f"Unsupported sample rate: {sample_rate}. Supported: {supported_rates}")
