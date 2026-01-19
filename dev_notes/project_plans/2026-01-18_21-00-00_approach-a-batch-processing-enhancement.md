# Project Plan: Approach A - Enhanced Batch Processing for Whisper

## Objective

Enhance the current batch processing implementation for production-readiness by documenting the streaming model, implementing robust error handling, adding comprehensive logging, optimizing chunk size handling, and establishing a solid foundation for Whisper integration. This provides a reliable, well-understood baseline before considering future enhancements.

---

## Strategic Rationale

**Why Approach A First:**
- Current implementation already buffers audio correctly
- Zero new dependencies required
- Lowest risk path to production quality
- Establishes foundation for future VAD integration
- Immediate value delivery with minimal complexity

**Production-Ready Criteria:**
- Comprehensive error handling
- Clear buffer lifecycle management
- Observable via logging and metrics
- Tested edge cases
- Configuration options documented

---

## Implementation Steps

### Step 1: Analyze Current Implementation
**Files to examine:**
- `cackle/adapters/wyoming/server.py` - Audio buffering logic
- `cackle/services.py` or `cackle/services/stt.py` - Whisper integration
- `wyoming_tester/cli.py` - Test client behavior

**Deliverable:** Document current streaming model
- How audio chunks flow through system
- Buffer initialization and lifecycle
- Whisper call invocation points
- Error paths and current handling

**Output:** Create `docs/WHISPER_STREAMING_MODEL.md` explaining:
- Architecture diagram
- Data flow diagram
- State machine (buffer states)
- Event sequence documentation

### Step 2: Enhance Error Handling in Buffer Management
**Current State:** Basic buffer with minimal error handling

**Improvements needed:**
1. Validate AudioChunk format before buffering
   - Check rate, width, channels match expectations
   - Verify audio byte length
   - Reject malformed chunks

2. Buffer size validation
   - Enforce maximum buffer size (30 seconds)
   - Log warning when approaching limit
   - Handle buffer overflow gracefully

3. Whisper transcription error handling
   - Catch Whisper exceptions
   - Distinguish error types (timeout, OOM, invalid audio, etc)
   - Implement retry logic with exponential backoff
   - Return meaningful error responses to client

4. Recovery mechanisms
   - Clear buffer on critical errors
   - State recovery after Whisper failure
   - Graceful degradation

**Files to modify:**
- `cackle/adapters/wyoming/server.py` - AudioChunk handler, AudioStop handler, _handle_transcribe
- `cackle/services/` - Whisper service error handling

**Implementation pattern:**
```python
class WyomingError(Exception):
    """Base exception for Wyoming protocol errors"""
    pass

class BufferError(WyomingError):
    """Buffer operation errors"""
    pass

class TranscriptionError(WyomingError):
    """Whisper transcription errors"""
    pass

# In handlers:
try:
    # Validate chunk
    if not self._validate_audio_chunk(event):
        raise BufferError("Invalid audio format")

    # Check buffer size
    if len(self.audio_buffer) + len(event.audio) > MAX_BUFFER_SIZE:
        raise BufferError("Buffer size exceeded")

    self.audio_buffer.extend(event.audio)
except BufferError as e:
    logger.error(f"Buffer error: {e}")
    # Send error response to client
    return
```

### Step 3: Add Comprehensive Logging for Audio Processing Metrics
**Logging Objectives:**
- Track buffer lifecycle (creation → fill → transcription → clear)
- Measure audio duration and quality
- Monitor Whisper performance
- Identify bottlenecks and issues

**Metrics to log:**
1. Per-session metrics:
   - Session ID / connection ID
   - Audio start/stop times
   - Total audio duration captured
   - Number of chunks received
   - Final buffer size

2. Per-chunk metrics:
   - Chunk sequence number
   - Chunk size in bytes
   - Cumulative buffer size after chunk
   - Timestamp received

3. Per-transcription metrics:
   - Whisper processing time
   - Audio duration processed
   - Transcript length (character count)
   - Confidence score (if available)
   - Errors encountered

4. System metrics:
   - Memory usage before/after
   - Buffer clearing time
   - Total uptime and session count

**Implementation pattern:**
```python
import time
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self.session_start = time.time()
        self.chunks_received = 0
        self.total_audio_bytes = 0
        self.transcription_time = 0
        self.transcript_length = 0

    def record_chunk(self, chunk_size):
        self.chunks_received += 1
        self.total_audio_bytes += chunk_size
        logger.debug(
            f"Chunk {self.chunks_received}: {chunk_size} bytes, "
            f"total: {self.total_audio_bytes} bytes"
        )

    def record_transcription(self, duration_ms, result_length):
        self.transcription_time = duration_ms
        self.transcript_length = result_length
        logger.info(
            f"Transcription complete: {duration_ms}ms processing, "
            f"{result_length} characters"
        )
```

**Logging Configuration:**
- DEBUG level: Per-chunk logging (verbose)
- INFO level: Session summaries, transcription results
- ERROR level: Buffer errors, Whisper failures
- Add structured logging support (JSON format option)

### Step 4: Optimize Chunk Size Handling
**Current Issue:** May not be optimally handling variable chunk sizes

**Optimization areas:**
1. Chunk size validation
   - Verify 2048-3200 byte chunks from Wyoming
   - Handle edge cases (first chunk, last chunk, variable sizes)
   - Log warnings for unexpected sizes

2. Memory-efficient buffering
   - Use bytearray (mutable, efficient append)
   - Pre-allocate buffer if max size known
   - Avoid unnecessary copies

3. Chunk boundary handling
   - Ensure no data loss at chunk boundaries
   - Handle partial frames correctly
   - Document assumptions about PCM format

4. Performance monitoring
   - Track append time for large buffers
   - Identify memory allocation bottlenecks
   - Optimize for typical session durations

**Implementation focus:**
```python
class AudioBuffer:
    def __init__(self, sample_rate=16000, channels=1, max_seconds=30):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = 2  # 16-bit
        self.max_size = sample_rate * self.sample_width * channels * max_seconds
        self.buffer = bytearray()
        self.chunks_added = 0

    def add_chunk(self, chunk):
        """Add chunk with validation and error handling"""
        if not chunk:
            raise ValueError("Empty chunk")

        if len(self.buffer) + len(chunk) > self.max_size:
            logger.warning(
                f"Buffer limit approaching: "
                f"{len(self.buffer)} + {len(chunk)} > {self.max_size}"
            )

        self.buffer.extend(chunk)
        self.chunks_added += 1

        if self.chunks_added % 10 == 0:  # Log every 10 chunks
            logger.debug(
                f"Added {self.chunks_added} chunks, "
                f"buffer size: {len(self.buffer)} bytes"
            )

    def get_duration_ms(self):
        """Calculate audio duration in milliseconds"""
        bytes_per_sample = self.sample_width * self.channels
        num_samples = len(self.buffer) // bytes_per_sample
        return (num_samples / self.sample_rate) * 1000

    def get_and_clear(self):
        """Get buffer contents and reset"""
        result = bytes(self.buffer)
        self.buffer.clear()
        self.chunks_added = 0
        logger.debug(f"Buffer cleared, returned {len(result)} bytes")
        return result
```

### Step 5: Comprehensive Testing Strategy
**Test Categories:**

#### 5.1 Unit Tests
- Buffer initialization and cleanup
- Chunk size validation
- Audio format validation
- Buffer size limit enforcement
- Error condition handling

#### 5.2 Integration Tests
- Wyoming protocol -> Buffer -> Whisper pipeline
- Multi-chunk buffering (10-100 chunks)
- Various audio qualities (clean, noisy, compressed)
- Edge cases (empty audio, maximum length, malformed chunks)

#### 5.3 Performance Tests
- Memory usage profiling (typical session: target < 2MB)
- CPU usage during buffering and transcription
- Transcription latency measurement
- Long-running session stability (30+ minutes)

#### 5.4 Reliability Tests
- Repeated sessions without memory leaks
- Error recovery (Whisper failure, then success)
- Buffer state after errors
- Connection drops and recovery

**Test Implementation:**
```python
# tests/adapters/wyoming/test_batch_processing.py

import pytest
from cackle.adapters.wyoming.server import VoiceAssistantServer

class TestBatchProcessing:
    """Test Approach A batch processing implementation"""

    def test_buffer_initialization(self):
        """Buffer should initialize empty"""
        pass

    def test_buffer_add_chunk(self):
        """Buffer should accumulate chunks correctly"""
        pass

    def test_buffer_max_size_enforcement(self):
        """Buffer should not exceed maximum size"""
        pass

    def test_invalid_chunk_format(self):
        """Invalid chunks should be rejected"""
        pass

    def test_whisper_transcription(self):
        """Complete audio should transcribe correctly"""
        pass

    def test_error_recovery(self):
        """Buffer should recover from Whisper errors"""
        pass

    def test_long_session_memory(self):
        """Memory should not leak in long sessions"""
        pass
```

### Step 6: Configuration System
**Establish configurable parameters:**
```python
# Configuration class for Approach A
class BatchProcessingConfig:
    # Audio format
    SAMPLE_RATE = 16000  # Hz
    CHANNELS = 1  # Mono
    SAMPLE_WIDTH = 2  # 16-bit

    # Buffer constraints
    MAX_BUFFER_SECONDS = 30  # Whisper maximum
    MAX_BUFFER_BYTES = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS * MAX_BUFFER_SECONDS

    # Validation
    EXPECTED_CHUNK_SIZE_MIN = 2048  # Bytes
    EXPECTED_CHUNK_SIZE_MAX = 3200  # Bytes

    # Whisper settings
    WHISPER_MODEL_SIZE = "base"
    WHISPER_DEVICE = "cpu"
    WHISPER_TIMEOUT_SECONDS = 30

    # Error handling
    MAX_RETRIES = 3
    RETRY_BACKOFF_MS = 100

    # Logging
    LOG_LEVEL = "INFO"
    LOG_METRICS_EVERY_N_CHUNKS = 10
```

### Step 7: Documentation
**Documents to create/update:**

1. **`docs/WHISPER_STREAMING_MODEL.md`**
   - Architecture overview
   - Data flow diagrams
   - State machine documentation
   - Performance characteristics

2. **`docs/BATCH_PROCESSING_GUIDE.md`**
   - Implementation details
   - Error handling strategies
   - Configuration guide
   - Troubleshooting guide

3. **Code documentation**
   - Docstrings for AudioBuffer class
   - Comments on error handling paths
   - Configuration parameter explanations

4. **`CHANGELOG.md` entry**
   - Summary of Approach A enhancements

---

## Success Criteria

### Functionality
- ✓ Audio buffering works correctly for 10-100 chunks
- ✓ Complete audio buffer sent to Whisper for transcription
- ✓ Whisper produces correct transcriptions
- ✓ Buffer properly cleared between sessions
- ✓ Invalid audio format detected and rejected

### Error Handling
- ✓ Buffer overflow prevented with error message
- ✓ Whisper failures caught and logged
- ✓ Graceful recovery from transcription errors
- ✓ Clear error messages for debugging

### Observability
- ✓ All audio events logged with timestamps
- ✓ Metrics collected for buffer size, chunk count, processing time
- ✓ Debug logs available at DEBUG level
- ✓ Session summary logged at INFO level

### Performance
- ✓ Memory usage < 2MB for typical session
- ✓ No memory leaks over 30-minute sessions
- ✓ Chunk append time < 1ms
- ✓ Transcription latency < 3 seconds
- ✓ CPU usage < 5% idle, < 30% during transcription

### Testing
- ✓ Unit tests for buffer operations (100% coverage)
- ✓ Integration tests with Whisper
- ✓ Performance tests establishing baseline
- ✓ Edge case tests (empty, max size, malformed)

### Documentation
- ✓ Streaming model documented
- ✓ Configuration options documented
- ✓ Error handling explained
- ✓ Troubleshooting guide provided

---

## Risk Assessment

### Risk: Breaking Changes to Existing API
**Likelihood:** Low | **Impact:** High
**Mitigation:**
- Maintain backward compatibility
- Keep AudioChunk handler signature unchanged
- Preserve existing Whisper service interface
- Version configuration schema

### Risk: Performance Regression
**Likelihood:** Low | **Impact:** Medium
**Mitigation:**
- Performance baseline tests
- Profile memory and CPU before/after
- Monitor transcription latency
- Optimize hot paths only

### Risk: Logging Overhead
**Likelihood:** Medium | **Impact:** Low
**Mitigation:**
- Use conditional logging (debug level for verbose)
- Lazy evaluation for expensive logs
- Benchmark logging performance
- Consider async logging for high-volume

### Risk: Incomplete Error Handling
**Likelihood:** Medium | **Impact:** Medium
**Mitigation:**
- Comprehensive error testing
- Real-world scenario simulation
- Code review for error paths
- Monitoring and alerting

---

## Implementation Order

**Phase 1: Foundation (Days 1-2)**
1. Analyze current implementation
2. Create documentation of streaming model
3. Create AudioBuffer utility class
4. Set up configuration system

**Phase 2: Error Handling (Days 2-3)**
1. Add input validation
2. Implement buffer overflow handling
3. Add Whisper error handling
4. Recovery mechanism implementation

**Phase 3: Observability (Days 3-4)**
1. Add comprehensive logging
2. Implement MetricsCollector
3. Add performance monitoring
4. Create structured logging option

**Phase 4: Testing (Days 4-5)**
1. Unit tests for buffer operations
2. Integration tests with Whisper
3. Performance baseline tests
4. Edge case and error tests

**Phase 5: Documentation (Days 5-6)**
1. Write streaming model documentation
2. Create troubleshooting guide
3. Update code comments
4. Create deployment guide

---

## Files to Modify/Create

### New Files
- `cackle/audio/buffer.py` - AudioBuffer class
- `cackle/audio/metrics.py` - MetricsCollector class
- `cackle/config/batch_processing.py` - Configuration
- `docs/WHISPER_STREAMING_MODEL.md` - Architecture docs
- `docs/BATCH_PROCESSING_GUIDE.md` - Implementation guide
- `tests/adapters/wyoming/test_batch_processing.py` - Test suite

### Modified Files
- `cackle/adapters/wyoming/server.py` - Add error handling, logging
- `cackle/services/` - Enhance Whisper service
- `docs/README.md` - Link to new documentation

---

## Notes & Assumptions

### Assumptions
- Audio format is always 16000 Hz, 16-bit, mono
- Whisper library available and functional
- Wyoming protocol provides well-formed AudioChunk events
- Single utterance per session (until Approach B)

### Future Considerations
- VAD integration (Approach B) would replace/extend AudioStop logic
- Multi-utterance support would require silence detection
- Streaming VAD would need different buffer management
- Configuration framework allows mode switching

---

## Appendix: Testing Checklist

### Before Approval
- [ ] Current implementation analyzed
- [ ] Compatibility assessment complete
- [ ] No breaking changes identified
- [ ] Configuration schema designed
- [ ] Error handling paths identified

### Before Merge
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Performance baseline established
- [ ] Memory profile clean (no leaks)
- [ ] Code review completed
- [ ] Documentation complete
- [ ] CHANGELOG updated
