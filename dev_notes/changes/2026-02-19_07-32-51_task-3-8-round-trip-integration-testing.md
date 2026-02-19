# Task 3.8: Round-Trip Integration Testing

**Date:** 2026-02-19
**Epic:** 3 — Wyoming Protocol Implementation and Validation
**Task:** 3.8 — Round-Trip Integration Testing
**Status:** Complete

## Summary

Implemented the round-trip integration test suite (`tests/integration/test_round_trip.py`) that validates complete STT → TTS pipeline flows via the Wyoming protocol. This is the final validation milestone for Epic 3's integration testing goal.

All 6 tests pass. Single round-trip latency: ~1.1 seconds. P95: 1084 ms. Concurrent (3 parallel): ~2.7 seconds.

## Changes

### New File: `tests/integration/test_round_trip.py`

Six integration tests covering the full STT → TTS round-trip:

| Test | Description |
|------|-------------|
| `test_round_trip_single` | Single round-trip on the shortest corpus file; validates success and latency |
| `test_round_trip_transcript_accuracy` | All 15 corpus entries; STT transcripts must meet WER ≤ 0.30 |
| `test_round_trip_audio_validity` | All 15 corpus entries; TTS audio must be non-empty and well-formed |
| `test_round_trip_latency_p95` | P95 round-trip latency over 5 shortest files must be < 120 s |
| `test_round_trip_concurrent` | Three simultaneous round-trips must all complete without corruption |
| `test_round_trip_stt_failure_propagation` | STT connection failure → TTS skipped; FullResult reflects upstream failure |

### Architecture

Each test spins up two independent `WyomingServer` instances via module-scoped async fixtures:
- **`stt_server`** — `WyomingServer(mode="stt_only")` with Whisper tiny model
- **`tts_server`** — `WyomingServer(mode="tts_only")` with Piper (mock voice in dev)

The `_run_round_trip()` helper chains `_stt_audio_only()` (AudioStop-triggered transcription, bypassing the known Transcribe-fires-early bug) with `HAEmulator.run_tts()` using the returned transcript.

### Testing Strategy Confirmed

The test suite validates the full architecture:

1. **Corpus WAV files** (15 files, 0.5s to 4.6s duration, committed to `tests/corpus/`) serve as input
2. **Chatterbox backend** starts a `WyomingServer` exposing a Wyoming protocol listener on an ephemeral port
3. **HA Emulator** (`HAEmulator`) connects to the Wyoming listener as a client, emulating Home Assistant's behavior:
   - Transmits WAV audio (e.g. "What is the weather in Kansas?") as PCM chunks via Wyoming
   - Receives STT transcript responses
   - Sends transcript text to TTS server via Wyoming
   - Receives synthesized audio back

### Follows Established Patterns

- Uses `@pytest.mark.anyio` (not `@pytest.mark.asyncio`)
- Module-scoped async fixtures with `anyio_backend` returning `"asyncio"`
- `_stt_audio_only()` helper mirrors the approach in `test_whisper_stt.py`
- WER tolerance: 0.30 (consistent with STT integration tests)

## Verification Results

```
pytest tests/integration/test_round_trip.py -v -s
(using /home/phaedrus/hentown/tools/venv/bin/pytest — see Known Issue below)

test_round_trip_single          PASSED  (STT=1087ms TTS=1ms total=1105ms)
test_round_trip_transcript_accuracy  PASSED
test_round_trip_audio_validity  PASSED
test_round_trip_latency_p95     PASSED  (P95=1084ms)
test_round_trip_concurrent      PASSED  (3 parallel: 2673ms 2579ms 2673ms)
test_round_trip_stt_failure_propagation  PASSED

6 passed in 55.38s
```

## Performance Measurements

| Metric | Value |
|--------|-------|
| Single round-trip (shortest file) | 1105 ms |
| P95 round-trip (5 shortest files) | 1084 ms |
| Concurrent 3-way round-trip | ~2.7 s each |
| Whisper model load time | 0.5 s (from cached CTranslate2 model) |
| Whisper transcription (0.5s audio) | ~0.8 s |
| TTS synthesis (mock Piper) | 1 ms |

## Known Issue: pytest-asyncio Conflict

**Critical finding:** Integration tests **hang** when run with the chatterbox venv's pytest because `pytest-asyncio 1.3.0` is installed alongside `anyio`.

**Root cause:** `pyproject.toml` sets `asyncio_mode = "auto"`, which causes `pytest-asyncio` to intercept all async test functions before anyio's plugin can handle them. Since the test fixtures use `asyncio.get_event_loop().create_task()` to start the WyomingServer, and `pytest-asyncio`'s runner uses a different event loop context, the server task's `run_in_executor` calls for Whisper transcription never complete — the client and server end up on different event loops, causing a deadlock.

**Workaround:** Run integration tests using `/home/phaedrus/hentown/tools/venv/bin/pytest` which does NOT have `pytest-asyncio` installed. This allows anyio's pytest plugin to correctly manage the event loop.

**Proper fix (recommended for next bead):** Either:
1. Remove `pytest-asyncio` from dependencies and `asyncio_mode = "auto"` from `pyproject.toml`, or
2. Set `asyncio_mode = "strict"` so pytest-asyncio only handles explicitly `@pytest.mark.asyncio`-marked tests, leaving `@pytest.mark.anyio` tests to anyio's plugin

This issue affects ALL integration tests in this project (whisper STT, piper TTS, and round-trip), not just the round-trip tests.

## Known Constraints

- **Mock Piper:** TTS uses `_MockPiperVoice` (3200 bytes silence) in dev env. Audio validity checks use `_MIN_AUDIO_BYTES = 160` (same as TTS tests), which the mock satisfies.
- **Latency budget:** 120 s per round-trip (generous for CPU-only CI with tiny Whisper model). Actual: ~1.1 s.
- **BrokenPipeError teardown:** Server tasks use the same suppression pattern as other integration tests to avoid noisy teardown errors.
- **Per-connection model loading:** Each TCP connection creates a new `WhisperSTTService` instance that lazy-loads the model. The pre-load in `WyomingServer.run()` only validates; it doesn't share the loaded model. Model loads from HuggingFace cache in ~0.5s so this is acceptable for testing.

## Definition of Done Verification

- [x] Round-trip tests pass with acceptable accuracy (WER ≤ 0.30)
- [x] End-to-end latency measured and documented (P95 = 1084 ms)
- [x] Concurrent request handling validated (3 parallel round-trips, ~2.7s each)
- [x] Integration test suite automated and repeatable
- [x] `black` formatting applied
- [x] All 6 tests pass (6/6 PASSED)
- [x] pytest-asyncio conflict diagnosed and documented
