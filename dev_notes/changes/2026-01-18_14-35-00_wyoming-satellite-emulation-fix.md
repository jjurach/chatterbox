# Change: Wyoming Satellite Emulation Fix

## Related Project Plan

`dev_notes/project_plans/2026-01-18_14-30-00_wyoming-satellite-emulation-fix.md`

---

## Overview

Fixed the Wyoming test client to properly emulate ESP32 satellite behavior by removing incorrect protocol usage (Transcribe event) and implementing auto-transcription on the server side when AudioStop is received. This resolves "Unhandled event type" protocol errors and enables the full voice assistant pipeline (STT → LLM → TTS) to work correctly.

---

## Files Modified

### 1. wyoming_tester/cli.py

**Lines 79-83**: Removed unused imports
- Removed: `from wyoming.pipeline import RunPipeline, PipelineStage`
- Removed: `Transcribe` from `from wyoming.asr import Transcript, Transcribe`
- Kept: `AudioChunk, AudioStart, AudioStop` and `Transcript` imports

**Lines 109-113**: Removed Transcribe event and updated documentation
- Changed comment from "Connect and run STT workflow" to "Connect and send audio (satellite mode)"
- Added explanation: "Satellite protocol: Send audio events only. Server will automatically transcribe when AudioStop is received."
- Deleted 3 lines that sent Transcribe event
- Deleted log entry for Transcribe event

**Result**: Client now sends only audio events (AudioStart → AudioChunk(s) → AudioStop), matching real ESP32 satellite protocol.

### 2. cackle/adapters/wyoming/server.py

**Lines 138-157**: Enhanced AudioStop handler with auto-transcription logic
- Added mode check: `if self.mode == "full"`
- Calls `_handle_transcribe()` to auto-transcribe buffered audio when in satellite mode
- Writes Transcript event back to client
- Added debug logging for auto-transcription trigger
- Added try/except with error handling
- Clear audio buffer in finally block to prevent double-processing

**Backward Compatibility**:
- "stt_only" mode: No change (waits for explicit Transcribe)
- "combined" mode: No change (waits for explicit Transcribe)
- "full" mode only: Auto-transcription on AudioStop (new behavior)

---

## Impact Assessment

### Positive Impacts
1. **Protocol Compliance**: Client now uses correct Wyoming satellite protocol (audio events only)
2. **Error Resolution**: Eliminates "Unhandled event type: Event" errors
3. **Pipeline Completion**: Enables full STT → LLM → TTS voice assistant flow
4. **Real Device Compatibility**: Test client now accurately emulates ESP32 satellite behavior

### Compatibility
- ✓ Service-mode clients (stt_only, combined) unaffected
- ✓ Explicit Transcribe events still processed (for backward compatibility)
- ✓ Buffer management prevents double-processing
- ✓ Mode-specific logic isolated to "full" mode

### Testing Performed
- Protocol error verification: No "Unhandled event" errors in logs
- End-to-end pipeline: Audio transcribed, LLM response generated, TTS synthesized
- Server mode compatibility: All modes function correctly
- Integration test: chat-demo.sh runs without protocol errors

---

## Implementation Details

### Client Change Logic
The client previously sent events in this order:
```
Transcribe (WRONG - not satellite protocol)
AudioStart
AudioChunk(s)
AudioStop
```

Now correctly sends:
```
AudioStart
AudioChunk(s)
AudioStop
```

### Server Change Logic
When AudioStop is received in "full" mode:
1. Check if mode is "full" (satellite/voice assistant mode)
2. Call auto-transcribe handler on buffered audio
3. If transcription succeeds, send Transcript event to client
4. Transcript triggers existing `_process_transcript()` handler
5. Full pipeline executes: STT → Agent Processing → TTS
6. Buffer cleared to prevent reprocessing

The change leverages existing `_handle_transcribe()` and `_process_transcript()` methods, maintaining code consistency.
