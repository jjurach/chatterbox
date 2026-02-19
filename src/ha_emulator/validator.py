"""Result validator — checks STT transcripts and TTS audio streams."""

import logging
import re
import string
import wave
import io
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .emulator import TTSResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Outcome of a single validation check."""

    passed: bool
    score: float  # 0.0–1.0  (accuracy for STT, format-check for TTS)
    details: str  # Human-readable reason


def _normalize(text: str) -> list:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _wer(reference: list, hypothesis: list) -> float:
    """Compute word-error rate via Wagner–Fischer DP.

    WER = (S + D + I) / len(reference)
    """
    r, h = reference, hypothesis
    n, m = len(r), len(h)

    if n == 0:
        return 0.0 if m == 0 else 1.0

    # DP table  (n+1) × (m+1)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, m + 1):
            if r[i - 1] == h[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j - 1], prev[j], dp[j - 1])
    return dp[m] / n


class ResultValidator:
    """Validates STT transcriptions and TTS audio streams."""

    DEFAULT_WER_THRESHOLD = 0.10  # ≤10 % WER → pass

    def validate_transcript(
        self,
        actual: str,
        expected: str,
        tolerance: float = DEFAULT_WER_THRESHOLD,
    ) -> ValidationResult:
        """Check word-error rate between *actual* and *expected* transcript.

        Args:
            actual: Transcript returned by the STT service.
            expected: Ground-truth text from the corpus.
            tolerance: Maximum acceptable WER (default 0.10 → 90 % accuracy).

        Returns:
            ValidationResult with ``passed``, ``score`` (1 - WER), and
            human-readable ``details``.
        """
        ref_tokens = _normalize(expected)
        hyp_tokens = _normalize(actual)

        wer = _wer(ref_tokens, hyp_tokens)
        score = max(0.0, 1.0 - wer)
        passed = wer <= tolerance

        details = (
            f"WER={wer:.3f} (threshold={tolerance:.2f})  "
            f"expected='{expected}'  actual='{actual}'"
        )
        logger.debug("Transcript validation: %s", details)
        return ValidationResult(passed=passed, score=score, details=details)

    def validate_audio(self, result: "TTSResult") -> ValidationResult:
        """Check that the TTS audio stream is non-empty and has valid format.

        Args:
            result: TTSResult returned by HAEmulator.run_tts().

        Returns:
            ValidationResult indicating whether audio is well-formed.
        """
        if not result.audio_bytes:
            return ValidationResult(
                passed=False,
                score=0.0,
                details="No audio bytes received",
            )

        checks = []
        ok = True

        if len(result.audio_bytes) < 160:
            ok = False
            checks.append(f"audio too short ({len(result.audio_bytes)} bytes)")
        else:
            checks.append(f"audio_bytes={len(result.audio_bytes)}")

        if result.audio_rate <= 0:
            ok = False
            checks.append(f"invalid rate={result.audio_rate}")
        else:
            checks.append(f"rate={result.audio_rate}")

        if result.audio_width not in (1, 2, 3, 4):
            ok = False
            checks.append(f"invalid width={result.audio_width}")
        else:
            checks.append(f"width={result.audio_width}")

        if result.audio_channels not in (1, 2):
            ok = False
            checks.append(f"invalid channels={result.audio_channels}")
        else:
            checks.append(f"channels={result.audio_channels}")

        score = 1.0 if ok else 0.0
        details = "  ".join(checks)
        logger.debug("Audio validation: passed=%s  %s", ok, details)
        return ValidationResult(passed=ok, score=score, details=details)

    def save_audio(self, result: "TTSResult", output_path: Path) -> None:
        """Write received PCM bytes to a WAV file.

        Args:
            result: TTSResult containing audio_bytes and format metadata.
            output_path: Destination WAV file path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(result.audio_channels)
            wf.setsampwidth(result.audio_width)
            wf.setframerate(result.audio_rate)
            wf.writeframes(result.audio_bytes)
        logger.info("Saved TTS audio to %s (%d bytes)", output_path, len(result.audio_bytes))
