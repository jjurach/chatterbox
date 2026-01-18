"""Audio processing utilities for Wyoming protocol."""

import logging
from pathlib import Path
from typing import Iterator, Tuple

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None


logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio file loading, conversion, and chunking for Wyoming protocol."""

    # Wyoming protocol requirements
    SAMPLE_RATE = 16000  # 16kHz
    BIT_DEPTH = 16       # 16-bit
    CHANNELS = 1         # Mono
    CHUNK_SIZE = 1024    # Bytes per chunk

    def __init__(self):
        """Initialize audio processor."""
        if not PYDUB_AVAILABLE:
            raise ImportError("pydub is required for audio processing. Install with: pip install pydub")

    def load_and_convert(self, file_path: Path) -> AudioSegment:
        """Load audio file and convert to Wyoming format.

        Args:
            file_path: Path to input audio file

        Returns:
            Converted AudioSegment in Wyoming format

        Raises:
            ValueError: If audio format conversion fails
            FileNotFoundError: If input file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Load audio file
            audio = AudioSegment.from_file(str(file_path))

            logger.info(f"Loaded audio: {audio.frame_rate}Hz, {audio.sample_width*8}bit, {audio.channels}ch")

            # Convert to Wyoming format
            converted = audio.set_frame_rate(self.SAMPLE_RATE)
            converted = converted.set_sample_width(self.BIT_DEPTH // 8)
            converted = converted.set_channels(self.CHANNELS)

            logger.info(f"Converted to: {converted.frame_rate}Hz, {converted.sample_width*8}bit, {converted.channels}ch")

            return converted

        except Exception as e:
            raise ValueError(f"Failed to load/convert audio file {file_path}: {e}")

    def get_pcm_chunks(self, audio: AudioSegment) -> Iterator[bytes]:
        """Convert AudioSegment to PCM chunks for transmission.

        Args:
            audio: AudioSegment in Wyoming format

        Yields:
            Raw PCM audio chunks
        """
        # Get raw PCM data
        pcm_data = audio.raw_data

        # Split into chunks
        for i in range(0, len(pcm_data), self.CHUNK_SIZE):
            chunk = pcm_data[i:i + self.CHUNK_SIZE]
            yield chunk

        logger.debug(f"Audio split into {len(pcm_data) // self.CHUNK_SIZE + 1} chunks")

    def save_wav(self, audio: AudioSegment, output_path: Path) -> None:
        """Save AudioSegment as WAV file.

        Args:
            audio: AudioSegment to save
            output_path: Output file path
        """
        try:
            audio.export(str(output_path), format="wav")
            logger.info(f"Saved audio to: {output_path}")
        except Exception as e:
            raise IOError(f"Failed to save audio to {output_path}: {e}")

    def reconstruct_from_chunks(self, chunks: list) -> AudioSegment:
        """Reconstruct AudioSegment from PCM chunks.

        Args:
            chunks: List of raw PCM audio chunks

        Returns:
            Reconstructed AudioSegment
        """
        # Combine all chunks
        pcm_data = b"".join(chunks)

        # Create AudioSegment from raw PCM
        audio = AudioSegment(
            data=pcm_data,
            sample_width=self.BIT_DEPTH // 8,
            frame_rate=self.SAMPLE_RATE,
            channels=self.CHANNELS
        )

        logger.debug(f"Reconstructed audio: {len(pcm_data)} bytes")
        return audio

    @staticmethod
    def validate_wyoming_format(audio: AudioSegment) -> bool:
        """Validate that audio meets Wyoming protocol requirements.

        Args:
            audio: AudioSegment to validate

        Returns:
            True if format is valid
        """
        return (
            audio.frame_rate == AudioProcessor.SAMPLE_RATE and
            audio.sample_width == AudioProcessor.BIT_DEPTH // 8 and
            audio.channels == AudioProcessor.CHANNELS
        )