"""Text-to-Speech service using mellona TTS providers."""

import logging
import wave
from pathlib import Path
from typing import Optional

from mellona import get_manager, TTSRequest

logger = logging.getLogger(__name__)


class PiperTTSService:
    """Text-to-Speech service using mellona's TTS providers.

    This service wraps mellona's TTS providers (primarily Piper)
    to maintain backward compatibility with the existing chatterbox interface.
    Mellona handles the underlying Piper model management and caching.
    """

    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        model_path: str = None,
        config_path: str = None,
        sample_rate: int = 22050,
        cache_dir: Optional[str] = None,
    ):
        """Initialize TTS service using mellona.

        Args:
            voice: Name of the Piper voice. Defaults to "en_US-lessac-medium".
            model_path: Unused, kept for backward compatibility.
            config_path: Unused, kept for backward compatibility.
            sample_rate: Sample rate in Hz. Defaults to 22050.
            cache_dir: Directory to cache models (unused, mellona manages this).
        """
        self.voice_name = voice
        self.sample_rate = sample_rate
        # Backward compatibility: store these but mellona manages them
        self.model_path = model_path
        self.config_path = config_path
        self.cache_dir = cache_dir

        # Get TTS provider from mellona
        manager = get_manager()
        self.tts_provider = manager.get_tts_provider("piper")

        if self.tts_provider is None:
            logger.warning(
                "Piper TTS provider not available. "
                "Ensure piper is installed and mellona is configured."
            )
        else:
            logger.info(
                f"Initialized mellona TTS service with piper "
                f"(voice: {voice}, sample_rate: {sample_rate})"
            )

    async def load_voice(self) -> None:
        """Load the voice model asynchronously (no-op with mellona).

        Mellona manages voice loading automatically.
        """
        logger.info("TTS voice load requested (mellona manages lifecycle)")

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize.

        Returns:
            Raw PCM audio bytes (S16_LE format at sample_rate).
        """
        if self.tts_provider is None:
            raise RuntimeError(
                "TTS provider not available. Ensure piper is installed."
            )

        request = TTSRequest(
            text=text,
            voice=self.voice_name,
        )
        response = await self.tts_provider.synthesize(request)

        logger.debug(
            f"Synthesized: {text[:50]!r} → {len(response.audio_data)} bytes"
        )
        return response.audio_data

    async def synthesize_to_file(self, text: str, file_path: str) -> None:
        """Synthesize text to speech and save to file.

        Args:
            text: Text to synthesize.
            file_path: Path to save audio file.
        """
        audio_bytes = await self.synthesize(text)

        # Write to WAV file
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # S16_LE format
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_bytes)

        logger.info(f"Synthesized to file: {file_path}")

    def unload_voice(self) -> None:
        """Unload the voice model from memory (no-op with mellona)."""
        logger.info("TTS voice unload requested (mellona manages lifecycle)")
