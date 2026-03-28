# Project Plan: Whisper Integration with Streaming STT

## Objective

Implement proper Whisper integration for real-time STT (speech-to-text) with PCM audio streaming capabilities. Research and decision analysis show that Whisper requires a **VAD-based buffering strategy** rather than streaming context accumulation. This plan establishes the architecture for efficient audio buffering, silence detection, and transcription with proper error handling and latency optimization.

---

## Research Findings & Strategic Decisions

### Finding 1: Whisper Does NOT Support Streaming
**Fact:** Whisper was designed for batch processing of complete audio files (up to 30 seconds). It does not accumulate context across multiple calls.

**Implication:** We cannot build a "single growing context" model. Instead, we must:
- Buffer PCM packets until a complete utterance is detected
- Send the complete buffer to Whisper for processing
- Clear the buffer and wait for the next utterance

### Finding 2: Real-Time Solutions Use VAD (Voice Activity Detection)
**Fact:** Implementations like FasterWhisper, WhisperLive, and WhisperX use Silero VAD for silence detection.

**Recommended Strategy:**
- Use **Silero VAD** for speaker activity detection
- Buffer audio ONLY when speech is detected
- Process when silence threshold is exceeded (typically 500-1000ms)
- Maximum buffer: 30 seconds (Whisper's limit)

### Finding 3: Home Assistant Uses Wyoming + Whisper
**Current Architecture:**
```
Device (ESP32) → Wyoming Protocol → Whisper Service → Transcript
```
- Wyoming buffers all audio until `AudioStop` event
- No VAD in basic Home Assistant Whisper
- FasterWhisper addon adds VAD support

### Finding 4: Optimal PCM Audio Format
**Standard for STT:**
- Sample Rate: 16000 Hz (16 kHz)
- Channels: 1 (Mono)
- Format: S16_LE (Signed 16-bit Little Endian)
- Chunk Size: 2048-3200 bytes (~64-100ms)

---

## Proposed Architecture (Three Approaches)

### Approach A: Basic Batch Processing (Current/Minimal)
**Trade-off: Simplicity vs Latency**

- Buffer all PCM packets until `AudioStop` event
- Send complete buffer to Whisper
- **Pros:** Simple, reliable, matches current pattern
- **Cons:** Higher latency (full utterance must complete before transcription)
- **Use Case:** Suitable for push-to-talk scenarios

**Implementation:**
- Keep existing buffer in `VoiceAssistantServer`
- On AudioStop, transcribe complete buffer
- No additional dependencies needed
- Current implementation already supports this

---

### Approach B: Silence-Based Streaming (Recommended)
**Trade-off: Latency vs Complexity**

- Use Silero VAD to detect speech/silence
- Buffer audio only while speech detected
- On silence detection (500-1000ms threshold), transcribe
- Restart buffering for next utterance

**Pros:**
- Near-real-time transcription
- Handles multiple utterances in single session
- Reduces memory usage
- Industry standard approach

**Cons:**
- Adds Silero VAD dependency (~50-100MB)
- More complex error handling
- Requires tuning silence thresholds

**Implementation Points:**
- Add Silero VAD library
- New `SileroVADService` class
- VAD-aware buffer management in server
- Configurable silence thresholds
- Continuous streaming mode option

---

### Approach C: Hybrid Adaptive Streaming (Advanced)
**Trade-off: Accuracy vs Complexity**

- Start with silence-based streaming (Approach B)
- Add adaptive thresholds based on audio quality
- Implement pre-roll buffer (capture speech start more reliably)
- Support both VAD mode and explicit Transcribe events

**Pros:**
- Handles difficult audio conditions
- Graceful fallback to explicit Transcribe
- Optimizes for different use cases
- Production-ready resilience

**Cons:**
- Highest complexity
- Multiple modes to maintain
- Requires extensive testing

**Implementation Points:**
- All of Approach B
- Audio quality analysis
- Adaptive threshold tuning
- Mode selection logic (VAD vs explicit)

---

## Recommended Direction: Hybrid Approach with Phased Rollout

### Phase 1: Enhanced Batch Processing (Foundation)
**Focus:** Make current batch approach production-ready

**Tasks:**
1. Document current streaming model
2. Implement proper error handling for buffer management
3. Add logging for audio processing metrics
4. Optimize chunk size handling
5. Test with various audio qualities

**Outcome:** Reliable batch processing baseline

### Phase 2: Silero VAD Integration (Optional Real-Time)
**Focus:** Add optional VAD for near-real-time transcription

**Tasks:**
1. Research and integrate Silero VAD library
2. Create `SileroVADService` class
3. Implement speech detection/silence thresholds
4. Add VAD-aware buffering strategy
5. Support mode selection (VAD vs Batch)
6. Add comprehensive testing

**Outcome:** Optional real-time STT capability

### Phase 3: Adaptive Streaming (Future Enhancement)
**Focus:** Production-grade resilience

**Tasks:**
1. Implement audio quality analysis
2. Add adaptive threshold tuning
3. Create fallback mechanisms
4. Comprehensive performance tuning
5. Production monitoring and metrics

**Outcome:** Robust adaptive streaming

---

## Decision Matrix for Implementation

| Aspect | Batch (A) | VAD-Based (B) | Hybrid (C) |
|--------|-----------|---------------|-----------|
| **Complexity** | Low | Medium | High |
| **Latency** | ~1-3s | ~500-1000ms | ~500-1000ms |
| **Memory Usage** | Low | Medium | Medium |
| **Dependencies** | None | Silero VAD | Silero VAD + extras |
| **Reliability** | High | High | Very High |
| **Multi-utterance** | Single | Multiple | Multiple |
| **Current Support** | ✓ | ✗ | ✗ |
| **Recommended** | Start here | Implement next | Roadmap |

---

## Implementation Steps (For Chosen Approach)

### Common Foundation (Required for all approaches)
1. Create `WhisperSTTService` integration class (if not exists)
2. Define audio format specifications
3. Implement proper PCM packet validation
4. Add comprehensive error handling
5. Create configuration system for thresholds

### If Choosing Approach B or C (VAD-Based)
1. Integrate Silero VAD library
2. Create `SileroVADService` class with:
   - Speech detection
   - Silence detection
   - Confidence scoring
   - Configurable thresholds
3. Implement VAD-aware buffer management
4. Add mode selection and fallback logic
5. Comprehensive testing strategy

### Buffer Management Strategy
**Key Concepts:**
- **Rolling buffer**: Continuous buffer that grows as audio arrives
- **Segment boundaries**: Detected by VAD (silence) or explicit events
- **Pre-roll buffer**: Keep last 100ms before speech to catch speech onset
- **Maximum buffer**: 30 seconds (Whisper maximum)

**Pseudocode:**
```python
class AudioBuffer:
    def __init__(self, sample_rate=16000, max_seconds=30):
        self.buffer = bytearray()
        self.max_bytes = sample_rate * 2 * max_seconds  # 16-bit samples

    def add_chunk(self, chunk):
        self.buffer.extend(chunk)
        # Trim if exceeds maximum
        if len(self.buffer) > self.max_bytes:
            # Keep latest audio, discard oldest
            self.buffer = self.buffer[-self.max_bytes:]

    def get_and_clear(self):
        result = bytes(self.buffer)
        self.buffer.clear()
        return result
```

---

## Success Criteria

### Core Criteria (All Approaches)
1. ✓ Audio chunks correctly accumulated into buffer
2. ✓ PCM format validation (16000 Hz, 16-bit, mono)
3. ✓ Whisper receives complete, valid audio
4. ✓ Transcription produces correct results
5. ✓ Buffer properly cleared between utterances
6. ✓ No memory leaks with long-running sessions
7. ✓ Proper error handling for malformed audio

### Approach B/C Specific Criteria
1. ✓ Silero VAD correctly detects speech
2. ✓ Silence detection works reliably
3. ✓ Silence threshold tuning verified
4. ✓ Multi-utterance sessions handled correctly
5. ✓ Graceful fallback to explicit Transcribe

### Performance Criteria
1. ✓ Transcription latency < 2 seconds (Approach A)
2. ✓ Transcription latency < 1 second (Approach B/C)
3. ✓ Buffer memory < 2MB typical
4. ✓ CPU usage < 5% idle, < 30% during transcription
5. ✓ No dropped audio packets

---

## Testing Strategy

### Unit Tests
- PCM chunk buffering correctness
- Audio format validation
- Buffer lifecycle management
- Error condition handling

### Integration Tests
- Whisper with real audio files
- Wyoming protocol integration
- Multi-utterance sessions
- Silence detection accuracy (VAD approaches)

### End-to-End Tests
- Complete STT pipeline
- Voice assistant response
- TTS synthesis
- Multi-turn conversations

### Performance Tests
- Latency measurement
- Memory profiling
- CPU utilization
- Long-running session stability

---

## Risk Assessment

### Risk: Audio Quality Degradation
**Likelihood:** Medium | **Impact:** High
**Mitigation:**
- Validate PCM format early
- Add quality checks before transcription
- Log audio statistics for debugging

### Risk: VAD Misdetection (Approaches B/C)
**Likelihood:** Low-Medium | **Impact:** Medium
**Mitigation:**
- Configurable thresholds
- Fallback to explicit Transcribe
- Audio quality analysis

### Risk: Memory Exhaustion (Long Sessions)
**Likelihood:** Low | **Impact:** High
**Mitigation:**
- Maximum buffer size enforcement
- Periodic buffer clearing
- Memory monitoring and alerts

### Risk: Whisper Performance
**Likelihood:** Low | **Impact:** Medium
**Mitigation:**
- Batch processing strategy
- Timeout handling
- Alternative STT service fallback

---

## Dependencies & Implementation Considerations

### Core Dependencies
- `whisper` or `faster-whisper` (existing)
- `numpy` (existing, for audio processing)
- `scipy` (existing, for audio operations)

### Optional Dependencies (VAD Approaches)
- `silero-vad` (~50-100MB)
- `torchaudio` (if using advanced VAD features)

### Configuration Parameters
```python
# Proposed configuration structure
WHISPER_CONFIG = {
    "mode": "batch",  # or "vad" or "hybrid"
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size_bytes": 3200,
    "max_buffer_seconds": 30,
    "silence_threshold_ms": 500,  # VAD modes
    "min_speech_duration_ms": 1500,  # VAD modes
    "vad_confidence_threshold": 0.5,  # VAD modes
}
```

---

## Recommendations

### Phase 1 Recommendation: Start with Approach A Enhancement
**Rationale:**
- Current implementation already supports this
- Lowest risk
- Foundation for future enhancement
- Meets immediate needs

**Justification:**
- Push-to-talk scenarios common for ESP32 devices
- Audio buffering already working
- Adding VAD is opt-in enhancement

### Phase 2 Recommendation: VAD Integration Optional
**Conditions for Implementation:**
- User demand for real-time transcription
- Latency becomes critical issue
- Resources available for testing

**Fallback Strategy:**
- Explicit Transcribe event always supported
- VAD is performance optimization, not requirement

---

## Notes & Next Steps

1. **Current Codebase Status:**
   - Audio buffering: ✓ Implemented (wyoming/server.py)
   - Whisper integration: ✓ Implemented (WhisperSTTService)
   - VAD integration: ✗ Not implemented
   - Wyoming protocol: ✓ Implemented

2. **Decision Point:**
   - Approach A is ready for production
   - Approach B requires engineering effort (~2-4 hours research + implementation)
   - Approach C is 6-12 month roadmap item

3. **Recommendation:**
   - Proceed with **Approach A enhancement** first
   - Document current behavior thoroughly
   - Evaluate VAD integration based on use case requirements
   - Plan Approach B as optional future enhancement

---

## Appendix: Audio Format Reference

### Standard STT Audio Format (16-bit Mono PCM @ 16kHz)
```
Sample Rate:     16000 Hz
Bit Depth:       16-bit signed (S16_LE)
Channels:        1 (Mono)
Byte Order:      Little Endian
Duration:        Variable (max ~30 seconds for Whisper)

Bytes per second: 16000 Hz × 2 bytes/sample = 32,000 bytes/sec
Typical chunk:    3200 bytes = 100ms of audio
30-second max:    480,000 bytes = ~468 KB
```

### Wyoming Protocol Audio Frame
```
AudioChunk Event:
  {
    "type": "audio-chunk",
    "rate": 16000,
    "width": 2,
    "channels": 1,
    "audio": <binary PCM data>
  }
```

### PCM Bytes to Samples Conversion
```python
# Extract sample value from PCM bytes (16-bit little endian)
import struct
pcm_chunk = b'\x00\x10...'  # 2-byte PCM samples
sample_width = 2
samples = struct.unpack(f'<{len(pcm_chunk)//sample_width}h', pcm_chunk)
# Returns tuple of signed 16-bit integers
```
