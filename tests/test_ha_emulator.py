"""Unit tests for ha_emulator — validator, runner, and corpus loader."""

import asyncio
import json
import struct
import tempfile
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ha_emulator.corpus import CorpusEntry, CorpusLoader
from ha_emulator.emulator import STTResult, TTSResult, FullResult
from ha_emulator.runner import EntryReport, TestReport, TestRunner, _build_report
from ha_emulator.validator import ResultValidator, ValidationResult, _normalize, _wer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tts_result(
    audio_bytes=b"\x00\x01" * 80,
    rate=22050,
    width=2,
    channels=1,
    success=True,
    error=None,
    latency_ms=50.0,
) -> TTSResult:
    return TTSResult(
        audio_bytes=audio_bytes,
        audio_rate=rate,
        audio_width=width,
        audio_channels=channels,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )


def _make_stt_result(
    transcript="hello world",
    latency_ms=100.0,
    success=True,
    error=None,
) -> STTResult:
    return STTResult(
        transcript=transcript,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )


def _write_temp_wav(path: Path, duration_frames: int = 1600) -> None:
    """Write a minimal mono 16kHz WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * duration_frames)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercases(self):
        assert _normalize("Hello WORLD") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert _normalize("Hello, world!") == ["hello", "world"]

    def test_empty_string(self):
        assert _normalize("") == []

    def test_only_punctuation(self):
        assert _normalize("...") == []


# ---------------------------------------------------------------------------
# _wer
# ---------------------------------------------------------------------------


class TestWer:
    def test_identical(self):
        assert _wer(["a", "b", "c"], ["a", "b", "c"]) == 0.0

    def test_completely_different(self):
        # 3 substitutions / 3 ref words = 1.0
        assert _wer(["a", "b", "c"], ["x", "y", "z"]) == 1.0

    def test_one_insertion(self):
        # ref=["a","b"]  hyp=["a","b","c"]  → 1 insertion / 2 = 0.5
        assert _wer(["a", "b"], ["a", "b", "c"]) == 0.5

    def test_empty_reference_empty_hypothesis(self):
        assert _wer([], []) == 0.0

    def test_empty_reference_nonempty_hypothesis(self):
        assert _wer([], ["a"]) == 1.0

    def test_empty_hypothesis(self):
        # ref=3, hyp=0 → 3 deletions / 3 = 1.0
        assert _wer(["a", "b", "c"], []) == 1.0


# ---------------------------------------------------------------------------
# ResultValidator.validate_transcript
# ---------------------------------------------------------------------------


class TestValidateTranscript:
    def setup_method(self):
        self.v = ResultValidator()

    def test_exact_match(self):
        vr = self.v.validate_transcript("turn on the lights", "turn on the lights")
        assert vr.passed
        assert vr.score == pytest.approx(1.0)

    def test_case_insensitive(self):
        vr = self.v.validate_transcript("Turn On The Lights", "turn on the lights")
        assert vr.passed
        assert vr.score == pytest.approx(1.0)

    def test_punctuation_ignored(self):
        vr = self.v.validate_transcript("turn on the lights!", "turn on the lights")
        assert vr.passed

    def test_one_word_error_within_tolerance(self):
        # "set the lights" vs "turn on the lights" — some errors but might pass
        vr = self.v.validate_transcript(
            "turn on the lamps", "turn on the lights", tolerance=0.5
        )
        assert vr.passed  # 1 sub out of 4 = 0.25 WER ≤ 0.5

    def test_high_wer_fails(self):
        vr = self.v.validate_transcript("foo bar baz", "turn on the lights")
        assert not vr.passed

    def test_score_bounded(self):
        vr = self.v.validate_transcript("completely wrong text here", "short")
        assert 0.0 <= vr.score <= 1.0

    def test_details_contains_expected_and_actual(self):
        vr = self.v.validate_transcript("hello", "world")
        assert "hello" in vr.details
        assert "world" in vr.details

    def test_returns_validation_result(self):
        vr = self.v.validate_transcript("hello", "hello")
        assert isinstance(vr, ValidationResult)


# ---------------------------------------------------------------------------
# ResultValidator.validate_audio
# ---------------------------------------------------------------------------


class TestValidateAudio:
    def setup_method(self):
        self.v = ResultValidator()

    def test_valid_audio_passes(self):
        result = _make_tts_result()
        vr = self.v.validate_audio(result)
        assert vr.passed
        assert vr.score == 1.0

    def test_empty_bytes_fails(self):
        result = _make_tts_result(audio_bytes=b"")
        vr = self.v.validate_audio(result)
        assert not vr.passed
        assert vr.score == 0.0
        assert "No audio bytes" in vr.details

    def test_too_short_fails(self):
        result = _make_tts_result(audio_bytes=b"\x00" * 100)
        vr = self.v.validate_audio(result)
        assert not vr.passed

    def test_invalid_rate_fails(self):
        result = _make_tts_result(rate=0)
        vr = self.v.validate_audio(result)
        assert not vr.passed
        assert "invalid rate" in vr.details

    def test_invalid_width_fails(self):
        result = _make_tts_result(width=5)
        vr = self.v.validate_audio(result)
        assert not vr.passed
        assert "invalid width" in vr.details

    def test_invalid_channels_fails(self):
        result = _make_tts_result(channels=3)
        vr = self.v.validate_audio(result)
        assert not vr.passed
        assert "invalid channels" in vr.details

    def test_valid_stereo(self):
        result = _make_tts_result(channels=2, audio_bytes=b"\x00\x01" * 80)
        vr = self.v.validate_audio(result)
        assert vr.passed


# ---------------------------------------------------------------------------
# ResultValidator.save_audio
# ---------------------------------------------------------------------------


class TestSaveAudio:
    def test_saves_wav_file(self, tmp_path):
        v = ResultValidator()
        result = _make_tts_result(audio_bytes=b"\x00\x01" * 80, rate=22050, width=2, channels=1)
        out = tmp_path / "out.wav"
        v.save_audio(result, out)
        assert out.exists()

        with wave.open(str(out), "rb") as wf:
            assert wf.getframerate() == 22050
            assert wf.getsampwidth() == 2
            assert wf.getnchannels() == 1

    def test_creates_parent_dirs(self, tmp_path):
        v = ResultValidator()
        result = _make_tts_result()
        out = tmp_path / "nested" / "dir" / "out.wav"
        v.save_audio(result, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# _build_report
# ---------------------------------------------------------------------------


class TestBuildReport:
    def test_empty(self):
        report = _build_report([])
        assert report.total == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.avg_latency_ms == 0.0

    def test_all_pass(self):
        entries = [
            EntryReport("a.wav", "hello", "hello", True, 0.0, 100.0),
            EntryReport("b.wav", "world", "world", True, 0.0, 200.0),
        ]
        report = _build_report(entries)
        assert report.total == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.avg_latency_ms == pytest.approx(150.0)

    def test_some_fail(self):
        entries = [
            EntryReport("a.wav", "hello", "bye", False, 1.0, 100.0),
            EntryReport("b.wav", "world", "world", True, 0.0, 200.0),
        ]
        report = _build_report(entries)
        assert report.passed == 1
        assert report.failed == 1


# ---------------------------------------------------------------------------
# TestRunner (mocked emulator)
# ---------------------------------------------------------------------------


def _make_corpus_entry(wav_path: Path, expected: str) -> CorpusEntry:
    return CorpusEntry(wav_path=wav_path, expected_text=expected, description="test")


class TestTestRunnerSTT:
    def _make_runner(self, entries, stt_result):
        emulator = MagicMock()
        emulator.run_stt = AsyncMock(return_value=stt_result)
        loader = MagicMock()
        loader.load_all.return_value = entries
        validator = ResultValidator()
        return TestRunner(emulator, loader, validator)

    def test_stt_suite_all_pass(self, tmp_path):
        wav = tmp_path / "a.wav"
        _write_temp_wav(wav)
        entries = [_make_corpus_entry(wav, "turn on the lights")]
        runner = self._make_runner(entries, _make_stt_result("turn on the lights"))
        report = asyncio.run(runner.run_stt_suite())
        assert report.total == 1
        assert report.passed == 1

    def test_stt_suite_connection_failure(self, tmp_path):
        wav = tmp_path / "a.wav"
        _write_temp_wav(wav)
        entries = [_make_corpus_entry(wav, "hello")]
        runner = self._make_runner(
            entries, _make_stt_result(success=False, error="Connection failed", transcript="")
        )
        report = asyncio.run(runner.run_stt_suite())
        assert report.failed == 1
        assert report.entries[0].error == "Connection failed"

    def test_stt_suite_transcript_mismatch(self, tmp_path):
        wav = tmp_path / "a.wav"
        _write_temp_wav(wav)
        entries = [_make_corpus_entry(wav, "turn on the lights")]
        runner = self._make_runner(entries, _make_stt_result("completely wrong text here"))
        report = asyncio.run(runner.run_stt_suite())
        assert report.failed == 1


class TestTestRunnerTTS:
    def _make_runner(self, tts_result):
        emulator = MagicMock()
        emulator.run_tts = AsyncMock(return_value=tts_result)
        loader = MagicMock()
        validator = ResultValidator()
        return TestRunner(emulator, loader, validator)

    def test_tts_suite_all_pass(self):
        runner = self._make_runner(_make_tts_result())
        report = asyncio.run(runner.run_tts_suite(["hello world"]))
        assert report.total == 1
        assert report.passed == 1

    def test_tts_suite_connection_failure(self):
        runner = self._make_runner(
            _make_tts_result(audio_bytes=b"", rate=0, width=0, channels=0, success=False, error="Connection failed")
        )
        report = asyncio.run(runner.run_tts_suite(["hello"]))
        assert report.failed == 1

    def test_tts_suite_invalid_audio(self):
        runner = self._make_runner(_make_tts_result(audio_bytes=b""))
        report = asyncio.run(runner.run_tts_suite(["hello"]))
        assert report.failed == 1


class TestTestRunnerFull:
    def _make_runner(self, entries, stt_result, tts_result):
        emulator = MagicMock()
        full_result = FullResult(stt=stt_result, tts=tts_result, round_trip_ms=200.0)
        emulator.run_full = AsyncMock(return_value=full_result)
        loader = MagicMock()
        loader.load_all.return_value = entries
        validator = ResultValidator()
        return TestRunner(emulator, loader, validator)

    def test_full_suite_pass(self, tmp_path):
        wav = tmp_path / "a.wav"
        _write_temp_wav(wav)
        entries = [_make_corpus_entry(wav, "turn on the lights")]
        runner = self._make_runner(
            entries,
            _make_stt_result("turn on the lights"),
            _make_tts_result(),
        )
        report = asyncio.run(runner.run_full_suite())
        assert report.passed == 1

    def test_full_suite_stt_failure(self, tmp_path):
        wav = tmp_path / "a.wav"
        _write_temp_wav(wav)
        entries = [_make_corpus_entry(wav, "turn on the lights")]
        runner = self._make_runner(
            entries,
            _make_stt_result(success=False, error="STT error", transcript=""),
            _make_tts_result(),
        )
        report = asyncio.run(runner.run_full_suite())
        assert report.failed == 1


# ---------------------------------------------------------------------------
# TestRunner.print_report / save_report
# ---------------------------------------------------------------------------


class TestReporting:
    def _make_report(self):
        entries = [
            EntryReport("a.wav", "hello", "hello", True, 0.0, 100.0),
            EntryReport("b.wav", "world", "bye", False, 1.0, 200.0, error=None),
        ]
        return _build_report(entries)

    def test_print_report_runs(self, capsys):
        runner = TestRunner(MagicMock(), MagicMock(), ResultValidator())
        runner.print_report(self._make_report())
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "FAIL" in out

    def test_save_report_json(self, tmp_path):
        runner = TestRunner(MagicMock(), MagicMock(), ResultValidator())
        out = tmp_path / "report.json"
        runner.save_report(self._make_report(), out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["total"] == 2
        assert data["passed"] == 1
        assert data["failed"] == 1
        assert len(data["entries"]) == 2


# ---------------------------------------------------------------------------
# CorpusLoader
# ---------------------------------------------------------------------------


class TestCorpusLoader:
    def _make_corpus(self, tmp_path, entries):
        manifest = [
            {"file": e["file"], "expected": e["expected"], "description": e.get("desc", "")}
            for e in entries
        ]
        (tmp_path / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
        for e in entries:
            _write_temp_wav(tmp_path / e["file"])

    def test_load_all(self, tmp_path):
        self._make_corpus(tmp_path, [
            {"file": "a.wav", "expected": "hello"},
            {"file": "b.wav", "expected": "world"},
        ])
        loader = CorpusLoader(tmp_path)
        entries = loader.load_all()
        assert len(entries) == 2
        assert entries[0].wav_path.name == "a.wav"
        assert entries[0].expected_text == "hello"

    def test_missing_directory(self, tmp_path):
        loader = CorpusLoader(tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="Corpus directory"):
            loader.load_all()

    def test_missing_manifest(self, tmp_path):
        loader = CorpusLoader(tmp_path)
        with pytest.raises(FileNotFoundError, match="manifest"):
            loader.load_all()

    def test_missing_wav_skipped(self, tmp_path):
        manifest = [
            {"file": "present.wav", "expected": "hello"},
            {"file": "missing.wav", "expected": "world"},
        ]
        (tmp_path / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
        _write_temp_wav(tmp_path / "present.wav")
        loader = CorpusLoader(tmp_path)
        entries = loader.load_all()
        assert len(entries) == 1
        assert entries[0].wav_path.name == "present.wav"

    def test_load_entry_by_stem(self, tmp_path):
        self._make_corpus(tmp_path, [{"file": "test_001.wav", "expected": "hello"}])
        loader = CorpusLoader(tmp_path)
        entry = loader.load_entry("test_001")
        assert entry.expected_text == "hello"

    def test_load_entry_not_found(self, tmp_path):
        self._make_corpus(tmp_path, [{"file": "a.wav", "expected": "hello"}])
        loader = CorpusLoader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load_entry("nonexistent")

    def test_sorted_by_filename(self, tmp_path):
        self._make_corpus(tmp_path, [
            {"file": "c.wav", "expected": "c"},
            {"file": "a.wav", "expected": "a"},
            {"file": "b.wav", "expected": "b"},
        ])
        loader = CorpusLoader(tmp_path)
        entries = loader.load_all()
        names = [e.wav_path.name for e in entries]
        assert names == sorted(names)
