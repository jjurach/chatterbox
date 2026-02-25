"""Speech-to-Text service using mellona STT providers."""

import logging
import tempfile
import wave
from pathlib import Path
from typing import Optional

from mellona import get_manager, STTRequest

logger = logging.getLogger(__name__)


class WhisperSTTService:
    """Speech-to-Text service using mellona's STT providers.

    This service wraps mellona's STT providers (primarily FasterWhisper)
    to maintain backward compatibility with the existing chatterbox interface.
    Mellona handles the underlying Whisper model management and caching.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        language: Optional[str] = None,
        compute_type: str = "int8",
        cache_dir: Optional[str] = None,
    ):
        """Initialize STT service using mellona.

        Args:
            model_size: Model size (tiny, base, small, medium, large). Defaults to "base".
            device: Device to run on (cpu, cuda). Defaults to "cpu".
            language: Language code (e.g., 'en'). None = auto-detect. Defaults to None.
            compute_type: Compute type (unused, kept for backward compatibility).
            cache_dir: Directory to cache models (unused, mellona manages this).
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        # Backward compatibility: store these but mellona manages them
        self.compute_type = compute_type
        self.cache_dir = cache_dir

        # Get STT provider from mellona
        manager = get_manager()
        self.stt_provider = manager.get_stt_provider("faster_whisper")

        if self.stt_provider is None:
            logger.warning(
                "FasterWhisper STT provider not available. "
                "Ensure faster-whisper is installed and mellona is configured."
            )
        else:
            logger.info(
                f"Initialized mellona STT service with faster_whisper "
                f"(model: {model_size}, device: {device})"
            )

    async def transcribe(
        self, audio_data: bytes, sample_rate: int = 16000
    ) -> dict:
        """Transcribe audio data.

        Args:
            audio_data: Raw PCM audio bytes (S16_LE format).
            sample_rate: Sample rate in Hz. Defaults to 16000.

        Returns:
            Dictionary with transcription results:
                - text: Transcribed text
                - language: Detected language code
                - confidence: Average confidence score (always 0.0 from mellona)
        """
        if self.stt_provider is None:
            raise RuntimeError(
                "STT provider not available. Ensure faster-whisper is installed."
            )

        # Convert PCM bytes to WAV file (mellona expects a file path)
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, mode="wb"
        ) as tmp_file:
            tmp_path = tmp_file.name
            try:
                # Write WAV header and PCM data
                with wave.open(tmp_path, "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data)

                # Call mellona STT provider
                request = STTRequest(
                    audio_file_path=tmp_path,
                    language=self.language,
                )
                response = await self.stt_provider.transcribe(request)

                logger.debug(
                    f"Transcribed: {response.text[:100]} "
                    f"(lang: {response.language})"
                )

                # Return in the same format as the old service
                return {
                    "text": response.text,
                    "language": response.language or "unknown",
                    "confidence": 0.0,  # Mellona doesn't provide confidence
                }

            finally:
                # Clean up temp file
                try:
                    Path(tmp_path).unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")

    async def transcribe_file(self, file_path: str) -> dict:
        """Transcribe audio from file.

        Args:
            file_path: Path to audio file.

        Returns:
            Transcription results dictionary.
        """
        if self.stt_provider is None:
            raise RuntimeError(
                "STT provider not available. Ensure faster-whisper is installed."
            )

        request = STTRequest(
            audio_file_path=file_path,
            language=self.language,
        )
        response = await self.stt_provider.transcribe(request)

        logger.info(f"Transcribed file {file_path}: {response.text[:100]}")

        return {
            "text": response.text,
            "language": response.language or "unknown",
            "confidence": 0.0,
        }

    def unload_model(self) -> None:
        """Unload the model from memory (no-op with mellona)."""
        logger.info("STT service model unload requested (mellona manages lifecycle)")
