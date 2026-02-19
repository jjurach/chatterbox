"""ha-emulator CLI — drive Chatterbox Wyoming services from the command line."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .corpus import CorpusLoader
from .emulator import HAEmulator
from .runner import TestRunner
from .validator import ResultValidator


def _build_parser() -> argparse.ArgumentParser:
    default_host = os.environ.get("CHATTERBOX_HOST", "localhost")
    default_port = int(os.environ.get("CHATTERBOX_PORT", "10700"))

    parser = argparse.ArgumentParser(
        prog="ha-emulator",
        description="Home Assistant Emulator — Wyoming protocol test harness",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Shared connection options
    conn = argparse.ArgumentParser(add_help=False)
    conn.add_argument(
        "--host",
        default=default_host,
        help=f"Server host (default: {default_host})",
    )
    conn.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"Server port (default: {default_port})",
    )
    conn.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-operation timeout in seconds (default: 30.0)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ---- stt suite -------------------------------------------------------
    p_stt = sub.add_parser(
        "stt",
        parents=[conn],
        help="Run STT suite against a corpus directory",
    )
    p_stt.add_argument(
        "--corpus",
        type=Path,
        default=Path("tests/corpus"),
        help="Path to corpus directory (default: tests/corpus)",
    )
    p_stt.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Save JSON report to this path",
    )

    # ---- tts -------------------------------------------------------------
    p_tts = sub.add_parser(
        "tts",
        parents=[conn],
        help="Send text through TTS and optionally save audio",
    )
    p_tts.add_argument("text", help="Text to synthesize")
    p_tts.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Save synthesized audio to this WAV file",
    )

    # ---- full suite ------------------------------------------------------
    p_full = sub.add_parser(
        "full",
        parents=[conn],
        help="Run full STT+TTS round-trip suite",
    )
    p_full.add_argument(
        "--corpus",
        type=Path,
        default=Path("tests/corpus"),
        help="Path to corpus directory (default: tests/corpus)",
    )
    p_full.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Save JSON report to this path",
    )

    # ---- single-stt ------------------------------------------------------
    p_single = sub.add_parser(
        "single-stt",
        parents=[conn],
        help="Transcribe a single WAV file",
    )
    p_single.add_argument("wav_file", type=Path, help="WAV file to transcribe")
    p_single.add_argument(
        "--expected",
        default=None,
        help="Expected transcript for validation",
    )

    return parser


async def _run_stt(args) -> int:
    emulator = HAEmulator(args.host, args.port, timeout=args.timeout)
    loader = CorpusLoader(args.corpus)
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    report = await runner.run_stt_suite()
    runner.print_report(report)

    if args.report:
        runner.save_report(report, args.report)

    return 0 if report.failed == 0 else 1


async def _run_tts(args) -> int:
    emulator = HAEmulator(args.host, args.port, timeout=args.timeout)
    result = await emulator.run_tts(args.text, output_wav=args.output)

    if result.success:
        print(f"TTS OK — {len(result.audio_bytes)} bytes, {result.latency_ms:.0f} ms")
        if args.output:
            print(f"Saved to {args.output}")
        return 0
    else:
        print(f"TTS FAILED — {result.error}", file=sys.stderr)
        return 1


async def _run_full(args) -> int:
    emulator = HAEmulator(args.host, args.port, timeout=args.timeout)
    loader = CorpusLoader(args.corpus)
    validator = ResultValidator()
    runner = TestRunner(emulator, loader, validator)

    report = await runner.run_full_suite()
    runner.print_report(report)

    if args.report:
        runner.save_report(report, args.report)

    return 0 if report.failed == 0 else 1


async def _run_single_stt(args) -> int:
    emulator = HAEmulator(args.host, args.port, timeout=args.timeout)
    result = await emulator.run_stt(args.wav_file)

    if not result.success:
        print(f"STT FAILED — {result.error}", file=sys.stderr)
        return 1

    print(f"Transcript : {result.transcript}")
    print(f"Latency    : {result.latency_ms:.0f} ms")

    if args.expected is not None:
        validator = ResultValidator()
        vr = validator.validate_transcript(result.transcript, args.expected)
        status = "PASS" if vr.passed else "FAIL"
        print(f"Validation : [{status}]  {vr.details}")
        return 0 if vr.passed else 1

    return 0


def main() -> None:
    """Entry point for the ha-emulator CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    handlers = {
        "stt": _run_stt,
        "tts": _run_tts,
        "full": _run_full,
        "single-stt": _run_single_stt,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = asyncio.run(handler(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
