# Home Assistant Conversation Flow

**Status:** Research Complete (Task 4.1)
**Last Updated:** 2026-02-20
**Related Epic:** Epic 4 — LLM Integration with Tool Calling

---

## Overview

This document captures how Home Assistant (HA) handles voice conversations internally,
clarifies the role of Wyoming protocol vs. Conversation Agents, and establishes the
architectural decision for where Chatterbox's LLM integration fits.

---

## HA Voice Pipeline Architecture

The HA Assist pipeline runs four sequential stages:

```
[ Wake Word Detection ]       ← Wyoming service (e.g. openWakeWord)
         ↓
[ Speech-to-Text (STT) ]      ← Wyoming service (e.g. Whisper / Speech-to-Phrase)
         ↓  (transcribed text)
[ Conversation Agent ]        ← HA integration (NOT a Wyoming service)
         ↓  (response text)
[ Text-to-Speech (TTS) ]      ← Wyoming service (e.g. Piper)
         ↓
[ Audio Output / Satellite ]
```

**Critical insight:** The Conversation Agent is **not** a Wyoming protocol service.
Wyoming is used only for STT, TTS, and wake word detection. The conversation/LLM
layer is a separate HA integration concept (`ConversationEntity`).

---

## The Conversation Agent Layer

Home Assistant's Conversation Agent is an abstraction that takes text input and
returns text output. It can be:

1. **Built-in HA (default)** — rule-based intent/string matching. Handles commands
   like "turn on the lights" locally and very quickly. Does not call any LLM.

2. **LLM-based agents** — integrations that subclass `ConversationEntity` and call
   an external LLM (OpenAI, Google, Ollama, etc.). HA ships with built-in integrations
   for these providers. Custom integrations can implement the same interface.

3. **Hybrid ("prefer handling locally")** — HA first tries the built-in intent
   engine; only falls back to an LLM if it cannot recognize the command. This is
   the recommended setting for most HA users.

### Custom Conversation Agent API

A custom HA integration can register any backend as a Conversation Agent by
subclassing `ConversationEntity` and implementing `_async_handle_message`. The
method receives a `ConversationInput` (containing the transcribed text and
conversation history) and returns a `ConversationResult` with the response text.

The pipeline then feeds that response text to the TTS stage.

---

## Integration Pattern Options for Chatterbox

### Pattern A — Custom HA Conversation Agent (Integration Plugin)

Chatterbox ships a custom HA integration that registers itself as a `ConversationEntity`.

```
Wyoming STT (Whisper) → [HA Pipeline] → Chatterbox ConversationEntity
                                              ↓
                                     LLM + Tool Calling
                                     (internal to Chatterbox)
                                              ↓
                                   [HA Pipeline] → Wyoming TTS (Piper)
```

**Pros:**
- "Correct" HA integration pattern — appears in HA UI alongside OpenAI/Ollama
- Supports HA's hybrid mode (local intents first, LLM fallback)
- Conversation history managed by HA pipeline
- Can access HA LLM API helper to expose HA device control to the LLM

**Cons:**
- Requires publishing a custom HA integration (Python package + manifest)
- Tied to HA's integration lifecycle (restarts, config flow, etc.)
- Harder to test in isolation without a running HA instance

---

### Pattern B — LLM at the Wyoming Satellite Level

The Wyoming satellite (Box 3B) intercepts audio, runs STT locally, passes text to
Chatterbox's LLM, synthesizes TTS locally, and returns audio — all without HA ever
seeing the text. HA only sees the final audio output.

```
[Box 3B Satellite]
   Wake Word → local STT → Chatterbox LLM → local TTS → audio playback
                                  ↑
                          (optional: HA REST API for device control)
```

**Pros:**
- No HA integration needed — fully self-contained
- Easy to develop and test independently of HA
- Low latency (no round-trip through HA for text processing)
- Can still call HA REST API for device control if needed

**Cons:**
- Bypasses HA's Assist pipeline visibility
- HA cannot surface voice history in its UI
- Requires satellite firmware modification
- Device control via HA REST API is more work than using the LLM API helper

---

### Pattern C — Chatterbox as a Combined Wyoming Service

A single Chatterbox Wyoming endpoint handles the full STT → LLM → TTS pipeline
internally. HA sees it as a STT-only service and sends audio; Chatterbox responds
with synthesized audio. HA never knows about the intermediate LLM step.

```
HA → Wyoming (audio) → Chatterbox {STT → LLM → TTS} → Wyoming (audio) → HA
```

This is effectively a hybrid of Pattern A and B — the Wyoming protocol carries
the audio frames, but the LLM logic lives entirely inside Chatterbox.

**Note:** This requires careful Wyoming protocol handling — the server must
intercept at the right point in the STT protocol flow to inject LLM processing
before returning the TTS audio.

---

## Architectural Decision

**Recommended approach for Epic 4: Pattern A (Custom HA Conversation Agent)**

Rationale:

1. **Correct integration point** — HA's pipeline was explicitly designed for this.
   Patterns B/C work around it rather than with it.

2. **Device control access** — The HA LLM API helper exposes all HA intents
   (lights, switches, sensors, automations) to the LLM as tools automatically.
   Replicating this externally is significant engineering effort.

3. **HA UI visibility** — Conversation history, pipeline stats, and agent selection
   all work natively.

4. **Simpler Wyoming layer** — Whisper STT and Piper TTS remain as-is. Only the
   conversation agent changes.

5. **Testable in isolation** — We can test the `ConversationEntity` with mocked
   HA context before integrating with hardware.

**Implementation path:**

```
Task 4.2: Design the ConversationEntity subclass + LLM client architecture
Task 4.3: Implement the core agentic loop (state machine)
Task 4.4: Implement weather and time/date tools
Task 4.5: Wire the ConversationEntity to the agentic loop
Task 4.6: LLM integration with system prompts and tool definitions
Task 4.7: Wyoming remains unchanged (STT/TTS only)
```

**If full satellite independence is desired later**, Pattern B can be layered on top
by having the satellite call Chatterbox's HTTP API directly, with the HA
ConversationEntity as a thin proxy.

---

## Wyoming Protocol Scope (Unchanged)

Wyoming continues to handle only:

| Service | Wyoming Role |
|---|---|
| Wake word detection | Wake word events (DetectActivation) |
| Whisper STT | AudioChunk → Transcript |
| Piper TTS | Synthesize text → AudioChunk stream |

The conversation/LLM step uses HA's internal conversation API, **not Wyoming**.

---

## HA Pipeline Event Flow (Technical Detail)

When a voice command is spoken:

1. HA sends `stt-start` over WebSocket, begins streaming `audio-chunk` binary frames
2. Whisper (Wyoming) receives audio, transcribes it, returns `Transcript` event
3. HA emits `stt-end` with `{"text": "what is the weather in Kansas"}` on the WebSocket
4. HA calls `conversation.process` on the configured Conversation Agent
5. Conversation Agent (Chatterbox) invokes LLM with tools, runs agentic loop,
   returns response text `{"speech": {"plain": {"speech": "It is 72°F and sunny."}}}`
6. HA emits `intent-end` then calls Piper TTS with the response text
7. Piper (Wyoming) synthesizes audio, streams it back to HA
8. HA plays audio on the satellite

---

## References

- [Home Assistant Wyoming Integration](https://www.home-assistant.io/integrations/wyoming/)
- [Assist Pipelines Developer Docs](https://developers.home-assistant.io/docs/voice/pipelines/)
- [Conversation Entity Developer Docs](https://developers.home-assistant.io/docs/core/conversation/custom_agent/)
- [HA LLM API for Integrations](https://developers.home-assistant.io/docs/core/llm/)
- [AI Agents for the Smart Home (HA Blog)](https://www.home-assistant.io/blog/2024/06/07/ai-agents-for-the-smart-home/)
- [FutureProofHomes wyoming-enhancements](https://github.com/FutureProofHomes/wyoming-enhancements)
  (reference for Pattern B satellite-level LLM integration)

---

**Document Version:** 1.0
**Author:** Research via Claude Code (Task 4.1)
