"""Unit tests for ha_emulator.validator."""

import pytest

from ha_emulator.emulator import TTSResult
from ha_emulator.validator import ResultValidator, _normalize, _wer


class TestNormalize:
    def test_lowercases_text(self):
        assert _normalize("Hello World") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert _normalize("hello, world!") == ["hello", "world"]

    def test_empty_string(self):
        assert _normalize("") == []


class TestWER:
    def test_identical_sequences(self):
        assert _wer(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(0.0)

    def test_all_wrong(self):
        assert _wer(["a", "b"], ["x", "y"]) == pytest.approx(1.0)

    def test_one_substitution(self):
        # 1 sub / 3 ref words = 0.333…
        assert _wer(["a", "b", "c"], ["a", "b", "x"]) == pytest.approx(1 / 3)

    def test_insertion(self):
        # hypothesis longer → insertion
        assert _wer(["a"], ["a", "b"]) == pytest.approx(1.0)

    def test_deletion(self):
        # hypothesis shorter → deletion
        assert _wer(["a", "b"], ["a"]) == pytest.approx(0.5)

    def test_empty_reference_empty_hypothesis(self):
        assert _wer([], []) == pytest.approx(0.0)

    def test_empty_reference_nonempty_hypothesis(self):
        assert _wer([], ["a"]) == pytest.approx(1.0)


class TestResultValidator:
    def setup_method(self):
        self.v = ResultValidator()

    # -- transcript validation ------------------------------------------

    def test_exact_match_passes(self):
        result = self.v.validate_transcript("turn on the lights", "turn on the lights")
        assert result.passed is True
        assert result.score == pytest.approx(1.0)

    def test_case_insensitive_match(self):
        result = self.v.validate_transcript("Turn On The Lights", "turn on the lights")
        assert result.passed is True

    def test_punctuation_ignored(self):
        result = self.v.validate_transcript(
            "turn on the lights!", "turn on the lights"
        )
        assert result.passed is True

    def test_one_wrong_word_below_threshold(self):
        # "turn on the lamp" vs "turn on the lights" → WER = 1/4 = 0.25  → FAIL
        result = self.v.validate_transcript("turn on the lamp", "turn on the lights")
        assert result.passed is False

    def test_custom_tolerance(self):
        # WER = 1/4 = 0.25; tolerance=0.30 → should pass
        result = self.v.validate_transcript(
            "turn on the lamp", "turn on the lights", tolerance=0.30
        )
        assert result.passed is True

    def test_empty_strings(self):
        result = self.v.validate_transcript("", "")
        assert result.passed is True

    # -- audio validation -----------------------------------------------

    def _make_tts(self, audio_bytes=None, rate=22050, width=2, channels=1):
        return TTSResult(
            audio_bytes=audio_bytes if audio_bytes is not None else b"\x00" * 320,
            audio_rate=rate,
            audio_width=width,
            audio_channels=channels,
            latency_ms=100.0,
            success=True,
        )

    def test_valid_audio_passes(self):
        result = self.v.validate_audio(self._make_tts())
        assert result.passed is True
        assert result.score == pytest.approx(1.0)

    def test_empty_audio_fails(self):
        result = self.v.validate_audio(self._make_tts(audio_bytes=b""))
        assert result.passed is False

    def test_too_short_audio_fails(self):
        result = self.v.validate_audio(self._make_tts(audio_bytes=b"\x00" * 100))
        assert result.passed is False

    def test_invalid_rate_fails(self):
        result = self.v.validate_audio(self._make_tts(rate=0))
        assert result.passed is False

    def test_invalid_width_fails(self):
        result = self.v.validate_audio(self._make_tts(width=0))
        assert result.passed is False

    def test_invalid_channels_fails(self):
        result = self.v.validate_audio(self._make_tts(channels=3))
        assert result.passed is False

    # -- save_audio -------------------------------------------------------

    def test_save_audio_creates_wav(self, tmp_path):
        out = tmp_path / "out.wav"
        tts = self._make_tts(audio_bytes=b"\x00\x00" * 160, rate=16000)
        self.v.save_audio(tts, out)
        assert out.exists()
        assert out.stat().st_size > 0
