"""Round-trip integration tests for the Wyoming STT → TTS pipeline.

Each test spins up *two* independent ``WyomingServer`` instances — one in
``stt_only`` mode (Whisper) and one in ``tts_only`` mode (Piper) — then
drives a full round-trip:

    WAV file  ──►  STT server  ──►  transcript text  ──►  TTS server  ──►  audio bytes

The tests validate:

* End-to-end latency for a complete STT + TTS cycle.
* Transcript fidelity: the text produced by STT matches expected corpus text.
* Audio validity: the TTS audio stream is non-empty and well-formed.
* Concurrent round-trips: multiple requests in parallel do not corrupt results.
* Error propagation: a failed STT step prevents (or gracefully handles) TTS.

Run integration tests:
    pytest tests/integration/test_round_trip.py -v

Skip integration tests (unit-only CI):
    pytest -m "not integration"
"""

import asyncio
import socket
import time
import wave
from pathlib import Path
from typing import AsyncGenerator, List, Tuple

import pytest

from chatterbox.adapters.wyoming.server import WyomingServer
from ha_emulator.corpus import CorpusLoader
from ha_emulator.emulator import HAEmulator, FullResult, STTResult, _read_wav
from ha_emulator.validator import ResultValidator
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import async_read_event, async_write_event

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CORPUS_DIR = Path(__file__).parent.parent / "corpus"

# WER tolerance — relaxed for integration tests because corpus WAVs are
# synthetic TTS audio and the tiny Whisper model has known accuracy limits.
_WER_TOLERANCE = 0.30

# Total latency budget for a single STT + TTS cycle (generous for CPU-only CI).
_ROUND_TRIP_LIMIT_MS = 120_000  # 120 s

# Minimum audio bytes expected from TTS (mock Piper returns 3200 bytes silence).
_MIN_AUDIO_BYTES = 160


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


async def _stt_audio_only(
    host: str,
    port: int,
    wav_path: Path,
    timeout: float = 60.0,
    connect_timeout: float = 10.0,
    chunk_size: int = 4096,
) -> STTResult:
    """Send a WAV file via Wyoming STT using AudioStop-triggered transcription.

    Sends ``AudioStart → AudioChunk×N → AudioStop`` without a leading
    ``Transcribe`` event, exercising the server's AudioStop handler.

    This avoids the known server bug where the ``Transcribe`` event handler
    fires immediately (before audio) and returns an empty transcript.
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
                AudioChunk(
                    rate=rate, width=width, channels=channels, audio=chunk
                ).event(),
                writer,
            )
        await async_write_event(AudioStop().event(), writer)
        stop_time = time.monotonic()

        deadline = time.monotonic() + timeout
        transcript_text = ""
        error = None
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                event = await asyncio.wait_for(
                    async_read_event(reader), timeout=remaining
                )
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


async def _run_round_trip(
    stt_host: str,
    stt_port: int,
    tts_host: str,
    tts_port: int,
    wav_path: Path,
    stt_timeout: float = 120.0,
    tts_timeout: float = 30.0,
) -> FullResult:
    """Execute one complete STT → TTS round-trip.

    Returns a ``FullResult`` with timing for both legs and the combined
    ``round_trip_ms``.
    """
    from ha_emulator.emulator import TTSResult

    start = time.monotonic()

    # --- STT leg ---
    stt_result = await _stt_audio_only(
        stt_host, stt_port, wav_path, timeout=stt_timeout
    )

    if not stt_result.success:
        # Build a failed TTSResult so callers always receive a FullResult.
        failed_tts = TTSResult(
            audio_bytes=b"",
            audio_rate=0,
            audio_width=0,
            audio_channels=0,
            latency_ms=0.0,
            success=False,
            error="STT failed; TTS skipped",
        )
        round_trip_ms = (time.monotonic() - start) * 1000.0
        return FullResult(stt=stt_result, tts=failed_tts, round_trip_ms=round_trip_ms)

    # --- TTS leg ---
    tts_emulator = HAEmulator(
        tts_host, tts_port, timeout=tts_timeout, connect_timeout=10.0
    )
    tts_result = await tts_emulator.run_tts(stt_result.transcript)

    round_trip_ms = (time.monotonic() - start) * 1000.0
    return FullResult(stt=stt_result, tts=tts_result, round_trip_ms=round_trip_ms)


# ---------------------------------------------------------------------------
# Module-level anyio backend declaration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


# ---------------------------------------------------------------------------
# Server fixtures (module-scoped — started once, reused across all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def stt_server() -> AsyncGenerator[Tuple[str, int], None]:
    """Start a WyomingServer in stt_only mode; yield (host, port); teardown."""
    import os

    host = "127.0.0.1"
    port = _free_port()
    stt_model = os.environ.get("CHATTERBOX_STT_MODEL", "tiny")

    server = WyomingServer(
        host=host,
        port=port,
        mode="stt_only",
        stt_model=stt_model,
        stt_device="cpu",
    )

    async def _run() -> None:
        try:
            await server.run()
        except (asyncio.CancelledError, BrokenPipeError, OSError, ConnectionError):
            pass

    task = asyncio.get_event_loop().create_task(_run())
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
async def tts_server() -> AsyncGenerator[Tuple[str, int], None]:
    """Start a WyomingServer in tts_only mode; yield (host, port); teardown."""
    host = "127.0.0.1"
    port = _free_port()

    server = WyomingServer(host=host, port=port, mode="tts_only")

    async def _run() -> None:
        try:
            await server.run()
        except (asyncio.CancelledError, BrokenPipeError, OSError, ConnectionError):
            pass

    task = asyncio.get_event_loop().create_task(_run())
    try:
        await _wait_for_port(host, port, timeout=30.0)
        yield host, port
    finally:
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Test: single round-trip (shortest corpus file)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_single(
    stt_server: Tuple[str, int],
    tts_server: Tuple[str, int],
) -> None:
    """A single round-trip (STT → TTS) must complete within the time budget.

    Uses the shortest corpus file so the test is as fast as possible.
    """
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    assert entries, "No corpus entries found"

    # Pick the shortest WAV by file size.
    entry = min(entries, key=lambda e: e.wav_path.stat().st_size)

    stt_host, stt_port = stt_server
    tts_host, tts_port = tts_server

    result = await _run_round_trip(
        stt_host, stt_port, tts_host, tts_port, entry.wav_path
    )

    assert result.stt.success, f"STT failed: {result.stt.error}"
    assert result.tts.success, f"TTS failed: {result.tts.error}"
    assert result.round_trip_ms < _ROUND_TRIP_LIMIT_MS, (
        f"Round-trip took {result.round_trip_ms:.0f} ms "
        f"(limit {_ROUND_TRIP_LIMIT_MS} ms)"
    )

    print(
        f"\nRound-trip ({entry.wav_path.name}): "
        f"STT={result.stt.latency_ms:.0f} ms  "
        f"TTS={result.tts.latency_ms:.0f} ms  "
        f"total={result.round_trip_ms:.0f} ms"
    )


# ---------------------------------------------------------------------------
# Test: transcript accuracy survives the pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_transcript_accuracy(
    stt_server: Tuple[str, int],
    tts_server: Tuple[str, int],
) -> None:
    """STT transcripts returned during round-trips must match corpus ground truth.

    This validates that the STT leg of the pipeline preserves textual fidelity
    even when the full round-trip flow is active (rather than STT-only mode).
    """
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    assert entries, "No corpus entries found"

    stt_host, stt_port = stt_server
    tts_host, tts_port = tts_server
    validator = ResultValidator()

    failures: List[str] = []

    for entry in entries:
        result = await _run_round_trip(
            stt_host, stt_port, tts_host, tts_port, entry.wav_path
        )

        if not result.stt.success:
            failures.append(f"{entry.wav_path.name}: STT failed — {result.stt.error}")
            continue

        vr = validator.validate_transcript(
            result.stt.transcript, entry.expected_text, tolerance=_WER_TOLERANCE
        )
        if not vr.passed:
            failures.append(f"{entry.wav_path.name}: {vr.details}")

    if failures:
        pytest.fail(
            "Round-trip transcript accuracy failures:\n"
            + "\n".join(f"  • {f}" for f in failures)
        )


# ---------------------------------------------------------------------------
# Test: TTS audio is valid after round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_audio_validity(
    stt_server: Tuple[str, int],
    tts_server: Tuple[str, int],
) -> None:
    """The TTS audio leg of every round-trip must produce valid audio.

    Validates non-empty bytes and correct format parameters (rate, width,
    channels) for every corpus entry processed through the full pipeline.
    """
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    assert entries, "No corpus entries found"

    stt_host, stt_port = stt_server
    tts_host, tts_port = tts_server
    validator = ResultValidator()

    failures: List[str] = []

    for entry in entries:
        result = await _run_round_trip(
            stt_host, stt_port, tts_host, tts_port, entry.wav_path
        )

        if not result.stt.success:
            # STT failure is reported in accuracy test; skip TTS check here.
            continue

        if not result.tts.success:
            failures.append(f"{entry.wav_path.name}: TTS failed — {result.tts.error}")
            continue

        vr = validator.validate_audio(result.tts)
        if not vr.passed:
            failures.append(f"{entry.wav_path.name}: audio invalid — {vr.details}")

    if failures:
        pytest.fail(
            "Round-trip audio validity failures:\n"
            + "\n".join(f"  • {f}" for f in failures)
        )


# ---------------------------------------------------------------------------
# Test: end-to-end latency P95
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_latency_p95(
    stt_server: Tuple[str, int],
    tts_server: Tuple[str, int],
) -> None:
    """P95 round-trip latency over the 5 shortest corpus files must be within budget."""
    loader = CorpusLoader(_CORPUS_DIR)
    all_entries = loader.load_all()
    entries = sorted(all_entries, key=lambda e: e.wav_path.stat().st_size)[:5]

    stt_host, stt_port = stt_server
    tts_host, tts_port = tts_server

    latencies: List[float] = []
    for entry in entries:
        result = await _run_round_trip(
            stt_host, stt_port, tts_host, tts_port, entry.wav_path
        )
        if result.stt.success and result.tts.success:
            latencies.append(result.round_trip_ms)

    assert latencies, "No successful round-trip latency measurements"

    latencies.sort()
    idx = int(len(latencies) * 0.95)
    p95 = latencies[min(idx, len(latencies) - 1)]

    print(f"\nRound-trip latency P95={p95:.0f} ms  (n={len(latencies)})")

    assert (
        p95 < _ROUND_TRIP_LIMIT_MS
    ), f"P95 latency {p95:.0f} ms exceeds {_ROUND_TRIP_LIMIT_MS} ms"


# ---------------------------------------------------------------------------
# Test: concurrent round-trips
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_concurrent(
    stt_server: Tuple[str, int],
    tts_server: Tuple[str, int],
) -> None:
    """Three simultaneous round-trips must all complete successfully.

    This exercises the servers' ability to handle overlapping requests without
    corrupting transcripts or audio streams.
    """
    loader = CorpusLoader(_CORPUS_DIR)
    entries = loader.load_all()
    assert len(entries) >= 3, "Need at least 3 corpus entries for concurrency test"

    # Use the 3 shortest files for speed.
    selected = sorted(entries, key=lambda e: e.wav_path.stat().st_size)[:3]

    stt_host, stt_port = stt_server
    tts_host, tts_port = tts_server

    tasks = [
        asyncio.create_task(
            _run_round_trip(stt_host, stt_port, tts_host, tts_port, e.wav_path)
        )
        for e in selected
    ]
    results: List[FullResult] = await asyncio.gather(*tasks)

    failures: List[str] = []
    for entry, result in zip(selected, results):
        if not result.stt.success:
            failures.append(f"{entry.wav_path.name}: STT failed — {result.stt.error}")
        elif not result.tts.success:
            failures.append(f"{entry.wav_path.name}: TTS failed — {result.tts.error}")

    if failures:
        pytest.fail(
            "Concurrent round-trip failures:\n"
            + "\n".join(f"  • {f}" for f in failures)
        )

    print(
        f"\nConcurrent round-trips ({len(results)} parallel): "
        + "  ".join(f"{r.round_trip_ms:.0f} ms" for r in results)
    )


# ---------------------------------------------------------------------------
# Test: STT failure gracefully handled (no TTS invoked)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_round_trip_stt_failure_propagation(
    tts_server: Tuple[str, int],
    tmp_path: Path,
) -> None:
    """When STT fails (refused connection), the round-trip must return success=False.

    The TTS leg should be skipped — we verify the FullResult reflects the
    upstream STT failure without crashing.
    """
    closed_port = _free_port()
    # Nothing is listening on closed_port.

    tts_host, tts_port = tts_server

    # Create a minimal WAV to submit.
    wav = tmp_path / "dummy.wav"
    with wave.open(str(wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)

    result = await _run_round_trip(
        "127.0.0.1", closed_port, tts_host, tts_port, wav, stt_timeout=5.0
    )

    assert result.stt.success is False, "Expected STT to fail on refused port"
    assert result.tts.success is False, "Expected TTS to be skipped when STT fails"
    assert result.stt.error is not None
