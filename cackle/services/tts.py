"""Text-to-Speech service using Piper TTS."""

import asyncio
import io
import logging
from typing import Optional

import numpy as np
from piper.voice import PiperVoice

logger = logging.getLogger(__name__)


class PiperTTSService:
    """Text-to-Speech service using Piper TTS."""

    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
    ):
        """Initialize Piper TTS service.

        Args:
            voice: Voice to use. Defaults to "en_US-lessac-medium".
            sample_rate: Sample rate in Hz. Defaults to 22050.
        """
        self.voice_name = voice
        self.sample_rate = sample_rate
        self.voice: Optional[PiperVoice] = None
        self._loaded = False

    async def load_voice(self) -> None:
        """Load the voice model asynchronously."""
        if self._loaded:
            return

        def _load():
            self.voice = PiperVoice.load(
                self.voice_name,
                model_path=None,  # Use default model directory
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load)
        self._loaded = True
        logger.info(f"Loaded Piper voice: {self.voice_name}")

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize.

        Returns:
            Raw PCM audio bytes (S16_LE format at sample_rate).
        """
        if not self._loaded:
            await self.load_voice()

        if self.voice is None:
            raise RuntimeError("Voice failed to load")

        def _synthesize():
            # Use BytesIO to capture audio output
            wav_file = io.BytesIO()

            # Synthesize audio
            self.voice.synthesize(
                text,
                wav_file,
                speaker_id=None,
                length_scale=1.0,
            )

            wav_file.seek(0)
            audio_bytes = wav_file.read()
            return audio_bytes

        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(None, _synthesize)
        logger.debug(f"Synthesized: {text[:50]}... ({len(audio_bytes)} bytes)")
        return audio_bytes

    async def synthesize_to_file(self, text: str, file_path: str) -> None:
        """Synthesize text to speech and save to file.

        Args:
            text: Text to synthesize.
            file_path: Path to save audio file.
        """
        if not self._loaded:
            await self.load_voice()

        def _synthesize():
            with open(file_path, "wb") as wav_file:
                self.voice.synthesize(
                    text,
                    wav_file,
                    speaker_id=None,
                    length_scale=1.0,
                )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _synthesize)
        logger.info(f"Synthesized to file: {file_path}")

    def unload_voice(self) -> None:
        """Unload the voice model from memory."""
        if self._loaded:
            del self.voice
            self.voice = None
            self._loaded = False
            logger.info("Unloaded Piper voice")
