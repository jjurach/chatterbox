# Whisper Streaming Model - Architecture & Data Flow

## Overview

This document describes the current batch processing model for Whisper STT integration in Chatterbox. This model uses Wyoming protocol to buffer audio until transcription is requested, then sends the complete buffer to Whisper for processing.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ESP32 Device (Satellite)                    │
│                                                                      │
│  Microphone → Audio Capture → PCM Stream at 16kHz, 16-bit, Mono    │
└────────────────────────────────┬──────────────────────────────────┘
                                 │ Wyoming Protocol
                    ┌────────────▼────────────┐
                    │  AudioStart Event       │ (Start capturing)
                    │  - rate: 16000          │
                    │  - width: 2 (16-bit)    │
                    │  - channels: 1 (Mono)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼──────────────────────┐
                    │  AudioChunk Events (Multiple)     │
                    │  - audio: 2048-3200 bytes PCM     │
                    │  - Arrives in ~100ms intervals    │
                    │  - Each chunk extends buffer      │
                    └────────────┬──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  AudioStop Event        │ (End capturing)
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────▼────────────────────────┐
        │  VoiceAssistantServer.handle_event()            │
        │  (Auto-transcribe on AudioStop in full mode)    │
        └────────────────────────┬───────────────────────┘
                                 │
        ┌────────────────────────▼────────────────────────┐
        │  _handle_transcribe()                           │
        │  1. Get buffer contents (all PCM data)          │
        │  2. Call WhisperSTTService.transcribe()         │
        │  3. Clear buffer                                │
        │  4. Return Transcript event                     │
        └────────────────────────┬───────────────────────┘
                                 │
        ┌────────────────────────▼────────────────────────┐
        │  WhisperSTTService.transcribe()                 │
        │  1. Convert bytes to numpy float32              │
        │  2. Normalize audio [-1, 1]                     │
        │  3. Call faster-whisper model                   │
        │  4. Extract text + confidence                   │
        │  5. Return results dictionary                   │
        └────────────────────────┬───────────────────────┘
                                 │
        ┌────────────────────────▼────────────────────────┐
        │  Transcript Event sent to client                │
        │  - text: "What is the weather?"                 │
        │  - confidence: 0.95                             │
        └────────────────────────┬───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  _process_transcript()  │
                    │  1. Send to LLM agent   │
                    │  2. Get response text   │
                    │  3. Generate TTS        │
                    │  4. Send Synthesize     │
                    └─────────────────────────┘
```

---

## Data Flow State Machine

```
                          ┌─────────────────┐
                          │    IDLE/READY   │
                          │                 │
                          │ Buffer empty    │
                          │ Listening       │
                          └────────┬────────┘
                                   │
                      AudioStart received
                                   │
                          ┌────────▼────────┐
                          │   BUFFERING     │
                          │                 │
                          │ Buffer active   │
                          │ Collecting PCM  │
                          └────────┬────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
         AudioChunk received         AudioStop received
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                          ┌────────▼─────────┐
                          │ TRANSCRIBING     │
                          │                  │
                          │ Buffer sent to   │
                          │ Whisper          │
                          │ Processing...    │
                          └────────┬─────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
              Success case              Error case
                    │                             │
         ┌──────────▼───────────┐    ┌──────────▼──────────┐
         │ PROCESSING RESULT    │    │  ERROR/RECOVERY     │
         │                      │    │                     │
         │ Send Transcript      │    │ Log error, clear    │
         │ Process via LLM      │    │ buffer, return to   │
         │ Generate TTS         │    │ IDLE                │
         │ Send to client       │    │                     │
         └──────────┬───────────┘    └─────────┬───────────┘
                    │                          │
                    └──────────┬───────────────┘
                               │
                          ┌────▼──────┐
                          │   IDLE    │
                          │ Ready for │
                          │ next      │
                          │ utterance │
                          └───────────┘
```

---

## Current Implementation Details

### Audio Buffer
**Location:** `cackle/adapters/wyoming/server.py:76`
```python
self.audio_buffer = bytearray()  # Initialized on connection
```

**Lifecycle:**
1. Created: When connection established
2. Cleared: When AudioStart received
3. Extended: Each AudioChunk received
4. Consumed: When AudioStop → _handle_transcribe called
5. Cleared: After Whisper returns results

### Audio Format Specification
**Wyoming Protocol Standard:**
```
Sample Rate:     16000 Hz
Bit Depth:       16-bit signed (S16_LE)
Channels:        1 (Mono)
Byte Order:      Little Endian
```

**PCM Data Layout:**
- Each audio sample: 2 bytes (16-bit)
- Samples per second: 16,000
- Bytes per second: 32,000
- Typical chunk: 3200 bytes = 100ms of audio
- Maximum buffer: 480,000 bytes = 30 seconds (Whisper limit)

### Event Sequence for Single Utterance

**Satellite sends:**
```
1. AudioStart(rate=16000, width=2, channels=1)
2. AudioChunk(audio=<2048-3200 bytes>) × N chunks
3. AudioStop()
```

**Server processes:**
```python
# On AudioStart:
self.audio_buffer.clear()  # line 125

# On each AudioChunk:
self.audio_buffer.extend(event.audio)  # line 135

# On AudioStop (full mode):
if self.mode == "full":
    # Auto-transcribe (from recent fix)
    response_event = await self._handle_transcribe(Transcribe())
    await self.write_event(response_event)  # Send Transcript back
```

**Server's _handle_transcribe method:**
```python
# 1. Get all buffered audio
audio_bytes = bytes(self.audio_buffer)

# 2. Send to Whisper
result = await self.stt_service.transcribe(audio_bytes)

# 3. Clear buffer for next utterance
self.audio_buffer.clear()

# 4. Return Transcript event
return Transcript(
    text=result["text"],
    confidence=result.get("confidence", 0.0)
)
```

**Whisper Processing:**
```python
# In WhisperSTTService.transcribe():

# 1. Convert PCM bytes to float32 array
audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

# 2. Normalize to [-1, 1] range
audio_array /= 32768.0

# 3. Run Whisper model
segments, info = self.model.transcribe(audio_array)

# 4. Extract results
text = "".join(segment.text for segment in segments)
avg_confidence = mean([segment.confidence for segment in segments])

# 5. Return dictionary
return {
    "text": text,
    "language": info.language,
    "confidence": avg_confidence,
}
```

---

## Performance Characteristics

### Latency Analysis
```
Device Audio Capture:    Variable (user speaks)
Network Transmission:    ~100ms per chunk (3200 bytes)
Buffer Accumulation:     0-3000ms (depends on speech length)
Whisper Processing:      500-2000ms (depends on audio length)
LLM Response:            ~1000-3000ms (depends on query)
TTS Synthesis:           1000-5000ms (depends on response length)
─────────────────────────────────────────────────────
Total E2E Latency:       ~2.6-13s per utterance
```

### Memory Usage
```
Audio buffer (30s max):   480 KB
Whisper model (base):     140-300 MB (loaded once)
numpy arrays:             ~2 MB (temporary during transcription)
─────────────────────────────────────────────
Typical session:          ~150 MB
Multiple connections:     Add ~500 KB per connection
```

### CPU Usage
```
Idle:                     < 1%
Buffering audio:          < 5%
Whisper transcription:    20-40% (depends on model size)
During LLM + TTS:         15-60% (varies)
```

---

## Error Handling (Current)

**Limited error handling:**
```python
# In _handle_transcribe:
try:
    if not self.stt_service:
        logger.error("STT service not available")
        return None

    if not self.audio_buffer:
        logger.warning("No audio data")
        return Transcript(text="", confidence=0.0)

    result = await self.stt_service.transcribe(bytes(self.audio_buffer))
    self.audio_buffer.clear()

    return Transcript(text=result["text"], confidence=result.get("confidence", 0.0))

except Exception as e:
    logger.error(f"Error transcribing: {e}", exc_info=True)
    return Transcript(text="", confidence=0.0)
```

**Issues with current error handling:**
- No distinction between error types (timeout, OOM, invalid audio)
- No retry logic
- Buffer not cleared on exception
- Limited logging context
- No metrics collected

---

## Batch Processing Model Constraints

### Design Assumptions
1. **Single utterance per session:** Audio captured for one complete utterance, then transcribed
2. **Complete buffer required:** All audio must arrive before transcription
3. **No streaming:** Cannot transcribe partial audio
4. **Fixed max length:** 30 seconds (Whisper limitation)
5. **Post-speech waiting:** Cannot transcribe until AudioStop or explicit Transcribe

### Advantages
✓ Simple implementation
✓ No VAD (Voice Activity Detection) required
✓ Complete audio = best transcription quality
✓ Works well with push-to-talk
✓ Minimal dependencies

### Disadvantages
✗ Higher latency (must wait for complete utterance)
✗ Cannot handle streaming use cases
✗ Single utterance per session (if using automatic AudioStop)
✗ No real-time feedback to user
✗ Not suitable for continuous listening

---

## Integration Points

### Connections to Other Components
1. **Wyoming Protocol Layer**
   - Receives: AudioStart, AudioChunk, AudioStop events
   - Sends: Transcript event back to client

2. **Whisper STT Service**
   - Calls: `await stt_service.transcribe(audio_bytes)`
   - Receives: Dictionary with text, language, confidence

3. **Voice Assistant Agent**
   - Receives: Transcript text
   - Processes: LLM query
   - Returns: Response text

4. **TTS Service**
   - Receives: Response text from agent
   - Returns: Audio chunks
   - Sends: Synthesize event to client

---

## Future Enhancement Paths

### Path 1: VAD-Based Streaming (Approach B)
- Add Silero VAD for silence detection
- Auto-transcribe on silence (not requiring AudioStop)
- Multi-utterance in single session
- Reduced latency (~500-1000ms)

### Path 2: Streaming Whisper (Approach C)
- Research Whisper streaming APIs
- Implement chunk-by-chunk transcription
- Real-time transcription feedback
- Complex implementation

### Path 3: Hybrid Mode
- Support both batch and VAD modes
- Mode selection via configuration
- Graceful fallback mechanisms

---

## References

- **Wyoming Protocol:** https://github.com/rhasspy/wyoming
- **Faster-Whisper:** https://github.com/guillaumekln/faster-whisper
- **OpenAI Whisper:** https://github.com/openai/whisper
- **PCM Audio Format:** https://en.wikipedia.org/wiki/Pulse-code_modulation
- **Audio Processing:** https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html
