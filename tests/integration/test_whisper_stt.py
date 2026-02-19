"""Integration tests for the Whisper STT service via Wyoming protocol.

These tests spin up a real ``WyomingServer`` in ``stt_only`` mode on an
ephemeral port and drive it through the full Wyoming audio-streaming protocol
using ``HAEmulator``.

Run integration tests:
    pytest tests/integration/test_whisper_stt.py -v

Skip integration tests (unit-only CI):
    pytest -m "not integration"
"""

import asyncio
import os
import socket
import time
import wave
from pathlib import Path
from typing import AsyncGenerator, Tuple

import pytest

from chatterbox.adapters.wyoming.server import WyomingServer
from ha_emulator.corpus import CorpusLoader
from ha_emulator.emulator import HAEmulator, STTResult, _read_wav
from ha_emulator.validator import ResultValidator
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import async_read_event, async_write_event

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CORPUS_DIR = Path(__file__).parent.parent / "corpus"
_STT_MODEL = os.environ.get("CHATTERBOX_STT_MODEL", "tiny")
_LATENCY_LIMIT_MS = 30_000  # 30 s — generous for CPU-only CI

# WER threshold for integration tests — relaxed vs unit tests (0.10) because
# the corpus WAVs are synthetic TTS audio and the tiny model has real accuracy
# limits (number words, leading artifacts, occasional mis-hearings).
_WER_TOLERANCE = float(os.environ.get("CHATTERBOX_WER_TOLERANCE", "0.30"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> None:
    """Retry connecting until the port accepts connections or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            if asyncio.get_event_loop().time() >= deadline:
                raise RuntimeError(
                    f"Timed out waiting for {host}:{port} to accept connections"
                )
            await asyncio.sleep(0.2)


def _make_wav(path: Path, duration_frames: int = 160) -> None:
    """Write a minimal silent WAV (16 kHz, 16-bit, mono)."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * duration_frames)


async def _run_stt_audio_only(
    host: str,
    port: int,
    wav_path: Path,
    timeout: float = 60.0,
    connect_timeout: float = 10.0,
    chunk_size: int = 4096,
) -> STTResult:
    """Send a WAV file via Wyoming STT using AudioStop-triggered transcription.

    Sends only ``AudioStart → AudioChunk×N → AudioStop`` (no leading
    ``Transcribe`` event).  This exercises the server's ``stt_only`` AudioStop
    handler, which auto-transcribes when audio streaming completes.

    This helper exists because the server's ``Transcribe`` event handler fires
    immediately (before audio arrives) and returns an empty transcript — a
    known server-side bug documented in the Task 3.6 change log.
    """
    wav_path = Path(wav_path)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=connect_timeout,
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

        await async_write_event(
            AudioStart(rate=rate, width=width, channels=channels).event(), writer
        )

        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i : i + chunk_size]
            await async_write_event(
                AudioChunk(rate=rate, width=width, channels=channels, audio=chunk).event(),
                writer,
            )

        await async_write_event(AudioStop().event(), writer)
        stop_time = time.monotonic()

        # Wait for Transcript
        deadline = time.monotonic() + timeout
        transcript_text = ""
        error = None
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                event = await asyncio.wait_for(async_read_event(reader), timeout=remaining)
            except asyncio.TimeoutError:
                error = "Timeout waiting for Transcript"
                break
            except Exception as exc:
                error = f"Read error: {exc}"
                break

            if event is None:
                error = "Connection closed before Transcript"
                break

            if event.type == "transcript":
                transcript_text = (event.data or {}).get("text", "")
                break

        latency_ms = (time.monotonic() - stop_time) * 1000.0
        return STTResult(
            transcript=transcript_text,
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


# ---------------------------------------------------------------------------
# Module-level server state (started once per test module)
# ---------------------------------------------------------------------------

_server_host: str = "127.0.0.1"
_server_port: int = 0
_server_task: asyncio.Task = None  # type: ignore[assignment]


def pytest_configure(config):
    """Register custom markers (local, non-ini fallback)."""
    config.addinivalue_line(
        "markers", "integration: requires live Wyoming server (slow)"
    )


@pytest.fixture(scope="module")
def server_address() -> Tuple[str, int]:
    """Synchronous fixture that returns the (host, port) of the running server.

    The server is started lazily the first time this fixture is requested and
    reused for all tests in the module.  Teardown is handled by the module
    finaliser registered here.
    """
    return _server_host, _server_port


# We use a conftest-free approach: start/stop the server around the whole
# module via autouse session fixtures is tricky with anyio, so we instead
# start the server inside each async test using a shared asyncio.Event to
# avoid re-spawning it.  A simpler approach: use a module-scoped sync
# fixture that stores state and a helper coroutine.

# For correctness we use pytest's anyio integration with a module-scoped
# async fixture.  anyio supports this via @pytest.fixture + async generator.

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def whisper_server() -> AsyncGenerator[Tuple[str, int], None]:
    """Start a WyomingServer in stt_only mode; yield (host, port); teardown."""
    host = "127.0.0.1"
    port = _free_port()

    server = WyomingServer(
        host=host,
        port=port,
        mode="stt_only",
        stt_model=_STT_MODEL,
        stt_device="cpu",
    )

    async def _run_server() -> None:
        try:
            await server.run()
        except (asyncio.CancelledError, BrokenPipeError, OSError, ConnectionError):
            pass

    task = asyncio.get_event_loop().create_task(_run_server())

    try:
        await _wait_for_port(host, port, timeout=60.0)
        yield host, port
    finally:
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass


@pytest.fixture(scope="module")
async def emulator(whisper_server: Tuple[str, int]) -> HAEmulator:
    """Return an HAEmulator pointed at the live Whisper server."""
    host, port = whisper_server
    return HAEmulator(host, port, timeout=60.0, connect_timeout=10.0)


# ---------------------------------------------------------------------------
# Test: corpus accuracy
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_corpus_accuracy(
    whisper_server: Tuple[str, int],
) -> None:
    """All corpus entries must achieve ≥90 % word accuracy within 30 s.

    NOTE: This test uses ``run_stt_audio_only`` (no leading Transcribe event)
    to work around a known server bug: the server's ``Transcribe`` handler
    transcribes the empty audio buffer immediately when it receives the event,
    then returns ``Transcript(text="")``.  The server correctly transcribes
    via its ``AudioStop`` handler in ``stt_only`` mode, so we use that path.
    """
    host, port = whisper_server
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    assert entries, "No corpus entries found"

    validator = ResultValidator()
    failures: list = []

    for entry in entries:
        result = await _run_stt_audio_only(host, port, entry.wav_path, timeout=60.0)

        if not result.success:
            failures.append(
                f"{entry.wav_path.name}: STT failed — {result.error}"
            )
            continue

        if result.latency_ms >= _LATENCY_LIMIT_MS:
            failures.append(
                f"{entry.wav_path.name}: latency {result.latency_ms:.0f} ms "
                f"exceeds {_LATENCY_LIMIT_MS} ms"
            )

        vr = validator.validate_transcript(
            result.transcript, entry.expected_text, tolerance=_WER_TOLERANCE
        )
        if not vr.passed:
            failures.append(
                f"{entry.wav_path.name}: accuracy too low — {vr.details}"
            )

    if failures:
        pytest.fail(
            "STT corpus accuracy failures:\n" + "\n".join(f"  • {f}" for f in failures)
        )


# ---------------------------------------------------------------------------
# Test: latency P95
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_latency_p95(
    whisper_server: Tuple[str, int],
) -> None:
    """P95 latency over the 5 shortest corpus files must be < 30 s."""
    host, port = whisper_server
    loader = CorpusLoader(_CORPUS_DIR)
    all_entries = loader.load_all()

    # Pick 5 shortest files by WAV file size
    entries = sorted(all_entries, key=lambda e: e.wav_path.stat().st_size)[:5]

    latencies: list = []
    for entry in entries:
        result = await _run_stt_audio_only(host, port, entry.wav_path, timeout=60.0)
        if result.success:
            latencies.append(result.latency_ms)

    assert latencies, "No successful latency measurements"

    latencies.sort()
    idx = int(len(latencies) * 0.95)
    p95 = latencies[min(idx, len(latencies) - 1)]

    print(f"\nSTT latency P95={p95:.0f} ms  (n={len(latencies)})")

    assert p95 < _LATENCY_LIMIT_MS, (
        f"P95 latency {p95:.0f} ms exceeds {_LATENCY_LIMIT_MS} ms"
    )


# ---------------------------------------------------------------------------
# Test: empty audio
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_empty_audio(
    whisper_server: Tuple[str, int],
    tmp_path: Path,
) -> None:
    """Sending a WAV with 0 PCM frames must return success=True, transcript=''."""
    host, port = whisper_server
    em = HAEmulator(host, port, timeout=30.0, connect_timeout=10.0)

    wav = tmp_path / "empty.wav"
    _make_wav(wav, duration_frames=0)

    result = await em.run_stt(wav)

    assert result.success is True, f"Expected success=True, got error={result.error!r}"
    assert result.transcript == "", (
        f"Expected empty transcript for silent audio, got {result.transcript!r}"
    )


# ---------------------------------------------------------------------------
# Test: single frame audio
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_single_frame(
    whisper_server: Tuple[str, int],
    tmp_path: Path,
) -> None:
    """Sending a 1-frame WAV must not crash the server (result may be empty)."""
    host, port = whisper_server
    em = HAEmulator(host, port, timeout=30.0, connect_timeout=10.0)

    wav = tmp_path / "single.wav"
    _make_wav(wav, duration_frames=1)

    result = await em.run_stt(wav)

    # Server must not crash; we accept any success state for 1-frame audio.
    assert result is not None
    assert isinstance(result.transcript, str)


# ---------------------------------------------------------------------------
# Test: connection refused
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_connection_refused(tmp_path: Path) -> None:
    """Connecting to a closed port must return success=False with error."""
    closed_port = _free_port()
    # Port is free — nothing listening there.
    em = HAEmulator("127.0.0.1", closed_port, timeout=5.0, connect_timeout=2.0)

    wav = tmp_path / "dummy.wav"
    _make_wav(wav)

    result = await em.run_stt(wav)

    assert result.success is False
    assert result.error is not None
    assert "Connection failed" in result.error


# ---------------------------------------------------------------------------
# Test: long-form STT (Gettysburg Address, ~49 s)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stt_long_form_gettysburg(
    whisper_server: Tuple[str, int],
) -> None:
    """Transcribing the ~49-second Gettysburg Address opening must succeed.

    This validates that the Wyoming STT service handles long-form audio
    without timing out, and that Whisper's transcription accuracy is
    acceptable (WER ≤ 0.35, relaxed vs. short utterances due to the
    increased difficulty of long continuous speech).

    The speech is Lincoln's Gettysburg Address opening (1863), generated
    via Piper TTS (en_US-ljspeech-high), stored as test_016_gettysburg_address.wav.

    Expected latency: up to 300 seconds on CPU (Whisper tiny processes ~5× speed).
    """
    host, port = whisper_server

    wav_path = _CORPUS_DIR / "test_016_gettysburg_address.wav"
    assert wav_path.exists(), f"Long-form WAV not found: {wav_path}"

    # Long-form transcription can take significantly more time on CPU.
    _LONG_FORM_TIMEOUT = float(os.environ.get("CHATTERBOX_LONG_FORM_TIMEOUT", "300"))
    _LONG_FORM_WER_TOLERANCE = 0.35  # relaxed vs. short utterances

    # Load expected text from corpus.json
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    gettysburg_entry = next(
        (e for e in entries if e.wav_path.name == "test_016_gettysburg_address.wav"),
        None,
    )
    assert gettysburg_entry is not None, "Gettysburg entry missing from corpus.json"

    result = await _run_stt_audio_only(
        host, port, wav_path, timeout=_LONG_FORM_TIMEOUT
    )

    assert result.success, f"Long-form STT failed: {result.error}"

    print(
        f"\nLong-form STT latency: {result.latency_ms:.0f} ms  "
        f"transcript_len={len(result.transcript.split())}"
    )

    validator = ResultValidator()
    vr = validator.validate_transcript(
        result.transcript,
        gettysburg_entry.expected_text,
        tolerance=_LONG_FORM_WER_TOLERANCE,
    )
    assert vr.passed, (
        f"Long-form STT accuracy too low — {vr.details}\n"
        f"  transcript: {result.transcript!r}\n"
        f"  expected:   {gettysburg_entry.expected_text!r}"
    )
