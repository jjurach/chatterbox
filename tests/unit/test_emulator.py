"""Unit tests for ha_emulator.emulator (mocked Wyoming server)."""

import asyncio
import json
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ha_emulator.emulator import HAEmulator, STTResult, TTSResult, FullResult, _read_wav


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(path: Path, duration_frames: int = 160) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * duration_frames)


def _make_event_bytes(event_type: str, data: dict = None, payload: bytes = None) -> bytes:
    """Encode a Wyoming event using the real wire format (v1.8.0).

    Header JSON: {"type": ..., "version": "1.8.0", ["data_length": N], ["payload_length": M]}
    Followed by data_bytes (JSON) then payload bytes.
    """
    header: dict = {"type": event_type, "version": "1.8.0"}
    data_bytes = b""
    if data:
        data_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    line = json.dumps(header).encode("utf-8") + b"\n"
    return line + data_bytes + (payload or b"")


class FakeStreamReader:
    """Delivers pre-built byte sequences via async_read_event calls."""

    def __init__(self, data: bytes):
        self._buf = asyncio.StreamReader()
        self._buf.feed_data(data)
        self._buf.feed_eof()

    # proxy attribute access so wyoming's async_read_event can use it
    def __getattr__(self, name):
        return getattr(self._buf, name)


# ---------------------------------------------------------------------------
# _read_wav helper
# ---------------------------------------------------------------------------


def test_read_wav(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav)
    pcm, rate, width, channels = _read_wav(wav)
    assert rate == 16000
    assert width == 2
    assert channels == 1
    assert len(pcm) == 160 * 2  # 160 frames × 2 bytes


# ---------------------------------------------------------------------------
# HAEmulator.run_stt — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stt_success(tmp_path):
    wav = tmp_path / "audio.wav"
    _make_wav(wav)

    # Build a fake server response: just a transcript event
    server_response = _make_event_bytes(
        "transcript", {"text": "turn on the lights"}
    )

    reader = FakeStreamReader(server_response)
    writer = MagicMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.drain = AsyncMock()

    with patch(
        "ha_emulator.emulator.asyncio.open_connection",
        new=AsyncMock(return_value=(reader, writer)),
    ):
        emulator = HAEmulator("localhost", 10700, timeout=5.0)
        result = await emulator.run_stt(wav)

    assert result.success is True
    assert result.transcript == "turn on the lights"
    assert result.error is None


# ---------------------------------------------------------------------------
# HAEmulator.run_stt — connection failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stt_connection_refused(tmp_path):
    wav = tmp_path / "audio.wav"
    _make_wav(wav)

    with patch(
        "ha_emulator.emulator.asyncio.open_connection",
        new=AsyncMock(side_effect=OSError("Connection refused")),
    ):
        emulator = HAEmulator("localhost", 10700, timeout=5.0)
        result = await emulator.run_stt(wav)

    assert result.success is False
    assert "Connection failed" in result.error


# ---------------------------------------------------------------------------
# HAEmulator.run_tts — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tts_success():
    audio_payload = b"\x01\x02" * 200

    server_response = (
        _make_event_bytes("audio-start", {"rate": 22050, "width": 2, "channels": 1})
        + _make_event_bytes("audio-chunk", {"rate": 22050, "width": 2, "channels": 1}, payload=audio_payload)
        + _make_event_bytes("audio-stop")
    )

    reader = FakeStreamReader(server_response)
    writer = MagicMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.drain = AsyncMock()

    with patch(
        "ha_emulator.emulator.asyncio.open_connection",
        new=AsyncMock(return_value=(reader, writer)),
    ):
        emulator = HAEmulator("localhost", 10700, timeout=5.0)
        result = await emulator.run_tts("hello world")

    assert result.success is True
    assert result.audio_rate == 22050
    assert result.audio_width == 2
    assert result.audio_channels == 1
    assert len(result.audio_bytes) > 0


# ---------------------------------------------------------------------------
# HAEmulator.run_tts — connection failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tts_connection_refused():
    with patch(
        "ha_emulator.emulator.asyncio.open_connection",
        new=AsyncMock(side_effect=OSError("refused")),
    ):
        emulator = HAEmulator("localhost", 10700)
        result = await emulator.run_tts("hello")

    assert result.success is False
    assert result.audio_bytes == b""


# ---------------------------------------------------------------------------
# HAEmulator.run_full — wires stt + tts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_composes_stt_and_tts(tmp_path):
    wav = tmp_path / "audio.wav"
    _make_wav(wav)

    stt_response = _make_event_bytes("transcript", {"text": "lights on"})
    tts_audio = b"\xff" * 320
    tts_response = (
        _make_event_bytes("audio-start", {"rate": 22050, "width": 2, "channels": 1})
        + _make_event_bytes("audio-chunk", {}, payload=tts_audio)
        + _make_event_bytes("audio-stop")
    )

    call_count = 0

    async def fake_open(host, port):
        nonlocal call_count
        call_count += 1
        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        writer.drain = AsyncMock()
        if call_count == 1:
            return FakeStreamReader(stt_response), writer
        return FakeStreamReader(tts_response), writer

    with patch("ha_emulator.emulator.asyncio.open_connection", new=fake_open):
        emulator = HAEmulator("localhost", 10700, timeout=5.0)
        result = await emulator.run_full(wav)

    assert isinstance(result, FullResult)
    assert result.stt.transcript == "lights on"
    assert result.tts.success is True
    assert result.round_trip_ms >= 0
