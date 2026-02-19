# Home Assistant Emulator — Architecture Design

**Status:** Design Complete (Task 3.2)
**Last Updated:** 2026-02-19
**Related Epic:** Epic 3 - Wyoming Protocol Implementation and Validation
**Related Plan:** dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md

---

## Overview

The Home Assistant (HA) Emulator is a Python test harness that drives the
Chatterbox Wyoming services the same way Home Assistant would in production.
Its purpose is to validate STT, TTS, and end-to-end conversation flows without
requiring a live Home Assistant instance.

### Design Principles

1. **Build on what exists** — The emulator extends the existing `wyoming_tester`
   infrastructure (`WyomingClient`, `AudioProcessor`) rather than reimplementing it.
2. **Separation of concerns** — Wave loading, protocol communication, validation,
   and reporting are distinct layers.
3. **Async-first** — All protocol I/O uses `asyncio` (consistent with the rest of
   the codebase), but the public test-runner API may also expose a sync wrapper.
4. **Self-contained** — No external dependencies beyond what is already in
   `requirements.txt` (`wyoming>=1.8.0`, `pydub`, `wave`, `asyncio`).

---

## Relationship to Existing Code

```
src/
├── wyoming_tester/          # EXISTING — keep as-is; used by emulator
│   ├── protocol.py          # WyomingClient (sync TCP client)
│   ├── audio.py             # AudioProcessor (load, convert, chunk)
│   └── cli.py               # wyoming-tester CLI (push-to-talk)
│
└── ha_emulator/             # NEW — Task 3.4 will create this package
    ├── __init__.py
    ├── emulator.py          # HAEmulator: orchestrates STT / TTS / full flows
    ├── corpus.py            # CorpusLoader: loads wave files + expected text
    ├── validator.py         # ResultValidator: text accuracy, audio integrity
    ├── runner.py            # TestRunner: runs corpus, aggregates results
    └── cli.py               # ha-emulator CLI entry point
```

The `WyomingClient` in `wyoming_tester/protocol.py` will be used directly by
`HAEmulator` for transport. `AudioProcessor` in `wyoming_tester/audio.py` will
be used for WAV loading and PCM reconstruction.

---

## Component Design

### 1. `HAEmulator` (`emulator.py`)

The central orchestrator. Wraps `WyomingClient` and exposes high-level test
methods for each conversation mode.

```python
class HAEmulator:
    """Emulates Home Assistant interactions with a Wyoming service."""

    def __init__(self, host: str, port: int, timeout: float = 30.0):
        ...

    async def run_stt(self, wav_path: Path) -> STTResult:
        """Send WAV file via Wyoming STT flow; return transcript + latency."""

    async def run_tts(self, text: str, output_wav: Optional[Path] = None) -> TTSResult:
        """Send text via Wyoming TTS flow; return audio bytes + latency."""

    async def run_full(self, wav_path: Path, output_wav: Optional[Path] = None) -> FullResult:
        """Run complete STT + TTS round-trip; return transcript + audio + latencies."""
```

**Protocol flows implemented by `HAEmulator`:**

| Method | Events sent | Events expected |
|---|---|---|
| `run_stt` | `AudioStart` + `AudioChunk`* + `AudioStop` | `Transcript` |
| `run_tts` | `Synthesize` | `AudioStart` + `AudioChunk`* + `AudioStop` |
| `run_full` | STT sequence | `Transcript`, then TTS sequence |

**Result dataclasses** (returned by each method):

```python
@dataclass
class STTResult:
    transcript: str           # Text returned by server
    latency_ms: float         # ms from AudioStop to Transcript
    success: bool

@dataclass
class TTSResult:
    audio_bytes: bytes        # Raw PCM received
    audio_rate: int           # Sample rate from AudioStart
    audio_width: int          # Bit depth from AudioStart
    audio_channels: int
    latency_ms: float         # ms from Synthesize to AudioStop
    success: bool

@dataclass
class FullResult:
    stt: STTResult
    tts: TTSResult
    round_trip_ms: float
```

---

### 2. `CorpusLoader` (`corpus.py`)

Loads wave files and their expected transcriptions from the test corpus
directory (`tests/corpus/`).

```
tests/corpus/
├── corpus.json              # Metadata: filename → expected transcription
├── test_001_turn_on_lights.wav
├── test_002_weather_kansas.wav
├── ...
└── test_015_short_yes.wav
```

```python
@dataclass
class CorpusEntry:
    wav_path: Path
    expected_text: str        # Expected transcription
    description: str          # Human-readable label

class CorpusLoader:
    def __init__(self, corpus_dir: Path): ...

    def load_all(self) -> list[CorpusEntry]:
        """Return all entries sorted by filename."""

    def load_entry(self, name: str) -> CorpusEntry:
        """Load a single entry by filename stem."""
```

**`corpus.json` format:**

```json
[
  {
    "file": "test_001_turn_on_lights.wav",
    "expected": "turn on the lights",
    "description": "Simple home control command"
  },
  {
    "file": "test_002_weather_kansas.wav",
    "expected": "what is the weather in kansas",
    "description": "Weather query"
  }
]
```

---

### 3. `ResultValidator` (`validator.py`)

Validates STT and TTS results against expectations.

```python
class ResultValidator:
    """Validates STT transcriptions and TTS audio streams."""

    def validate_transcript(
        self,
        actual: str,
        expected: str,
        tolerance: float = 0.9,
    ) -> ValidationResult:
        """
        Check word-error rate. Returns pass/fail + WER score.
        Uses simple token comparison (no external ASR library required).
        """

    def validate_audio(self, result: TTSResult) -> ValidationResult:
        """
        Check that received audio is non-empty and has correct format
        (rate, width, channels match expectations).
        Can optionally save PCM to a WAV file for manual listening.
        """

    def save_audio(self, result: TTSResult, output_path: Path) -> None:
        """Write received PCM bytes to a WAV file."""

@dataclass
class ValidationResult:
    passed: bool
    score: float              # 0.0–1.0 (WER for STT, format check for TTS)
    details: str              # Human-readable reason
```

**Word-error rate (WER) implementation:**

Use a simple token-based comparison:
```
WER = (substitutions + insertions + deletions) / len(reference_tokens)
```
No external library required. Normalize both strings (lowercase, strip
punctuation) before comparison.

---

### 4. `TestRunner` (`runner.py`)

Iterates over the corpus, runs each entry through the emulator, validates
results, and aggregates a report.

```python
@dataclass
class TestReport:
    total: int
    passed: int
    failed: int
    skipped: int
    entries: list[EntryReport]
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    generated_at: str         # ISO timestamp

@dataclass
class EntryReport:
    file: str
    expected: str
    actual: str
    passed: bool
    wer: float
    latency_ms: float
    error: Optional[str]

class TestRunner:
    def __init__(
        self,
        emulator: HAEmulator,
        loader: CorpusLoader,
        validator: ResultValidator,
    ): ...

    async def run_stt_suite(self) -> TestReport:
        """Run all corpus entries through STT; validate transcriptions."""

    async def run_tts_suite(self, texts: list[str]) -> TestReport:
        """Run list of texts through TTS; validate audio streams."""

    async def run_full_suite(self) -> TestReport:
        """Run full STT+TTS round-trip for each corpus entry."""

    def print_report(self, report: TestReport) -> None:
        """Print human-readable summary to stdout."""

    def save_report(self, report: TestReport, output_path: Path) -> None:
        """Save report as JSON for automated processing."""
```

---

### 5. `cli.py` — `ha-emulator` command

```
ha-emulator stt --corpus tests/corpus/ --host localhost --port 10700
ha-emulator tts --text "Hello world" --output /tmp/out.wav --host localhost --port 10700
ha-emulator full --corpus tests/corpus/ --host localhost --port 10700
ha-emulator single-stt tests/corpus/test_001.wav --expected "turn on the lights"
```

---

## Data Flow Diagrams

### STT Validation Flow

```
CorpusLoader
    │  (wav_path, expected_text)
    ▼
HAEmulator.run_stt(wav_path)
    │
    ├─ AudioProcessor.load_and_convert(wav_path)  → PCM bytes
    ├─ WyomingClient.connect(host, port)
    ├─ send AudioStart
    ├─ send AudioChunk × N
    ├─ send AudioStop
    ├─ receive Transcript
    └─ return STTResult(transcript, latency_ms)
    │
    ▼
ResultValidator.validate_transcript(actual, expected)
    │  (ValidationResult: passed, wer, details)
    ▼
TestReport (entry added)
```

### TTS Validation Flow

```
HAEmulator.run_tts(text)
    │
    ├─ WyomingClient.connect(host, port)
    ├─ send Synthesize(text)
    ├─ receive AudioStart
    ├─ receive AudioChunk × N  (buffer bytes)
    ├─ receive AudioStop
    └─ return TTSResult(audio_bytes, rate, width, channels, latency_ms)
    │
    ▼
ResultValidator.validate_audio(result)
    │  (ValidationResult: passed, score, details)
    ├─ [optional] save_audio(result, output_wav)
    ▼
TestReport (entry added)
```

### Full Round-Trip Flow

```
CorpusLoader → (wav_path, expected_text)
    │
    ▼
HAEmulator.run_full(wav_path)
    │
    ├─ run_stt(wav_path) → STTResult(transcript)
    │
    ├─ run_tts(transcript) → TTSResult(audio_bytes)
    │
    └─ return FullResult(stt, tts, round_trip_ms)
    │
    ▼
Validate both STT transcript and TTS audio integrity
```

---

## Reuse vs. New Code

| Component | Action | Rationale |
|---|---|---|
| `wyoming_tester.WyomingClient` | **Reuse as-is** | Already implements the Wyoming TCP protocol correctly |
| `wyoming_tester.AudioProcessor` | **Reuse as-is** | Already handles WAV loading and PCM conversion |
| `wyoming_tester.cli` (`wyoming-tester`) | **Keep unchanged** | Useful interactive push-to-talk tool; emulator is its automated counterpart |
| `chatterbox.adapters.wyoming.client` | **Evaluate** | Async alternative to `WyomingClient`; may be used for the async API in `HAEmulator` |
| `ha_emulator.*` | **New — Task 3.4** | The test harness, validation, and reporting layers |

**Decision on sync vs. async client:**

`WyomingClient` (`wyoming_tester/protocol.py`) uses synchronous sockets.
`chatterbox.adapters.wyoming.client` (`src/chatterbox/adapters/wyoming/client.py`)
uses `asyncio.StreamReader/Writer`.

`HAEmulator` will use the **async client** (`asyncio.open_connection`) to be
consistent with the rest of the async codebase and to enable future concurrent
test execution. The sync `WyomingClient` remains available for manual testing via
`wyoming-tester`.

---

## Testing Strategy

### Unit Tests

| Module | What to test |
|---|---|
| `corpus.py` | `CorpusLoader.load_all()` returns correct entries; handles missing JSON gracefully |
| `validator.py` | WER calculation correctness; audio validation edge cases (empty bytes, wrong rate) |
| `emulator.py` | Protocol flow (mock server); timeout handling; connection errors |
| `runner.py` | Report aggregation; pass/fail counting; JSON serialization |

All unit tests use `pytest` with mocked Wyoming server connections
(`unittest.mock.patch` on `asyncio.open_connection`).

### Integration Tests

Run against a live Chatterbox server (manual or CI):
```bash
./scripts/run-server.sh start
pytest tests/integration/test_ha_emulator.py -v
./scripts/run-server.sh stop
```

---

## Directory Layout (post-Task 3.4)

```
src/
└── ha_emulator/
    ├── __init__.py
    ├── emulator.py
    ├── corpus.py
    ├── validator.py
    ├── runner.py
    └── cli.py

tests/
├── corpus/
│   ├── corpus.json
│   ├── test_001_turn_on_lights.wav
│   └── ...
├── unit/
│   ├── test_corpus.py
│   ├── test_validator.py
│   ├── test_emulator.py
│   └── test_runner.py
└── integration/
    └── test_ha_emulator.py
```

---

## Known Constraints and Decisions

1. **No `wyoming-satellite` package** — The project uses a custom TCP client.
   The emulator follows the same approach and does not depend on the external
   `wyoming-satellite` package.

2. **TTS mock blocker** — `PiperTTSService.synthesize()` currently returns
   `b'\x00' * 160` (mock). TTS validation (Task 3.7) and round-trip testing
   (Task 3.8) cannot succeed until this is fixed. This is noted in the
   `wyoming-protocol.md` Known Issues section and must be resolved before or
   during Task 3.4/3.7.

3. **One connection per test** — Following the existing protocol behavior
   (one TCP connection per conversation), the emulator opens a new connection
   for each corpus entry. Connection pooling is out of scope for Epic 3.

4. **No GUI** — The emulator is a CLI-only tool. Reporting is stdout + JSON file.

5. **WER tolerance** — Default acceptance threshold is WER ≤ 0.10 (≥90% word
   accuracy), matching the Epic 3 acceptance criterion. This is configurable.

---

## Related Documentation

- [Wyoming Protocol Reference](wyoming-protocol.md)
- [Testing with Wyoming](testing-wyoming.md)
- [Architecture](architecture.md)
- [Epic 3 & 4 Project Plan](../dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md)
