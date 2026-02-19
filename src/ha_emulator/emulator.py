"""HAEmulator — orchestrates Wyoming STT / TTS / full-round-trip flows."""

import asyncio
import logging
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import async_read_event, async_write_event
from wyoming.tts import Synthesize

logger = logging.getLogger(__name__)

# PCM chunk size sent per AudioChunk event (bytes)
_CHUNK_SIZE = 4096


@dataclass
class STTResult:
    """Result from a Wyoming STT flow."""

    transcript: str
    latency_ms: float  # ms from AudioStop → Transcript
    success: bool
    error: Optional[str] = None


@dataclass
class TTSResult:
    """Result from a Wyoming TTS flow."""

    audio_bytes: bytes
    audio_rate: int
    audio_width: int
    audio_channels: int
    latency_ms: float  # ms from Synthesize → AudioStop
    success: bool
    error: Optional[str] = None


@dataclass
class FullResult:
    """Result from a full STT + TTS round-trip."""

    stt: STTResult
    tts: TTSResult
    round_trip_ms: float


class HAEmulator:
    """Emulates Home Assistant interactions with a Wyoming service.

    Opens one TCP connection per operation (matching Wyoming's expected
    one-connection-per-conversation pattern).

    Usage::

        emulator = HAEmulator("localhost", 10700)
        result = asyncio.run(emulator.run_stt(Path("audio.wav")))
        print(result.transcript)
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 30.0,
        connect_timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connect_timeout = connect_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_stt(self, wav_path: Path) -> STTResult:
        """Send a WAV file via Wyoming STT flow and return the transcript.

        Protocol sequence:
          → Transcribe
          → AudioStart
          → AudioChunk × N  (raw PCM from wav_path)
          → AudioStop
          ← Transcript
        """
        wav_path = Path(wav_path)
        t0 = time.monotonic()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout,
            )
        except (asyncio.TimeoutError, OSError) as exc:
            return STTResult(
                transcript="",
                latency_ms=0.0,
                success=False,
                error=f"Connection failed: {exc}",
            )

        try:
            pcm_data, rate, width, channels = _read_wav(wav_path)

            # Send Transcribe + AudioStart
            await async_write_event(Transcribe().event(), writer)
            await async_write_event(
                AudioStart(rate=rate, width=width, channels=channels).event(), writer
            )

            # Stream PCM chunks
            for i in range(0, len(pcm_data), _CHUNK_SIZE):
                chunk = pcm_data[i : i + _CHUNK_SIZE]
                await async_write_event(
                    AudioChunk(
                        rate=rate, width=width, channels=channels, audio=chunk
                    ).event(),
                    writer,
                )

            # Signal end of audio
            await async_write_event(AudioStop().event(), writer)
            stop_time = time.monotonic()

            # Wait for Transcript
            transcript_text, error = await self._wait_for_transcript(reader)
            latency_ms = (time.monotonic() - stop_time) * 1000.0

            return STTResult(
                transcript=transcript_text or "",
                latency_ms=latency_ms,
                success=error is None,
                error=error,
            )
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run_tts(
        self, text: str, output_wav: Optional[Path] = None
    ) -> TTSResult:
        """Send text via Wyoming TTS flow and return the audio stream.

        Protocol sequence:
          → Synthesize(text)
          ← AudioStart
          ← AudioChunk × N
          ← AudioStop
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout,
            )
        except (asyncio.TimeoutError, OSError) as exc:
            return TTSResult(
                audio_bytes=b"",
                audio_rate=0,
                audio_width=0,
                audio_channels=0,
                latency_ms=0.0,
                success=False,
                error=f"Connection failed: {exc}",
            )

        try:
            await async_write_event(Synthesize(text=text).event(), writer)
            send_time = time.monotonic()

            result = await self._collect_audio(reader)
            result.latency_ms = (time.monotonic() - send_time) * 1000.0

            if output_wav and result.success:
                _save_wav(result, Path(output_wav))

            return result
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run_full(
        self, wav_path: Path, output_wav: Optional[Path] = None
    ) -> FullResult:
        """Run a complete STT + TTS round-trip.

        Sends the audio from *wav_path* to STT, then sends the resulting
        transcript to TTS, and returns both results plus total round-trip time.
        """
        t0 = time.monotonic()
        stt_result = await self.run_stt(wav_path)
        tts_result = await self.run_tts(
            stt_result.transcript, output_wav=output_wav
        )
        round_trip_ms = (time.monotonic() - t0) * 1000.0
        return FullResult(stt=stt_result, tts=tts_result, round_trip_ms=round_trip_ms)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _wait_for_transcript(
        self, reader: asyncio.StreamReader
    ) -> tuple:
        """Read events until a ``transcript`` event arrives or timeout."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                event = await asyncio.wait_for(
                    async_read_event(reader), timeout=remaining
                )
            except asyncio.TimeoutError:
                return None, "Timeout waiting for Transcript"
            except Exception as exc:
                return None, f"Read error: {exc}"

            if event is None:
                return None, "Connection closed before Transcript"

            if event.type == "transcript":
                text = (event.data or {}).get("text", "")
                logger.debug("Received Transcript: %r", text)
                return text, None

            logger.debug("Skipping event: %s", event.type)

        return None, "Timeout waiting for Transcript"

    async def _collect_audio(
        self, reader: asyncio.StreamReader
    ) -> TTSResult:
        """Collect AudioStart / AudioChunk / AudioStop from the server."""
        audio_rate = 22050
        audio_width = 2
        audio_channels = 1
        chunks: list = []
        stream_started = False
        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                event = await asyncio.wait_for(
                    async_read_event(reader), timeout=remaining
                )
            except asyncio.TimeoutError:
                return TTSResult(
                    audio_bytes=b"".join(chunks),
                    audio_rate=audio_rate,
                    audio_width=audio_width,
                    audio_channels=audio_channels,
                    latency_ms=0.0,
                    success=False,
                    error="Timeout waiting for audio stream",
                )
            except Exception as exc:
                return TTSResult(
                    audio_bytes=b"".join(chunks),
                    audio_rate=audio_rate,
                    audio_width=audio_width,
                    audio_channels=audio_channels,
                    latency_ms=0.0,
                    success=False,
                    error=f"Read error: {exc}",
                )

            if event is None:
                break

            if event.type == "audio-start":
                d = event.data or {}
                audio_rate = d.get("rate", audio_rate)
                audio_width = d.get("width", audio_width)
                audio_channels = d.get("channels", audio_channels)
                stream_started = True
                logger.debug(
                    "AudioStart: rate=%d width=%d channels=%d",
                    audio_rate,
                    audio_width,
                    audio_channels,
                )
            elif event.type == "audio-chunk":
                payload = getattr(event, "payload", None) or (event.data or {}).get(
                    "audio", b""
                )
                if payload:
                    chunks.append(payload)
                    logger.debug("AudioChunk: %d bytes", len(payload))
            elif event.type == "audio-stop":
                logger.debug("AudioStop received")
                return TTSResult(
                    audio_bytes=b"".join(chunks),
                    audio_rate=audio_rate,
                    audio_width=audio_width,
                    audio_channels=audio_channels,
                    latency_ms=0.0,
                    success=True,
                )
            else:
                logger.debug("Skipping event: %s", event.type)

        return TTSResult(
            audio_bytes=b"".join(chunks),
            audio_rate=audio_rate,
            audio_width=audio_width,
            audio_channels=audio_channels,
            latency_ms=0.0,
            success=False,
            error="Connection closed before AudioStop",
        )


# ------------------------------------------------------------------
# WAV I/O helpers (no external deps beyond stdlib)
# ------------------------------------------------------------------


def _read_wav(wav_path: Path) -> tuple:
    """Read a WAV file and return (pcm_data, rate, width, channels)."""
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        width = wf.getsampwidth()
        channels = wf.getnchannels()
        pcm_data = wf.readframes(wf.getnframes())
    return pcm_data, rate, width, channels


def _save_wav(result: TTSResult, output_path: Path) -> None:
    """Save a TTSResult's audio_bytes to a WAV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(result.audio_channels)
        wf.setsampwidth(result.audio_width)
        wf.setframerate(result.audio_rate)
        wf.writeframes(result.audio_bytes)
    logger.info("Saved TTS audio to %s", output_path)
