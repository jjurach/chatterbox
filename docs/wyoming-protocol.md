# Wyoming Protocol - Chatterbox Implementation Reference

**Status:** Research Complete (Task 3.1)
**Last Updated:** 2026-02-19
**Related Epic:** Epic 3 - Wyoming Protocol Implementation and Validation

---

## Overview

The Wyoming protocol is Home Assistant's standard for voice satellite communication.
It enables bidirectional streaming of PCM audio and text events between Home
Assistant (or emulated clients) and backend services like Chatterbox.

The protocol runs over TCP and encodes messages as newline-delimited JSON, with
binary payloads (for audio) appended immediately after the JSON line.

---

## Wire Format

Each Wyoming message has two parts:

1. **JSON header line** (terminated by `\n`):

   ```json
   {"type": "audio-chunk", "data": {"rate": 16000, "width": 2, "channels": 1}, "payload_length": 4096}\n
   ```

2. **Binary payload** (optional, `payload_length` bytes appended directly after the `\n`):
   - Present for `audio-chunk` events only
   - Raw PCM bytes, no additional framing

All text fields use UTF-8 encoding. The `payload_length` key in the JSON header
must equal the exact number of binary bytes that follow the newline.

---

## Event Types

### Audio Events (PCM Streaming)

| Event Type | Direction | Description |
|---|---|---|
| `audio-start` | client→server or server→client | Begins an audio stream; carries sample rate, width, and channel metadata |
| `audio-chunk` | client→server or server→client | Carries a slice of raw PCM data in the binary payload |
| `audio-stop` | client→server or server→client | Signals the end of an audio stream |

**AudioStart data fields:**
```json
{"rate": 16000, "width": 2, "channels": 1}
```
- `rate` — samples per second (16000 Hz for STT input; 22050 Hz for TTS output)
- `width` — bytes per sample (2 = 16-bit)
- `channels` — 1 = mono

**AudioChunk data fields:**
```json
{"rate": 16000, "width": 2, "channels": 1}
```
Same metadata as AudioStart, plus the raw PCM bytes as the binary payload.

---

### Speech-to-Text Events

| Event Type | Direction | Description |
|---|---|---|
| `transcribe` | client→server | Request transcription of the buffered audio |
| `transcript` | server→client | Returns the resulting text |

**Transcribe data fields:** (all optional)
```json
{"language": "en"}
```

**Transcript data fields:**
```json
{"text": "what is the weather in kansas", "language": "en"}
```

---

### Text-to-Speech Events

| Event Type | Direction | Description |
|---|---|---|
| `synthesize` | client→server | Request synthesis of the provided text |
| `audio-start` + `audio-chunk` + `audio-stop` | server→client | Synthesized PCM stream streamed back |

**Synthesize data fields:**
```json
{
  "text": "The weather in Kansas is currently 72 degrees.",
  "voice": {"name": "default", "language": "en-US", "speaker": "default"}
}
```

---

## Conversation Flows

### STT-Only Flow

```
Client (HA/emulator)                 Chatterbox (STT service)
─────────────────────                ─────────────────────────
AudioStart (16kHz, 16-bit, mono)  →
AudioChunk (raw PCM bytes)        →  (buffer accumulates)
AudioChunk (raw PCM bytes)        →  (buffer accumulates)
  ...
AudioStop                         →  (auto-triggers Whisper)
                                  ←  Transcript {"text": "..."}
```

When the server receives `AudioStop` in `stt_only` or `full` mode it automatically
invokes the Whisper transcription on the full buffered audio and writes back a
`Transcript` event.

A client may also send an explicit `Transcribe` event after `AudioStop` to trigger
transcription on demand — the server handles both patterns.

---

### TTS-Only Flow

```
Client (HA/emulator)                 Chatterbox (TTS service)
─────────────────────                ─────────────────────────
Synthesize {"text": "..."}        →
                                  ←  AudioStart (22050 Hz, 16-bit, mono)
                                  ←  AudioChunk (raw PCM bytes)
                                  ←  AudioChunk (raw PCM bytes)
                                       ...
                                  ←  AudioStop
```

Piper TTS generates 22050 Hz, 16-bit, mono PCM. The server chunks the audio
into 4096-byte pieces and streams them back with an `AudioStart` / `AudioChunk`*
/ `AudioStop` sequence.

---

### Full Voice Assistant Flow (STT + LLM + TTS)

```
Client (HA/emulator)                 Chatterbox (full mode)
─────────────────────                ─────────────────────────────
AudioStart (16kHz)                →
AudioChunk* (raw PCM)             →  (buffering)
AudioStop                         →  → Whisper transcription
                                  ←  Transcript {"text": "..."}
  [client echoes Transcript back, or server auto-processes]
                                     → LLM agent (Ollama)
                                     → (optional: tool calls)
                                     → Piper TTS synthesis
                                  ←  AudioStart (22050 Hz)
                                  ←  AudioChunk* (raw PCM)
                                  ←  AudioStop
```

In `full` mode the server auto-processes the `Transcript` through the LLM agent
and pipes the response directly to TTS, sending the audio stream back without
waiting for the client to re-send the `Transcript`.

---

### Combined Mode (STT + TTS, No LLM)

Same as Full flow, but the `Transcript` result is not forwarded to an LLM agent.
The client receives the `Transcript` and is responsible for driving the next step.

---

## Server Modes

The Chatterbox server (`chatterbox-server`) supports four modes:

| Mode | STT | LLM | TTS | Use Case |
|---|---|---|---|---|
| `full` | ✓ | ✓ | ✓ | Complete voice assistant |
| `stt_only` | ✓ | — | — | Transcription-only endpoint |
| `tts_only` | — | — | ✓ | Synthesis-only endpoint |
| `combined` | ✓ | ✓ | ✓ | STT + TTS without LLM agent |

Default mode: `full`
Default port: `10700`
Default URI: `tcp://0.0.0.0:10700`

---

## Audio Format Requirements

### STT Input (Chatterbox ← client)

| Parameter | Value |
|---|---|
| Sample rate | 16000 Hz |
| Bit depth | 16-bit signed (S16_LE) |
| Channels | 1 (mono) |
| Encoding | Raw PCM, little-endian |

Whisper (`faster-whisper`) receives raw PCM bytes and resamples as needed.

### TTS Output (Chatterbox → client)

| Parameter | Value |
|---|---|
| Sample rate | 22050 Hz |
| Bit depth | 16-bit signed |
| Channels | 1 (mono) |
| Encoding | Raw PCM, little-endian |

Piper generates 22050 Hz by default. An `AudioStart` with the correct metadata
always precedes the audio stream so the client can set up its decoder.

---

## Current Implementation Status

### Working

- `wyoming>=1.8.0` installed; `AsyncServer`, `AsyncEventHandler` in use
- STT via `faster-whisper` — audio buffering, Whisper transcription, `Transcript` response
- TTS via `piper-tts` — `Synthesize` event received, PCM stream returned
- Four server modes (`full`, `stt_only`, `tts_only`, `combined`)
- `wyoming_tester` CLI for push-to-talk testing with WAV files

### Known Gaps (as of 2026-02-19)

| Gap | Location | Notes |
|---|---|---|
| TTS returns mock audio | `src/chatterbox/services/tts.py` | `PiperTTSService.synthesize()` returns `b'\x00' * 160` placeholder; `MockPiperVoice` bypasses ONNX model loading |
| No `wyoming-satellite` package | — | Project uses custom TCP client (`wyoming_tester`) instead of official satellite |
| No Wyoming assist/handle pipeline | — | LLM response handled internally; no `wyoming.handle` or `RunPipeline` usage |
| `RunPipeline` imported but unused | `src/wyoming_tester/protocol.py:13` | Dead import; no pipeline stage integration |

---

## Protocol Assumptions and Validation Notes

The following protocol behaviors have been confirmed from code inspection:

1. **Audio buffering on server** — The server buffers all `AudioChunk` payloads
   between `AudioStart` and `AudioStop`. Transcription happens on the complete
   buffer, not on streaming chunks.

2. **Event serialization** — Both specific Wyoming types (`AudioChunk`) and generic
   `Event` objects with a `type` attribute are handled. The server checks `isinstance`
   first, then falls back to `event.type` string comparison.

3. **Chunk size for TTS output** — Server sends TTS audio in 4096-byte chunks.
   Clients should expect multiple `AudioChunk` events between `AudioStart` and
   `AudioStop`.

4. **No protocol handshake** — There is no initial handshake or capability
   negotiation. The first event from either side begins the interaction.

5. **Connection per request** — Each TCP connection handles one conversation.
   The `AsyncServer` creates a new `VoiceAssistantServer` handler per connection.

---

## Dependencies

| Package | Version | Role |
|---|---|---|
| `wyoming` | `>=1.8.0` | Protocol types, AsyncServer, event I/O |
| `faster-whisper` | `>=0.10.0` | STT backend |
| `piper-tts` | `>=1.2.0` | TTS backend |
| `pydub` | `>=0.25.1` | WAV file handling in `wyoming_tester` |

---

## Test Infrastructure

### wyoming-tester CLI

```bash
# Send a WAV file and print transcript + response
wyoming-tester --uri tcp://localhost:10700 --file test_audio.wav

# Verbose protocol logging
wyoming-tester --uri tcp://localhost:10700 --file test.wav --verbose
```

Source: `src/wyoming_tester/`

### Server Runner

```bash
./scripts/run-server.sh start
./scripts/run-server.sh status
./scripts/run-server.sh stop
```

Logs to `tmp/chatterbox-server.log`.

---

## Related Documentation

- [Testing Infrastructure](testing-infrastructure.md) — Automated test suite, HAEmulator API, known issues
- [HA Emulator Architecture](ha-emulator-architecture.md) — Emulator component design and data flows
- [Testing with Wyoming](testing-wyoming.md) — Manual server runner + wyoming-tester workflow
- [Architecture](architecture.md) — System component overview
- [STT/TTS Services](stt_tts_services.md) — Whisper and Piper service details
- [Adapters](adapters.md) — Wyoming adapter design

---

## Epic 3 Status (as of 2026-02-19)

All Epic 3 Wyoming protocol tasks are **complete**. The following work was
done after the initial research phase:

| Task | Deliverable |
|---|---|
| 3.2 | `docs/ha-emulator-architecture.md` — emulator design |
| 3.3 | 16 WAV files in `tests/corpus/` + `corpus.json` |
| 3.4 | `src/ha_emulator/` — HAEmulator, corpus, CLI |
| 3.5 | `src/ha_emulator/validator.py`, `runner.py` + unit tests |
| 3.6 | `tests/integration/test_whisper_stt.py` — 6 integration tests |
| 3.7 | `tests/integration/test_piper_tts.py` — 7 integration tests |
| 3.8 | `tests/integration/test_round_trip.py`, `test_end_to_end.py` |
| 3.8.1 | `asyncio_mode = "strict"` fix; long-form STT test (Gettysburg Address) |
| 3.9 | `docs/testing-infrastructure.md`, corpus README update (this document) |

See [Testing Infrastructure](testing-infrastructure.md) for how to run the
test suite and interpret results.
