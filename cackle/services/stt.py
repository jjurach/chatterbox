"""Speech-to-Text service using OpenAI Whisper."""

import asyncio
import io
import logging
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperSTTService:
    """Speech-to-Text service using faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        language: Optional[str] = None,
        compute_type: str = "int8",
    ):
        """Initialize Whisper STT service.

        Args:
            model_size: Model size (tiny, base, small, medium, large). Defaults to "base".
            device: Device to run on (cpu, cuda). Defaults to "cpu".
            language: Language code (e.g., 'en'). None = auto-detect. Defaults to None.
            compute_type: Compute type (int8, int16, float32, float16). Defaults to "int8".
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        self._loaded = False

    async def load_model(self) -> None:
        """Load the Whisper model asynchronously."""
        if self._loaded:
            return

        def _load():
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load)
        self._loaded = True
        logger.info(
            f"Loaded Whisper model: {self.model_size} on {self.device}"
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
                - confidence: Average confidence score
        """
        if not self._loaded:
            await self.load_model()

        if self.model is None:
            raise RuntimeError("Model failed to load")

        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        audio_array /= 32768.0  # Normalize to [-1, 1]

        # Run transcription in executor
        def _transcribe():
            segments, info = self.model.transcribe(
                audio_array,
                language=self.language,
                beam_size=5,
                best_of=5,
            )
            text = "".join(segment.text for segment in segments)
            # Calculate average confidence
            confidences = [segment.confidence for segment in segments]
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )
            return {
                "text": text,
                "language": info.language,
                "confidence": avg_confidence,
            }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _transcribe)
        logger.debug(
            f"Transcribed: {result['text'][:100]} "
            f"(lang: {result['language']}, conf: {result['confidence']:.2f})"
        )
        return result

    async def transcribe_file(self, file_path: str) -> dict:
        """Transcribe audio from file.

        Args:
            file_path: Path to audio file.

        Returns:
            Transcription results dictionary.
        """
        if not self._loaded:
            await self.load_model()

        def _transcribe():
            segments, info = self.model.transcribe(
                file_path,
                language=self.language,
                beam_size=5,
                best_of=5,
            )
            text = "".join(segment.text for segment in segments)
            confidences = [segment.confidence for segment in segments]
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )
            return {
                "text": text,
                "language": info.language,
                "confidence": avg_confidence,
            }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _transcribe)
        logger.info(f"Transcribed file {file_path}: {result['text'][:100]}")
        return result

    def unload_model(self) -> None:
        """Unload the model from memory."""
        if self._loaded:
            del self.model
            self.model = None
            self._loaded = False
            logger.info("Unloaded Whisper model")
