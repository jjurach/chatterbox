# Task 3.6: Validate Whisper STT Service — Project Plan

**Status:** Completed
**Created:** 2026-02-19
**Epic:** 3 — Wyoming Protocol Implementation and Validation
**Depends On:** Tasks 3.1–3.5 (all complete)

---

## Overview

Use the existing HAEmulator and TestRunner infrastructure to validate that the Chatterbox Whisper STT service correctly handles Wyoming protocol PCM streams and returns accurate transcripts.

This task delivers:
- A pytest integration test module (`tests/integration/test_whisper_stt.py`) that spins up a real `WyomingServer` in `stt_only` mode in-process and runs the full corpus through it.
- Coverage of: happy-path transcription accuracy, empty-audio edge case, connection-failure error handling, and latency measurement.
- A change log entry with real verification output.

---

## Scope

### In Scope
1. **Integration test fixture** — Start a real `WyomingServer(mode="stt_only")` on a free ephemeral port; tear it down after each test session.
2. **Corpus-wide STT accuracy test** — Run all 15 corpus WAV files through the live server; assert >90% word accuracy per entry.
3. **Latency measurement** — Assert each transcription completes within 30 s (generous, to handle CI CPU-only inference).
4. **Edge cases** — Empty audio, very short audio (single frame), connection-refused behavior.
5. **Pytest markers** — Mark integration tests with `@pytest.mark.integration` so they are skippable in unit-only CI.
6. **Change documentation** — Timestamped entry in `dev_notes/changes/`.

### Out of Scope
- TTS validation (Task 3.7).
- Round-trip testing (Task 3.8).
- Performance tuning (not a goal here; just measure).
- Live hardware / actual Home Assistant device testing.

---

## Implementation Steps

### Step 1 — Integration test module skeleton
Create `tests/integration/test_whisper_stt.py` with:
- `pytest.ini` marker `integration` registered (add to `pyproject.toml`).
- Module-scoped async fixture `whisper_server` that:
  1. Finds a free TCP port.
  2. Instantiates `WyomingServer(host="127.0.0.1", port=<free>, mode="stt_only", stt_model="tiny")`.
  3. Starts it as a background asyncio task.
  4. Yields `(host, port)`.
  5. Cancels the task on teardown.
- A helper fixture `emulator` that constructs `HAEmulator(host, port, timeout=60.0)`.

### Step 2 — Corpus accuracy tests
```
test_stt_corpus_accuracy
```
- Load corpus via `CorpusLoader(Path("tests/corpus"))`.
- Run `emulator.run_stt(entry.wav_path)` for each entry.
- Validate with `ResultValidator().validate_transcript(...)`.
- Assert `result.success is True`.
- Assert `vr.passed` (WER ≤ 0.10, i.e., ≥90% word accuracy).
- Assert `result.latency_ms < 30_000` (30 s).
- Report all failures together (use `pytest.fail` with accumulated messages, don't short-circuit on first failure).

### Step 3 — Edge-case tests
```
test_stt_empty_audio       — send 0-byte PCM; service must return success=True, transcript=""
test_stt_single_frame      — send 2-byte PCM (1 frame); service must not crash
test_stt_connection_refused — connect to a port with no listener; assert success=False
```

### Step 4 — Latency snapshot test
```
test_stt_latency_p95
```
- Run a subset of 5 shortest corpus files.
- Compute P95 latency.
- Assert P95 < 30_000 ms (no hard cap; just measure and log).

### Step 5 — Register pytest marker
Add to `pyproject.toml` `[tool.pytest.ini_options]`:
```
markers = ["integration: requires live Wyoming server (slow)"]
```

### Step 6 — Run tests and capture output
```bash
CHATTERBOX_STT_MODEL=tiny \
  /home/phaedrus/hentown/tools/venv/bin/pytest \
  tests/integration/test_whisper_stt.py -v --timeout=120
```

### Step 7 — Change documentation
Create `dev_notes/changes/2026-02-19_05-44-53_task-3-6-whisper-stt-validation.md`.

---

## Files Changed

| File | Action |
|------|--------|
| `tests/integration/test_whisper_stt.py` | **Create** |
| `pyproject.toml` | **Edit** — add `integration` marker |
| `dev_notes/changes/2026-02-19_05-44-53_task-3-6-whisper-stt-validation.md` | **Create** |

---

## Definition of Done

- [x] `tests/integration/test_whisper_stt.py` created with all four test functions.
- [x] `integration` marker registered in `pyproject.toml`.
- [x] Tests run against real Whisper server (model=tiny).
- [x] Verification output (command + snippet) in change log.
- [x] Plan status set to `Completed`.
- [x] Change log entry created.
- [x] Project plan updated to mark Task 3.6 as Completed.

---

## Risks / Notes

- **Whisper model download**: First run will download `tiny` model (~75 MB). Subsequent runs use cache.
- **CPU inference latency**: `tiny` model on CPU is fast enough for test purposes.
- **WER threshold**: The 90% threshold applies per entry. Some very short utterances ("yes", "no") may not hit 90% but the overall suite should.
- **Server startup race**: The fixture must wait until the port is accepting connections before yielding. Use a retry loop with `asyncio.open_connection`.
