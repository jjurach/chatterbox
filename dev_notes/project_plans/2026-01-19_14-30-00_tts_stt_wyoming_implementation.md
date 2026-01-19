# Project Plan: TTS/STT Wyoming Protocol Implementation

## Objective

Implement complete STT (Speech-to-Text) and TTS (Text-to-Speech) workflow support in the Chatterbox Wyoming service adapter, enabling the brain server to process audio from Home Assistant through Whisper (transcription) and Piper (synthesis) models. This includes configuring model selection, caching, concurrency handling, test client improvements, and comprehensive validation.

---

## Implementation Steps

### Phase 1: Code Refactoring & Naming Updates

#### Step 1.1: Rename All "chatterbox3b" References to "chatterbox"
- **Objective:** Consolidate naming convention across the entire codebase
- **Scope:** Source tree-wide search and replace
- **Details:**
  - Search for all variations: `chatterbox3b`, `Chatterbox3B`, `CHATTERBOX3B`
  - Update in Python source files (`cackle/`, `src/`, `tests/`, `examples/`)
  - Update in configuration files, scripts, and documentation references
  - Update in CLI entry points and console scripts in `setup.py`
  - Update in comments and docstrings
  - Verify no breaking changes to git history or external references

---

### Phase 2: Wyoming Protocol Event Handling

#### Step 2.1: Implement STT Event Flow (transcribe → transcript)
- **Objective:** Handle STT pipeline: transcribe event → audio-start/audio-chunk/audio-stop → transcript response
- **Location:** `cackle/adapters/wyoming/server.py`
- **Details:**
  - Implement handler for `Transcribe` event (language/model specification)
  - Implement handler for `AudioStart` event (initialize audio stream)
  - Implement handler for `AudioChunk` event (accumulate PCM audio data)
  - Implement handler for `AudioStop` event (trigger transcription)
  - Process accumulated audio through WhisperSTTService
  - Send `Transcript` event back through the socket with transcribed text
  - Ensure proper JSONL formatting: `{"type": "transcript", "data": {"text": "..."}, "payload_length": null}`
  - Add logging for each event stage

#### Step 2.2: Implement TTS Event Flow (synthesize → audio-start/chunk/stop)
- **Objective:** Handle TTS pipeline: synthesize event → audio-start/audio-chunk/audio-stop response stream
- **Location:** `cackle/adapters/wyoming/server.py`
- **Details:**
  - Implement handler for `Synthesize` event (extract text to synthesize)
  - Process text through PiperTTSService to generate audio chunks
  - Send `AudioStart` event with metadata (rate, width, channels)
  - Stream `AudioChunk` events with binary PCM audio data
  - Send `AudioStop` event to signal end of TTS stream
  - Ensure proper JSONL/binary format:
    - JSON header: `{"type": "audio-chunk", "data": {"rate": 22050, "width": 2, "channels": 1}, "payload_length": 1024}`
    - Followed by 1024 bytes of binary PCM data
  - Add logging for each chunk and completion

---

### Phase 3: Model Configuration & Initialization

#### Step 3.1: Add Command-Line Arguments for Model Selection
- **Objective:** Allow configuration of Whisper and Piper models via CLI
- **Location:** `src/main.py` (CLI entry point)
- **Details:**
  - Add `--whisper-model` argument (default: `small.en`)
  - Add `--piper-voice` argument (default: `en_US-danny-low`)
  - Add `--whisper-cache-dir` argument (default: `~/.cache/chatterbox/whisper`)
  - Add `--piper-cache-dir` argument (default: `~/.cache/chatterbox/piper`)
  - Parse arguments and pass to service initialization
  - Add help text and examples

#### Step 3.2: Implement Model Caching in User Home Directory
- **Objective:** Cache downloaded models in user's home directory, not temporary directories
- **Location:** `cackle/services/stt.py` and `cackle/services/tts.py`
- **Details:**
  - For Whisper: Set `download_root` parameter to `~/.cache/chatterbox/whisper/`
  - For Piper: Configure model cache directory to `~/.cache/chatterbox/piper/`
  - Create cache directories if they don't exist (with proper error handling)
  - Allow cache directory location to be configurable via constructor parameters
  - Verify models are not re-downloaded if already cached
  - Add logging to indicate cache hit vs. new download

#### Step 3.3: Implement Model Pre-Initialization on Server Startup
- **Objective:** Load all models before accepting connections to ensure fast response times
- **Location:** `cackle/adapters/wyoming/server.py` (in server startup)
- **Details:**
  - Before the main event loop starts, call model load functions
  - Load Whisper model with specified model size
  - Load Piper voice with specified voice ID
  - Add startup logging: "Initializing STT model: {model_name}..."
  - Add completion logging: "STT model loaded successfully in {elapsed_seconds}s"
  - Add startup logging: "Initializing TTS voice: {voice_name}..."
  - Add completion logging: "TTS voice loaded successfully in {elapsed_seconds}s"
  - If initialization fails, exit with clear error message (don't accept connections)
  - Only accept connections after all models are ready

---

### Phase 4: Test Client Improvements

#### Step 4.1: Refactor Wyoming Test Client to Emulate Home Assistant Behavior
- **Objective:** Transform test client from satellite emulator to HA emulator
- **Location:** `cackle/adapters/wyoming/client.py`
- **Details:**
  - Update class/function documentation to reflect HA emulation role
  - Remove any satellite-specific logic or comments
  - Ensure client behaves like Home Assistant orchestrator, not satellite device

#### Step 4.2: Implement STT Test Workflow with Timeout
- **Objective:** Test STT pipeline end-to-end with proper timing
- **Location:** `cackle/adapters/wyoming/client.py` or `examples/wyoming_client_test.py`
- **Details:**
  - Create `test_stt()` function that:
    - Sends `Transcribe` event (language specification)
    - Sends `AudioStart` event
    - Reads audio file (WAV format) and sends in chunks via `AudioChunk` events
    - Sends `AudioStop` event
    - Waits up to 20 seconds for `Transcript` response
    - Parses and validates transcript text
    - Reports failure if timeout occurs
    - Reports success/failure with comparison to expected text
  - Add configurable audio file path parameter
  - Add timeout as configurable parameter (default: 20s)

#### Step 4.3: Implement TTS Test Workflow with Timeout
- **Objective:** Test TTS pipeline end-to-end with proper timing
- **Location:** `cackle/adapters/wyoming/client.py` or `examples/wyoming_client_test.py`
- **Details:**
  - Create `test_tts()` function that:
    - Sends `Synthesize` event with test text
    - Waits up to 20 seconds for response stream
    - Collects `AudioChunk` events with PCM audio data
    - Receives `AudioStop` event to signal completion
    - Saves generated audio to file (optional)
    - Reports success if complete stream received before timeout
    - Reports failure if timeout or incomplete stream
  - Add configurable test text parameter
  - Add timeout as configurable parameter (default: 20s)
  - Add optional output file path parameter

#### Step 4.4: Enhance scripts/chat-demo.sh for Wyoming Testing
- **Objective:** Improve shell script to properly exercise Wyoming client like HA would
- **Location:** `scripts/chat-demo.sh`
- **Details:**
  - Update script to use new STT test workflow
  - Update script to use new TTS test workflow
  - Add clear console output showing each pipeline stage
  - Add success/failure indicators
  - Make script executable and usable for manual testing
  - Ensure it calls the Wyoming client with proper parameters

---

### Phase 5: Concurrency & Performance Research

#### Step 5.1: Research Whisper and Piper Concurrency Characteristics
- **Objective:** Understand thread-safety and concurrent access requirements
- **Location:** Research, then document in `docs/assist-service-concurrency.md`
- **Details:**
  - Research Whisper library (faster-whisper) concurrency model:
    - Can multiple requests run in parallel?
    - Are there shared resources that require synchronization?
    - Are there thread-safety guarantees?
  - Research Piper library concurrency model:
    - Can multiple TTS requests run in parallel?
    - Are there shared resources that require synchronization?
    - Are there thread-safety guarantees?
  - Document findings in new file with recommendations

#### Step 5.2: Create docs/assist-service-concurrency.md
- **Objective:** Document concurrency patterns for Wyoming service
- **Location:** `docs/assist-service-concurrency.md`
- **Contents:**
  - Executive summary of concurrency support
  - Whisper concurrency analysis (with research findings)
  - Piper concurrency analysis (with research findings)
  - Recommendations for mutex/locking (if needed)
  - Expected contention behavior with multiple HA connections
  - Performance characteristics and bottlenecks
  - Suggested optimization strategies
  - Code examples showing proper usage patterns

#### Step 5.3: Implement Concurrency Safeguards (if needed)
- **Objective:** Add thread-safety mechanisms if research indicates necessity
- **Location:** `cackle/services/stt.py` and `cackle/services/tts.py`
- **Details:**
  - If Whisper/Piper require serialized access: implement asyncio.Lock or threading.Lock
  - Document locking strategy in code comments
  - Add logging around lock acquisition for performance monitoring
  - Test with concurrent connections (see Phase 6)

---

### Phase 6: Concurrency Testing

#### Step 6.1: Implement Concurrent Connection Test
- **Objective:** Verify server handles multiple simultaneous HA connections
- **Location:** `tests/adapters/wyoming/` or new test file
- **Details:**
  - Create test that spawns 3-5 concurrent client connections
  - Each connection sends STT request (different audio or same audio)
  - Each connection sends TTS request (different text or same text)
  - All requests are in flight simultaneously
  - Verify all responses complete correctly
  - Measure response time and identify bottlenecks
  - Add assertions for no data corruption or mixing between streams
  - Document results and any concurrency issues found

---

### Phase 7: Testing & Validation

#### Step 7.1: Verify Pytest Tests Continue to Pass
- **Objective:** Ensure no regression in existing tests
- **Location:** All test files
- **Details:**
  - Run full test suite: `pytest tests/`
  - Verify all existing tests pass
  - Fix any new failures introduced by changes
  - Maintain test coverage for new event handlers

#### Step 7.2: Create New Tests for STT/TTS Event Handlers
- **Objective:** Add unit and integration tests for new event handling
- **Location:** `tests/adapters/wyoming/test_server.py`
- **Details:**
  - Create test for STT event sequence (transcribe → audio-start/chunks/stop → transcript)
  - Create test for TTS event sequence (synthesize → audio-start/chunks/stop)
  - Create test for timeout behavior
  - Create test for invalid/malformed events
  - Create test for concurrent connections
  - Mock Whisper/Piper services for unit tests
  - Use real models for integration tests (if feasible)

#### Step 7.3: Run scripts/chat-demo.sh and Validate Output
- **Objective:** Manual end-to-end testing of the complete workflow
- **Details:**
  - Start server with `scripts/run-server.sh`
  - Run chat-demo script
  - Verify STT produces correct transcript
  - Verify TTS produces audio output
  - Monitor `scripts/run-server.sh` logs for errors
  - Test with different audio samples and TTS texts
  - Document any issues or unexpected behavior

---

### Phase 8: Server Operations Documentation

#### Step 8.1: Add General Reminders to Project Plan
- **Objective:** Ensure developer awareness of operational tools
- **Details:**
  - Reminder: Use `scripts/run-server.sh` to start/restart server
  - Reminder: Check server logs regularly during development
  - Reminder: Monitor `dev_notes/` for any error logs
  - Reminder: Use `--debug` flag for verbose output during development
  - Reminder: Use `scripts/chat-demo.sh` to test end-to-end workflows

---

## Success Criteria

1. **Event Handling:** STT and TTS Wyoming events are properly handled:
   - `Transcribe` → `AudioStart` → `AudioChunk` (multiple) → `AudioStop` → `Transcript` response
   - `Synthesize` → `AudioStart` → `AudioChunk` (multiple) → `AudioStop` response

2. **Model Configuration:**
   - CLI arguments accept `--whisper-model`, `--piper-voice`, `--whisper-cache-dir`, `--piper-cache-dir`
   - Defaults: whisper=small.en, piper=en_US-danny-low
   - Models cache in `~/.cache/chatterbox/` subdirectories

3. **Model Initialization:**
   - Models load on server startup before accepting connections
   - Server logs clearly show loading progress and completion
   - Server rejects connections until all models are loaded

4. **Test Client:**
   - Wyoming test client emulates Home Assistant behavior
   - STT test: transmit audio, receive transcript within 20 seconds
   - TTS test: transmit text, receive audio stream within 20 seconds
   - Proper timeout handling and failure reporting

5. **Naming Convention:**
   - All "chatterbox3b" references renamed to "chatterbox"
   - No stray references remain

6. **Concurrency:**
   - Server handles 3+ concurrent connections without data corruption
   - Performance research documented in `docs/assist-service-concurrency.md`
   - Any necessary locking mechanisms implemented and tested

7. **Testing:**
   - All existing pytest tests pass
   - New tests for STT/TTS event handlers added and passing
   - `scripts/chat-demo.sh` successfully tests end-to-end workflows

---

## Testing Strategy

### Unit Tests
- Mock Whisper/Piper services
- Test event parsing and generation
- Test error handling for malformed events
- Test timeout logic

### Integration Tests
- Use real Whisper/Piper models
- Test full STT pipeline with sample audio
- Test full TTS pipeline with sample text
- Test concurrent connections

### Manual Testing
- Run `scripts/chat-demo.sh` with various inputs
- Monitor logs for errors and performance
- Test with different Whisper models and Piper voices
- Verify model caching behavior

### Performance Testing
- Measure time to first response (after model preload)
- Measure time for full STT pipeline
- Measure time for full TTS pipeline
- Test with 3-5 concurrent connections

---

## Risk Assessment

### Risk 1: Model Initialization Takes Too Long
- **Impact:** Server startup blocked for extended periods
- **Mitigation:** Use smaller models (tiny/base for Whisper, low-quality voice for Piper); document expected load times; add progress logging
- **Owner:** Implement in Step 3.3

### Risk 2: Whisper/Piper Don't Support Concurrent Access
- **Impact:** Performance degradation or crashes under concurrent load
- **Mitigation:** Research concurrency characteristics (Phase 5); implement locking if needed; test thoroughly (Phase 6)
- **Owner:** Steps 5.1, 5.2, 5.3

### Risk 3: Audio Format/Encoding Mismatches
- **Impact:** Transcripts are garbled or TTS produces wrong audio
- **Mitigation:** Validate audio format in handlers; add comprehensive logging; test with various audio samples
- **Owner:** Steps 2.1, 2.2

### Risk 4: Renaming "chatterbox3b" → "chatterbox" Breaks External References
- **Impact:** Integration issues with Home Assistant or other systems
- **Mitigation:** Check all external references first; verify no external dependencies; update documentation
- **Owner:** Step 1.1

### Risk 5: Model Caching Fails Due to Permissions or Disk Space
- **Impact:** Server fails to start or models can't be loaded
- **Mitigation:** Add error handling for cache directory creation; check disk space; provide clear error messages
- **Owner:** Step 3.2

### Risk 6: Wyoming Protocol Implementation Doesn't Match HA Expectations
- **Impact:** HA can't communicate with server properly
- **Mitigation:** Review Wyoming protocol spec carefully; test against real HA instance if possible; use proper JSONL formatting
- **Owner:** Steps 2.1, 2.2

---

## Notes

- **Server Management Reminder:** Always use `scripts/run-server.sh` for starting/restarting the service. Monitor logs frequently during development.
- **Model Size Considerations:** The default `small.en` Whisper model is a good balance; use `base` for smaller footprint. The `en_US-danny-low` Piper voice is lightweight.
- **Concurrency Research:** This is critical for production use; don't skip Phase 5.
- **Backwards Compatibility:** The naming change from "chatterbox3b" to "chatterbox" is a breaking change; ensure all dependent systems are updated.
