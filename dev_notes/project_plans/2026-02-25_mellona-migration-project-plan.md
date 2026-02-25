# Chatterbox → Mellona Migration Project Plan

**Status:** Planned (not started)
**Created:** 2026-02-25
**Depends On:** Mellona STT/TTS feature additions (hentown beads, see below)

## Overview

This project replaces all direct STT and TTS service code in chatterbox with calls to
mellona, the Cackle ecosystem's unified AI provider library. It also routes chatterbox's
LLM configuration (Ollama) through mellona's config system.

After this migration, chatterbox will contain no direct usage of:
- `faster-whisper` Python library
- `piper-tts` Python library
- Hard-coded Ollama connection parameters

All of these will be configured and managed by mellona.

## Prerequisites: Mellona Must Implement First

**This migration cannot begin until mellona has STT and TTS provider support.**
The required mellona work is tracked in the top-level hentown beads system:

| Hentown Bead | Description |
|---|---|
| `hentown-bg0` | Add FasterWhisper STT provider to mellona |
| `hentown-ze0` | Add Piper TTS provider to mellona |
| `hentown-nl6` | Add named STT/TTS profiles to mellona config system |
| `hentown-84n` | Add `--config-file` global flag to mellona CLI |
| `hentown-deb` | Add `mellona transcribe` CLI command |
| `hentown-ayd` | Add `mellona synthesize` CLI command |
| `hentown-akm` | Add STT/TTS provider documentation to mellona docs |
| `hentown-4fs` | Write mellona STT/TTS integration guide for calling applications |

Once those are complete, begin this plan from Task 1.

## Mellona Reference Documentation

Once mellona adds STT/TTS support, copy the relevant docs into this project:
- `chatterbox/docs/mellona-stt-tts-integration.md` (from mellona integration guide)
- `chatterbox/docs/mellona-provider-reference.md` (STT/TTS sections)
- `chatterbox/docs/mellona-migration-notes.md` (chatterbox-specific notes)

See chatterbox bead `chatterbox-65y` for details.

## Architecture: Before and After

### Before (current)
```
chatterbox config (Pydantic BaseSettings)
    ↓
WhisperSTTService (faster-whisper directly)
PiperTTSService (piper-tts directly)
VoiceAssistantAgent (LangChain → ChatOpenAI → Ollama URL from Settings)
```

### After (target)
```
mellona config (YAML, env-var substitution)
    ↓ mellona Python API
chatterbox server
  STT: mellona.get_stt_provider('default') → FasterWhisperProvider
  TTS: mellona.get_tts_provider('default') → PiperTTSProvider
  LLM: mellona profile config → LangChain ChatOpenAI(base_url=..., model=...)
```

### Key Design Decisions

- **LangChain stays in chatterbox.** mellona does not replace LangChain as the agent
  framework. mellona provides config and provider access; LangChain handles ReAct agent
  loops, tool calling, and ConversationBufferWindowMemory.

- **PCM bytes ↔ file path conversion.** mellona's STT takes a file path; chatterbox's
  Wyoming server works with raw PCM bytes. The migration must write PCM to a temp WAV
  file, call mellona, then clean up. A utility function in chatterbox should handle this.

- **Audio format compatibility.** Mellona's Piper provider will return WAV or PCM bytes.
  Verify the format matches what chatterbox's Wyoming server expects
  (22050Hz, 16-bit mono PCM for Piper; 16kHz for Whisper input).

- **Single mellona config file.** Chatterbox will use one mellona config file, located
  at a path configurable via `CHATTERBOX_MELLONA_CONFIG` env var or the Settings class.
  Default suggestion: `~/.config/mellona/config.yaml` (shared with other tools) or
  a chatterbox-specific `~/.config/chatterbox/mellona.yaml`.

## Beaded Task Plan

All tasks below are tracked in chatterbox's beads system.
Run `bd ready` in the chatterbox directory to see available work.

### Task 1: Add mellona as chatterbox dependency
**Bead:** `chatterbox-cxg` | **Priority:** P0

Add mellona to `pyproject.toml`. Since mellona is a local submodule (not on PyPI),
configure as an editable path dependency. Verify `import mellona` works in chatterbox's venv.

Also install `aiohttp` (mellona's undeclared dependency).

**Acceptance criteria:**
- [ ] `mellona` in `pyproject.toml` dependencies
- [ ] `python -c 'import mellona'` succeeds in chatterbox venv
- [ ] No import errors at server startup

---

### Task 2: Create mellona config for chatterbox integration
**Bead:** `chatterbox-e8y` | **Priority:** P1 | **Blocked by:** Task 1

Create the mellona YAML config that chatterbox will use, mapping chatterbox's env vars
to mellona provider settings. Add a `mellona_config_path` setting to chatterbox's
`Settings` class.

**Mellona config template:**
```yaml
providers:
  faster_whisper:
    model: ${CHATTERBOX_STT_MODEL}      # default: base
    device: ${CHATTERBOX_STT_DEVICE}    # default: cpu
  piper:
    voice: ${CHATTERBOX_TTS_VOICE}      # default: en_US-lessac-medium
  ollama:
    base_url: ${CHATTERBOX_OLLAMA_BASE_URL}  # default: http://localhost:11434/v1

stt_profiles:
  default:
    provider: faster_whisper

tts_profiles:
  default:
    provider: piper

profiles:
  default:
    provider: ollama
    model: ${CHATTERBOX_OLLAMA_MODEL}         # default: llama3.1:8b
    temperature: ${CHATTERBOX_OLLAMA_TEMPERATURE}  # default: 0.7
```

**Acceptance criteria:**
- [ ] Config template created and documented
- [ ] `CHATTERBOX_MELLONA_CONFIG` env var respected in Settings
- [ ] MellonaConfig loads correctly from chatterbox code

---

### Task 3: Replace WhisperSTTService with mellona STT
**Bead:** `chatterbox-f1p` | **Priority:** P1 | **Blocked by:** Task 2

Replace `WhisperSTTService` in all chatterbox server components with mellona STT calls.

**Files to modify:**
- `src/chatterbox/services/stt.py` — gut or replace implementation
- `src/chatterbox/adapters/wyoming/server.py` — update STT call sites
- `src/chatterbox/adapters/rest/api.py` — update `/stt` and `/stt/file` endpoints

**Key implementation note:** Write PCM bytes to a temp WAV file before calling mellona:
```python
import tempfile, wave, os
from mellona import get_stt_provider
from mellona.types import STTRequest

async def transcribe_pcm(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp_path = f.name
    try:
        with wave.open(tmp_path, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_bytes)
        provider = await get_stt_provider('default')
        response = await provider.transcribe(STTRequest(audio_file_path=tmp_path))
        return response.text
    finally:
        os.unlink(tmp_path)
```

**Acceptance criteria:**
- [ ] `WhisperSTTService` no longer used by server or REST API
- [ ] STT works via mellona in wyoming server
- [ ] `/stt` and `/stt/file` REST endpoints work via mellona
- [ ] Tests updated

---

### Task 4: Replace PiperTTSService with mellona TTS
**Bead:** `chatterbox-tey` | **Priority:** P1 | **Blocked by:** Task 2

Replace `PiperTTSService` in all chatterbox server components with mellona TTS calls.

**Files to modify:**
- `src/chatterbox/services/tts.py` — gut or replace implementation
- `src/chatterbox/adapters/wyoming/server.py` — update TTS/Synthesize event handler
- `src/chatterbox/adapters/rest/api.py` — update `/tts` endpoint
- `src/chatterbox/tools/registry.py` — update `TTSTool` if it calls PiperTTSService

**Key implementation note:**
```python
from mellona import get_tts_provider
from mellona.types import TTSRequest

async def synthesize_speech(text: str) -> bytes:
    provider = await get_tts_provider('default')
    response = await provider.synthesize(TTSRequest(text=text, output_format='pcm'))
    return response.audio_data
```

Verify audio format compatibility with Wyoming protocol expectations.

**Acceptance criteria:**
- [ ] `PiperTTSService` and `_MockPiperVoice` no longer used
- [ ] TTS works via mellona in Wyoming Synthesize handler
- [ ] `/tts` REST endpoint works via mellona
- [ ] Tests updated

---

### Task 5: Update VoiceAssistantAgent to use mellona config for Ollama
**Bead:** `chatterbox-44u` | **Priority:** P1 | **Blocked by:** Task 2

Read Ollama connection config from mellona profile instead of chatterbox Settings.
Keep LangChain as the agent framework — only change where config values come from.

```python
# src/chatterbox/agent.py
from mellona import MellonaConfig

mellona_config = MellonaConfig(...)  # uses chatterbox's configured mellona config path
profile = mellona_config.get_profile('default')

self.llm = ChatOpenAI(
    base_url=profile.metadata.get('base_url', 'http://localhost:11434/v1'),
    api_key='ollama',
    model=profile.model,
    temperature=profile.temperature,
)
```

**Acceptance criteria:**
- [ ] Agent reads Ollama URL/model/temp from mellona profile
- [ ] No direct Ollama settings in chatterbox Settings class
- [ ] Agent works correctly in full-mode server test

---

### Task 6: Update ha-emulator for mellona migration
**Bead:** `chatterbox-wav` | **Priority:** P1 | **Blocked by:** Tasks 3 & 4

Review and update `src/ha_emulator/` for consistency with the mellona migration.
If ha-emulator calls STT/TTS services directly, replace with mellona calls.
If it uses the REST API, verify it still works against the updated server.

**Acceptance criteria:**
- [ ] ha-emulator has no direct faster-whisper or piper-tts calls
- [ ] `ha-emulator run-stt-chat-tts test.wav` succeeds against migrated server

---

### Task 7: Update wyoming-tester for mellona migration
**Bead:** `chatterbox-092` | **Priority:** P1 | **Blocked by:** Tasks 3 & 4

Review and update `src/wyoming_tester/` for consistency with the mellona migration.
Verify it works correctly against the updated chatterbox Wyoming server.

**Acceptance criteria:**
- [ ] wyoming-tester has no direct faster-whisper or piper-tts calls
- [ ] `wyoming-tester --file test.wav` succeeds against migrated server

---

### Task 8: Remove deprecated STT/TTS code
**Bead:** `chatterbox-a4w` | **Priority:** P1 | **Blocked by:** Tasks 3–7

After all callers are migrated, remove the deprecated chatterbox-specific service code
and their dependencies.

**Remove from pyproject.toml:**
- `faster-whisper`
- `piper-tts`
- `scipy` (if not used elsewhere)

**Remove from Settings:**
- `stt_model`, `stt_device`, `stt_language`, `whisper_cache_dir`
- `tts_voice`, `tts_sample_rate`, `piper_cache_dir`

**Remove CLI args from main.py:**
- `--whisper-model`, `--whisper-cache-dir`, `--whisper-device`
- `--piper-voice`, `--piper-cache-dir`

**Acceptance criteria:**
- [ ] No imports of `faster_whisper` or `piper` in chatterbox source
- [ ] `pip install -e .` succeeds without piper-tts or faster-whisper
- [ ] All tests pass

---

### Task 9: Validate server startup
**Bead:** `chatterbox-mja` | **Priority:** P0 | **Blocked by:** Task 8

Verify the migrated chatterbox server starts and operates correctly.

**Test commands:**
```bash
# Using a test mellona config file (not personal config)
export CHATTERBOX_MELLONA_CONFIG=/tmp/chatterbox-test-mellona.yaml

# Full mode
chatterbox serve --mode full --debug --verbose

# REST API health check
curl http://localhost:8080/health

# STT via REST
curl -X POST http://localhost:8080/stt -F 'file=@tests/fixtures/audio/test.wav'

# TTS via REST
curl -X POST http://localhost:8080/tts -d '{"text": "Hello world"}'
```

**Acceptance criteria:**
- [ ] Server starts without errors
- [ ] No references to old WhisperSTTService/PiperTTSService in logs
- [ ] Health endpoint returns `{"stt": true, "tts": true}`
- [ ] STT REST endpoint transcribes audio correctly
- [ ] TTS REST endpoint synthesizes audio correctly

---

### Task 10: ha-emulator end-to-end validation
**Bead:** `chatterbox-p1n` | **Priority:** P0 | **Blocked by:** Task 9

Run comprehensive ha-emulator tests against the migrated server.

**Test procedure:**
```bash
# At least 5 different audio files
for wav in tests/fixtures/audio/*.wav; do
    ha-emulator run-stt-chat-tts "$wav"
done
```

**Acceptance criteria:**
- [ ] All 5+ test inputs produce valid transcripts
- [ ] LLM responses are sensible (not empty)
- [ ] TTS output is valid audio for each test
- [ ] End-to-end latency documented
- [ ] No server crashes during test run

---

### Task 11: wyoming-tester end-to-end validation
**Bead:** `chatterbox-w5r` | **Priority:** P0 | **Blocked by:** Task 9

Run wyoming-tester against the migrated server to validate Wyoming protocol compatibility.

**Test procedure:**
```bash
# Start server in full mode
chatterbox serve --mode full &

# Text test
chatterbox-wyoming-client "What time is it?"

# Audio tests
for wav in tests/fixtures/audio/*.wav; do
    wyoming-tester --uri tcp://localhost:10700 --file "$wav"
done
```

**Acceptance criteria:**
- [ ] Wyoming protocol connection established
- [ ] Audio input transcribed correctly
- [ ] TTS audio response received
- [ ] No protocol errors in server logs
- [ ] Round-trip latency documented

---

### Task 12: Copy mellona docs into chatterbox
**Bead:** `chatterbox-65y` | **Priority:** P2 | **Blocked by:** Task 8

Copy mellona STT/TTS integration docs into `chatterbox/docs/` so agents working in
this submodule have full mellona API reference without needing to read mellona source.

**Acceptance criteria:**
- [ ] `docs/mellona-stt-tts-integration.md` created
- [ ] `docs/mellona-migration-notes.md` created (chatterbox-specific patterns and gotchas)
- [ ] `docs/README.md` updated to reference new docs

---

## Testing Philosophy

Emphasis on re-testing throughout this migration:

1. **After each task** (not just at the end): verify that previously-working functionality
   still works. Don't wait until Task 8 to discover a regression introduced in Task 3.

2. **Use real audio files** from `tests/fixtures/audio/` for all STT and pipeline tests.
   The fixtures corpus must include at least 5 varied utterances.

3. **Use a dedicated mellona test config** — never use `~/.config/mellona/config.yaml`
   for automated tests. Use `CHATTERBOX_MELLONA_CONFIG=/path/to/test-config.yaml`.

4. **Document latency baselines** at each testing task so regressions are detectable.

5. **Test all server modes**: `full`, `stt_only`, `tts_only`, `combined` — not just `full`.

## Definition of Done

This migration is complete when:
- [ ] All 12 tasks above are closed in chatterbox beads
- [ ] No `faster-whisper` or `piper-tts` in `pyproject.toml`
- [ ] No `WhisperSTTService` or `PiperTTSService` classes in chatterbox source
- [ ] `chatterbox serve --mode full` starts successfully with mellona
- [ ] ha-emulator round-trip tests pass for 5+ inputs
- [ ] wyoming-tester round-trip tests pass for 5+ inputs
- [ ] mellona docs copied into chatterbox/docs/
