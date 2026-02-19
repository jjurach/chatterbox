"""TestRunner — iterates the corpus, aggregates results, and reports."""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .corpus import CorpusLoader
from .emulator import HAEmulator
from .validator import ResultValidator

logger = logging.getLogger(__name__)


@dataclass
class EntryReport:
    """Result for a single corpus entry."""

    file: str
    expected: str
    actual: str
    passed: bool
    wer: float
    latency_ms: float
    error: Optional[str] = None


@dataclass
class TestReport:
    """Aggregated results for a full test suite run."""

    total: int
    passed: int
    failed: int
    skipped: int
    entries: List[EntryReport]
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TestRunner:
    """Runs corpus entries through the emulator and aggregates results.

    Usage::

        emulator = HAEmulator("localhost", 10700)
        loader = CorpusLoader(Path("tests/corpus"))
        validator = ResultValidator()
        runner = TestRunner(emulator, loader, validator)
        report = asyncio.run(runner.run_stt_suite())
        runner.print_report(report)
    """

    def __init__(
        self,
        emulator: HAEmulator,
        loader: CorpusLoader,
        validator: ResultValidator,
    ) -> None:
        self.emulator = emulator
        self.loader = loader
        self.validator = validator

    # ------------------------------------------------------------------
    # Suite runners
    # ------------------------------------------------------------------

    async def run_stt_suite(self) -> TestReport:
        """Run all corpus entries through STT and validate transcripts."""
        entries = self.loader.load_all()
        reports: List[EntryReport] = []

        for entry in entries:
            logger.info("STT: %s", entry.wav_path.name)
            result = await self.emulator.run_stt(entry.wav_path)

            if not result.success:
                reports.append(
                    EntryReport(
                        file=entry.wav_path.name,
                        expected=entry.expected_text,
                        actual="",
                        passed=False,
                        wer=1.0,
                        latency_ms=result.latency_ms,
                        error=result.error,
                    )
                )
                continue

            vr = self.validator.validate_transcript(
                result.transcript, entry.expected_text
            )
            reports.append(
                EntryReport(
                    file=entry.wav_path.name,
                    expected=entry.expected_text,
                    actual=result.transcript,
                    passed=vr.passed,
                    wer=round(1.0 - vr.score, 4),
                    latency_ms=result.latency_ms,
                )
            )

        return _build_report(reports)

    async def run_tts_suite(self, texts: List[str]) -> TestReport:
        """Run a list of texts through TTS and validate audio streams."""
        reports: List[EntryReport] = []

        for text in texts:
            logger.info("TTS: %r", text[:60])
            result = await self.emulator.run_tts(text)

            if not result.success:
                reports.append(
                    EntryReport(
                        file="",
                        expected=text,
                        actual="",
                        passed=False,
                        wer=0.0,
                        latency_ms=result.latency_ms,
                        error=result.error,
                    )
                )
                continue

            vr = self.validator.validate_audio(result)
            reports.append(
                EntryReport(
                    file="",
                    expected=text,
                    actual=f"{len(result.audio_bytes)} bytes",
                    passed=vr.passed,
                    wer=0.0,
                    latency_ms=result.latency_ms,
                    error=None if vr.passed else vr.details,
                )
            )

        return _build_report(reports)

    async def run_full_suite(self) -> TestReport:
        """Run full STT+TTS round-trip for each corpus entry."""
        entries = self.loader.load_all()
        reports: List[EntryReport] = []

        for entry in entries:
            logger.info("Full: %s", entry.wav_path.name)
            result = await self.emulator.run_full(entry.wav_path)

            stt_ok = result.stt.success
            tts_ok = result.tts.success
            passed = stt_ok and tts_ok

            vr = None
            if stt_ok:
                vr = self.validator.validate_transcript(
                    result.stt.transcript, entry.expected_text
                )
                passed = passed and vr.passed

            error_parts = []
            if result.stt.error:
                error_parts.append(f"STT: {result.stt.error}")
            if result.tts.error:
                error_parts.append(f"TTS: {result.tts.error}")

            reports.append(
                EntryReport(
                    file=entry.wav_path.name,
                    expected=entry.expected_text,
                    actual=result.stt.transcript,
                    passed=passed,
                    wer=round(1.0 - vr.score, 4) if vr else 1.0,
                    latency_ms=result.round_trip_ms,
                    error="; ".join(error_parts) or None,
                )
            )

        return _build_report(reports)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self, report: TestReport) -> None:
        """Print a human-readable summary to stdout."""
        print(
            f"\n{'='*60}\n"
            f"Test Report — {report.generated_at}\n"
            f"{'='*60}"
        )
        print(
            f"  Total   : {report.total}\n"
            f"  Passed  : {report.passed}\n"
            f"  Failed  : {report.failed}\n"
            f"  Skipped : {report.skipped}\n"
            f"  Latency : avg={report.avg_latency_ms:.0f}ms  "
            f"min={report.min_latency_ms:.0f}ms  max={report.max_latency_ms:.0f}ms"
        )
        print(f"\n{'─'*60}")
        for e in report.entries:
            status = "PASS" if e.passed else "FAIL"
            label = e.file or "(tts)"
            print(f"  [{status}]  {label}")
            if not e.passed:
                if e.error:
                    print(f"          error    : {e.error}")
                else:
                    print(f"          expected : {e.expected}")
                    print(f"          actual   : {e.actual}")
                    print(f"          WER      : {e.wer:.3f}")
        print(f"{'='*60}\n")

    def save_report(self, report: TestReport, output_path: Path) -> None:
        """Save the report as JSON for automated processing."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(report), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Report saved to %s", output_path)


# ------------------------------------------------------------------
# Internal helper
# ------------------------------------------------------------------


def _build_report(reports: List[EntryReport]) -> TestReport:
    latencies = [r.latency_ms for r in reports if r.latency_ms > 0]
    return TestReport(
        total=len(reports),
        passed=sum(1 for r in reports if r.passed),
        failed=sum(1 for r in reports if not r.passed),
        skipped=0,
        entries=reports,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        min_latency_ms=min(latencies) if latencies else 0.0,
        max_latency_ms=max(latencies) if latencies else 0.0,
    )
