# Testing Infrastructure — Epic 3 Guide

**Status:** Complete (Task 3.9, 2026-02-19)
**Related Epic:** Epic 3 — Wyoming Protocol Implementation and Validation

---

## Overview

Epic 3 established a full automated testing stack for the Chatterbox Wyoming
services. The stack has two independent layers:

| Layer | What it tests | How it runs |
|---|---|---|
| **Unit tests** | Individual classes (corpus, validator, emulator, runner) | `pytest tests/unit/` — no server needed |
| **Integration tests** | Live Wyoming server via the HAEmulator | `pytest tests/integration/` — spins up an in-process server |

---

## Quick-Start

```bash
# Install the package in editable mode first (one-time)
pip install -e /home/phaedrus/hentown/modules/chatterbox

# Run all tests (unit + integration)
/home/phaedrus/hentown/modules/chatterbox/venv/bin/pytest tests/ -v

# Unit tests only (fast; no model downloads required)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With an alternate STT model (default: tiny)
CHATTERBOX_STT_MODEL=small.en pytest tests/integration/test_whisper_stt.py -v
```

Supported pytest binaries (both work identically):
- `/home/phaedrus/hentown/modules/chatterbox/venv/bin/pytest`
- `/home/phaedrus/hentown/tools/venv/bin/pytest`

---

## Test Corpus

Test WAV files live in `tests/corpus/`. See
[tests/corpus/README.md](../tests/corpus/README.md) for the full catalogue.

**Summary:** 16 WAV files, 22050 Hz, 16-bit mono (Piper TTS output). The
`AudioProcessor` class resamples to 16000 Hz before Wyoming transmission.

| Range | Content | Notes |
|---|---|---|
| test_001–test_006 | Common voice commands | Home control, weather, media, utility |
| test_007–test_008 | Single-word utterances | Edge case: minimal audio |
| test_009–test_015 | Commands and queries | Environment, home automation, compound commands |
| test_016 | ~49-second Gettysburg Address | Long-form transcription stress test |

Corpus metadata is in `tests/corpus/corpus.json`.

---

## Integration Test Architecture

The integration tests in `tests/integration/` do **not** require a separately
running server. Each test module spins up an in-process `WyomingServer` on a
random free port, runs its assertions, and tears it down. This makes them
self-contained and safe to run in CI.

### How the Server Fixture Works

```
@pytest.fixture(scope="module")
async def stt_server():
    port = _free_port()
    server = WyomingServer(host="127.0.0.1", port=port, mode="stt_only", ...)
    task = asyncio.create_task(server.run())
    await _wait_for_port("127.0.0.1", port)   # poll until ready
    yield ("127.0.0.1", port)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
```

Each test then creates an `HAEmulator` pointing at the fixture's host/port.

### async / anyio Notes

Integration tests use `@pytest.mark.anyio` (not `@pytest.mark.asyncio`).
Module-scoped async fixtures use:

```python
@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"
```

`pyproject.toml` sets `asyncio_mode = "strict"` so pytest-asyncio does not
interfere with anyio-managed tests. This was fixed in Task 3.8.1.

---

## Integration Test Modules

### `test_whisper_stt.py` — STT Validation (6 tests)

Validates the Whisper STT service via Wyoming protocol.

| Test | What it checks |
|---|---|
| `test_single_stt_transcription` | Single WAV → correct transcript |
| `test_stt_corpus_accuracy` | All 15 standard corpus entries, WER ≤ 0.30 |
| `test_stt_latency` | Single entry latency < 30 s |
| `test_stt_audio_format` | Server accepts 16 kHz, 16-bit, mono audio |
| `test_stt_empty_audio` | Graceful handling of zero-duration audio |
| `test_stt_long_form` | ~49-second Gettysburg Address; WER ≤ 0.30, latency < 60 s |

Environment variables:
- `CHATTERBOX_STT_MODEL` — Whisper model size (default: `tiny`; production: `small.en`)
- `CHATTERBOX_WER_TOLERANCE` — WER threshold (default: `0.30`)

### `test_piper_tts.py` — TTS Validation (7 tests)

Validates the Piper TTS service via Wyoming protocol.

| Test | What it checks |
|---|---|
| `test_single_tts_synthesis` | Synthesize text → receives audio bytes |
| `test_tts_audio_format` | AudioStart rate/width/channels match spec (22050 Hz, 16-bit, mono) |
| `test_tts_audio_nonempty` | Synthesized PCM is non-empty |
| `test_tts_latency` | Synthesis latency < 30 s |
| `test_tts_empty_text` | Graceful handling of empty string |
| `test_tts_long_text` | Long text (100+ words) synthesized without error |
| `test_tts_special_characters` | Text with punctuation and numbers |

Environment variable:
- `CHATTERBOX_REAL_PIPER=1` — use real ONNX model instead of `_MockPiperVoice`

> **Note:** Without a downloaded Piper ONNX model, TTS returns 3200 bytes of
> silence from `_MockPiperVoice`. Audio quality tests are skipped unless
> `CHATTERBOX_REAL_PIPER=1` is set and a model is present.

### `test_round_trip.py` — Round-Trip Integration (varies)

Validates full STT → TTS round-trip flows. Measures combined latency.

### `test_end_to_end.py` — End-to-End Flows

Full pipeline tests (STT + TTS chained via `HAEmulator.run_full()`).

---

## HAEmulator API

The `HAEmulator` class (`src/ha_emulator/emulator.py`) is the central driver.
It connects to a Wyoming server and runs individual protocol flows.

```python
from ha_emulator.emulator import HAEmulator

async with HAEmulator(host="127.0.0.1", port=10700) as emulator:
    # STT: send WAV file, get transcript
    result = await emulator.run_stt(Path("tests/corpus/test_001_turn_on_lights.wav"))
    print(result.transcript, result.latency_ms)

    # TTS: send text, get PCM audio
    result = await emulator.run_tts("Hello, this is Chatterbox.")
    print(len(result.audio_bytes), result.audio_rate)

    # Full round-trip: WAV → STT → TTS → PCM
    result = await emulator.run_full(Path("tests/corpus/test_002_weather_kansas.wav"))
    print(result.stt.transcript, result.round_trip_ms)
```

### Result Types

```python
@dataclass
class STTResult:
    transcript: str       # Text returned by the server
    latency_ms: float     # ms from AudioStop to Transcript event
    success: bool

@dataclass
class TTSResult:
    audio_bytes: bytes    # Raw PCM received
    audio_rate: int       # From AudioStart (22050 for Piper)
    audio_width: int      # Bytes per sample (2 = 16-bit)
    audio_channels: int   # 1 = mono
    latency_ms: float     # ms from Synthesize to AudioStop
    success: bool

@dataclass
class FullResult:
    stt: STTResult
    tts: TTSResult
    round_trip_ms: float
```

---

## ResultValidator API

The `ResultValidator` class (`src/ha_emulator/validator.py`) validates results.

```python
from ha_emulator.validator import ResultValidator

validator = ResultValidator()

# Validate transcription accuracy (WER-based)
vr = validator.validate_transcript(
    actual="turn on the lights",
    expected="turn on the lights",
    tolerance=0.90,     # ≥90% word accuracy required
)
print(vr.passed, vr.score, vr.details)

# Validate TTS audio integrity
vr = validator.validate_audio(tts_result)
print(vr.passed, vr.details)

# Save received audio to WAV for manual inspection
validator.save_audio(tts_result, Path("/tmp/output.wav"))
```

---

## TestRunner API

The `TestRunner` class (`src/ha_emulator/runner.py`) runs corpus sweeps.

```python
from ha_emulator.runner import TestRunner
from ha_emulator.corpus import CorpusLoader

loader = CorpusLoader(Path("tests/corpus"))
runner = TestRunner(emulator=emulator, loader=loader, validator=ResultValidator())

report = await runner.run_stt_suite()
runner.print_report(report)
runner.save_report(report, Path("results.json"))
```

---

## ha-emulator CLI

The `ha-emulator` command provides a CLI over the same API:

```bash
# Run the full STT corpus against a live server
ha-emulator stt --corpus tests/corpus/ --host localhost --port 10700

# Synthesize a single phrase
ha-emulator tts --text "Hello world" --output /tmp/out.wav --host localhost --port 10700

# Full round-trip corpus sweep
ha-emulator full --corpus tests/corpus/ --host localhost --port 10700

# Test a single WAV file
ha-emulator single-stt tests/corpus/test_001_turn_on_lights.wav \
    --expected "turn on the lights" --host localhost --port 10700
```

Requires a live Chatterbox server. Start one with:

```bash
./scripts/run-server.sh start
./scripts/run-server.sh status
```

---

## Performance Baselines (CPU, Whisper tiny, cached model)

| Scenario | Latency |
|---|---|
| Model load (HuggingFace cache, no download) | ~0.5 s |
| Transcription — 0.5 s audio | ~0.8 s |
| Transcription — 49 s Gettysburg Address (140 words) | ~3.8 s |
| Full round-trip (STT + TTS), single | ~1.1 s |
| Full round-trip (STT + TTS), 3× concurrent | ~2.7 s |

> Per-connection model loading: each TCP connection creates a new
> `WhisperSTTService` that lazy-loads the model. Pre-loading in
> `WyomingServer.run()` validates the model but does not share the instance
> across connections.

---

## Known Issues and Workarounds

### 1. Piper ONNX Model Not Present in Dev Environment

**Symptom:** TTS tests pass but return 3200 bytes of silence.

**Cause:** `_MockPiperVoice` is used when no ONNX model is found.

**Workaround:** Download `en_US-ljspeech-high.onnx` and set
`CHATTERBOX_REAL_PIPER=1` to enable real TTS.

```bash
# Download model (example)
piper --download-dir ~/.local/share/piper --download en_US-ljspeech-high
CHATTERBOX_REAL_PIPER=1 pytest tests/integration/test_piper_tts.py -v
```

---

### 2. VoiceAssistantServer Handles Transcribe Early

**Symptom:** `HAEmulator.run_stt()` against a standalone server returns empty
transcript `""`.

**Cause:** The server handles the leading `Transcribe` event (sent before
audio) immediately on connection, returning an empty result.

**Workaround:** The internal `_run_stt_audio_only()` helper in `emulator.py`
skips the leading `Transcribe` event. Integration tests use this pattern.
The server bug is tracked in `docs/wyoming-protocol.md` Known Gaps.

---

### 3. BrokenPipeError in Test Teardown

**Symptom:** `BrokenPipeError` logged during anyio fixture teardown after
integration tests.

**Cause:** The server's `write_event()` calls are not wrapped in try/except,
so a client disconnecting during teardown causes an unhandled exception.

**Impact:** Teardown error only — tests themselves pass correctly.

**Workaround:** None needed; the test outcome is not affected.

---

## Related Documentation

- [Wyoming Protocol Reference](wyoming-protocol.md) — wire format, event types, conversation flows
- [HA Emulator Architecture](ha-emulator-architecture.md) — component design and data flows
- [Test Corpus README](../tests/corpus/README.md) — WAV file catalogue
- [Testing with Wyoming](testing-wyoming.md) — manual server runner workflow
- [STT/TTS Services](stt_tts_services.md) — Whisper and Piper service details
- [Epic 3 & 4 Project Plan](../dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md)
