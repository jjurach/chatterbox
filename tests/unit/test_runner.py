"""Unit tests for ha_emulator.runner."""

import json
import wave
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ha_emulator.corpus import CorpusEntry, CorpusLoader
from ha_emulator.emulator import HAEmulator, STTResult, TTSResult
from ha_emulator.runner import EntryReport, TestReport, TestRunner, _build_report
from ha_emulator.validator import ResultValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)


def _corpus_with_entries(tmp_path, entries):
    """Create a minimal corpus directory with given entries."""
    manifest = []
    for file, expected, desc in entries:
        wav = tmp_path / file
        _make_wav(wav)
        manifest.append({"file": file, "expected": expected, "description": desc})
    (tmp_path / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# _build_report
# ---------------------------------------------------------------------------


def test_build_report_counts_correctly():
    reports = [
        EntryReport("a.wav", "hello", "hello", True, 0.0, 100.0),
        EntryReport("b.wav", "world", "wörld", False, 0.5, 200.0),
    ]
    report = _build_report(reports)
    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
    assert report.skipped == 0
    assert report.avg_latency_ms == pytest.approx(150.0)
    assert report.min_latency_ms == pytest.approx(100.0)
    assert report.max_latency_ms == pytest.approx(200.0)


def test_build_report_empty():
    report = _build_report([])
    assert report.total == 0
    assert report.avg_latency_ms == 0.0


# ---------------------------------------------------------------------------
# TestRunner.run_stt_suite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stt_suite_all_pass(tmp_path):
    corpus_dir = _corpus_with_entries(
        tmp_path,
        [("test_001.wav", "turn on the lights", "lights")],
    )

    emulator = HAEmulator("localhost", 10700)
    loader = CorpusLoader(corpus_dir)
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    # Mock emulator.run_stt to return a successful result
    emulator.run_stt = AsyncMock(
        return_value=STTResult(
            transcript="turn on the lights",
            latency_ms=50.0,
            success=True,
        )
    )

    report = await runner.run_stt_suite()

    assert report.total == 1
    assert report.passed == 1
    assert report.failed == 0


@pytest.mark.asyncio
async def test_run_stt_suite_failure_recorded(tmp_path):
    corpus_dir = _corpus_with_entries(
        tmp_path,
        [("test_001.wav", "turn on the lights", "lights")],
    )

    emulator = HAEmulator("localhost", 10700)
    loader = CorpusLoader(corpus_dir)
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    emulator.run_stt = AsyncMock(
        return_value=STTResult(
            transcript="",
            latency_ms=0.0,
            success=False,
            error="Connection refused",
        )
    )

    report = await runner.run_stt_suite()

    assert report.failed == 1
    assert report.entries[0].error == "Connection refused"


# ---------------------------------------------------------------------------
# TestRunner.run_tts_suite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tts_suite_all_pass(tmp_path):
    emulator = HAEmulator("localhost", 10700)
    loader = CorpusLoader(tmp_path)  # not used in tts suite
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    emulator.run_tts = AsyncMock(
        return_value=TTSResult(
            audio_bytes=b"\x00" * 320,
            audio_rate=22050,
            audio_width=2,
            audio_channels=1,
            latency_ms=80.0,
            success=True,
        )
    )

    report = await runner.run_tts_suite(["hello world", "goodbye"])

    assert report.total == 2
    assert report.passed == 2


# ---------------------------------------------------------------------------
# TestRunner.save_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_report_writes_json(tmp_path):
    emulator = HAEmulator("localhost", 10700)
    loader = CorpusLoader(tmp_path)
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    report = _build_report(
        [EntryReport("a.wav", "hello", "hello", True, 0.0, 55.0)]
    )
    out = tmp_path / "report.json"
    runner.save_report(report, out)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data["total"] == 1
    assert data["passed"] == 1


# ---------------------------------------------------------------------------
# TestRunner.print_report — smoke test (no assertion, just no exception)
# ---------------------------------------------------------------------------


def test_print_report_does_not_raise(capsys):
    emulator = HAEmulator("localhost", 10700)
    loader = CorpusLoader(Path("."))
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    report = _build_report(
        [
            EntryReport("a.wav", "hello", "hello", True, 0.0, 50.0),
            EntryReport("b.wav", "world", "ward", False, 0.5, 150.0),
        ]
    )
    runner.print_report(report)
    captured = capsys.readouterr()
    assert "PASS" in captured.out
    assert "FAIL" in captured.out
