"""Integration tests for the Piper TTS service via Wyoming protocol.

These tests spin up a real ``WyomingServer`` in ``tts_only`` mode on an
ephemeral port and drive it through the full Wyoming TTS protocol using
``HAEmulator``.

Run integration tests:
    pytest tests/integration/test_piper_tts.py -v

Skip integration tests (unit-only CI):
    pytest -m "not integration"

Notes
-----
When a real Piper ONNX model is present at
``~/.cache/chatterbox/piper/en_US-lessac-medium.onnx``, the tests validate
real synthesised audio (non-silent bytes, expected sample rate, etc.).

When the model is absent the service falls back to ``_MockPiperVoice`` which
emits 3200 bytes of silence.  The protocol-level tests (audio-start /
audio-chunk / audio-stop sequence, latency measurement, error handling) still
run and pass regardless of whether a real model is present.  Real-audio
quality assertions are gated behind ``CHATTERBOX_REAL_PIPER=1``.
"""

import asyncio
import os
import socket
import time
from pathlib import Path
from typing import AsyncGenerator, Tuple

import pytest

from chatterbox.adapters.wyoming.server import WyomingServer
from ha_emulator.emulator import HAEmulator
from ha_emulator.validator import ResultValidator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_LATENCY_LIMIT_MS = 10_000  # 10 s — generous for CPU-only CI
_REAL_PIPER = os.environ.get("CHATTERBOX_REAL_PIPER", "").strip() == "1"

_TEST_TEXTS = [
    "Hello, world.",
    "The quick brown fox jumps over the lazy dog.",
    "One two three four five.",
    "What is the weather today?",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
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


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


def pytest_configure(config):
    """Register custom markers (local, non-ini fallback)."""
    config.addinivalue_line(
        "markers", "integration: requires live Wyoming server (slow)"
    )


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def piper_server() -> AsyncGenerator[Tuple[str, int], None]:
    """Start a WyomingServer in tts_only mode; yield (host, port); teardown."""
    host = "127.0.0.1"
    port = _free_port()

    server = WyomingServer(
        host=host,
        port=port,
        mode="tts_only",
    )

    async def _run_server() -> None:
        try:
            await server.run()
        except (asyncio.CancelledError, BrokenPipeError, OSError, ConnectionError):
            pass

    task = asyncio.get_event_loop().create_task(_run_server())

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


@pytest.fixture(scope="module")
async def emulator(piper_server: Tuple[str, int]) -> HAEmulator:
    """Return an HAEmulator pointed at the live Piper server."""
    host, port = piper_server
    return HAEmulator(host, port, timeout=30.0, connect_timeout=10.0)


# ---------------------------------------------------------------------------
# Test: basic synthesis returns valid audio stream
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_basic_synthesis(emulator: HAEmulator) -> None:
    """A simple text input must produce a non-empty, well-formed audio stream."""
    result = await emulator.run_tts("Hello, world.")

    assert result.success is True, f"TTS failed: {result.error!r}"
    assert result.audio_bytes, "Expected non-empty audio bytes"
    assert len(result.audio_bytes) >= 160, (
        f"Audio too short: {len(result.audio_bytes)} bytes"
    )

    validator = ResultValidator()
    vr = validator.validate_audio(result)
    assert vr.passed, f"Audio validation failed: {vr.details}"

    print(
        f"\nBasic synthesis: {len(result.audio_bytes)} bytes  "
        f"rate={result.audio_rate}  width={result.audio_width}  "
        f"channels={result.audio_channels}  latency={result.latency_ms:.0f} ms"
    )


# ---------------------------------------------------------------------------
# Test: audio format metadata
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_audio_format(emulator: HAEmulator) -> None:
    """AudioStart must advertise valid rate, width, and channels."""
    result = await emulator.run_tts("Check audio format.")

    assert result.success is True, f"TTS failed: {result.error!r}"
    assert result.audio_rate > 0, f"Invalid sample rate: {result.audio_rate}"
    assert result.audio_width in (1, 2, 3, 4), (
        f"Invalid sample width: {result.audio_width}"
    )
    assert result.audio_channels in (1, 2), (
        f"Invalid channels: {result.audio_channels}"
    )


# ---------------------------------------------------------------------------
# Test: latency within limit
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_latency(emulator: HAEmulator) -> None:
    """End-to-end TTS latency must be within the configured limit."""
    result = await emulator.run_tts("Latency test sentence.")

    assert result.success is True, f"TTS failed: {result.error!r}"
    assert result.latency_ms < _LATENCY_LIMIT_MS, (
        f"Latency {result.latency_ms:.0f} ms exceeds {_LATENCY_LIMIT_MS} ms"
    )
    print(f"\nTTS latency: {result.latency_ms:.0f} ms")


# ---------------------------------------------------------------------------
# Test: multiple texts (corpus-style)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_multiple_texts(piper_server: Tuple[str, int]) -> None:
    """All test texts must produce valid audio streams without errors."""
    host, port = piper_server
    validator = ResultValidator()
    failures = []

    for text in _TEST_TEXTS:
        em = HAEmulator(host, port, timeout=30.0, connect_timeout=10.0)
        result = await em.run_tts(text)

        if not result.success:
            failures.append(f"{text!r}: TTS failed — {result.error}")
            continue

        vr = validator.validate_audio(result)
        if not vr.passed:
            failures.append(f"{text!r}: audio validation failed — {vr.details}")

    if failures:
        pytest.fail(
            "TTS corpus failures:\n" + "\n".join(f"  • {f}" for f in failures)
        )


# ---------------------------------------------------------------------------
# Test: empty text
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_empty_text(emulator: HAEmulator) -> None:
    """Sending empty text must not crash the server (result may be empty audio)."""
    result = await emulator.run_tts("")

    # Server must not crash; we accept any success state for empty input.
    assert result is not None
    assert isinstance(result.audio_bytes, bytes)


# ---------------------------------------------------------------------------
# Test: connection refused
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_tts_connection_refused() -> None:
    """Connecting to a closed port must return success=False with error."""
    closed_port = _free_port()
    em = HAEmulator("127.0.0.1", closed_port, timeout=5.0, connect_timeout=2.0)

    result = await em.run_tts("Should fail to connect.")

    assert result.success is False
    assert result.error is not None
    assert "Connection failed" in result.error


# ---------------------------------------------------------------------------
# Test: real audio quality (only when CHATTERBOX_REAL_PIPER=1)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.skipif(
    not _REAL_PIPER,
    reason="Set CHATTERBOX_REAL_PIPER=1 to enable real Piper audio quality tests",
)
async def test_tts_real_audio_quality(emulator: HAEmulator) -> None:
    """With a real Piper model, audio must be non-silent and at 22050 Hz."""
    result = await emulator.run_tts("The quick brown fox jumps over the lazy dog.")

    assert result.success is True, f"TTS failed: {result.error!r}"
    assert result.audio_rate == 22050, (
        f"Expected 22050 Hz, got {result.audio_rate}"
    )
    # Real synthesis produces substantially more than 3200 bytes
    assert len(result.audio_bytes) > 3200, (
        f"Expected >3200 bytes for real synthesis, got {len(result.audio_bytes)}"
    )
    # Check the audio is not all-zero (i.e., not mock silence)
    assert any(b != 0 for b in result.audio_bytes), (
        "Audio bytes are all zero — real Piper synthesis likely not active"
    )
    print(f"\nReal audio quality: {len(result.audio_bytes)} bytes at {result.audio_rate} Hz")
