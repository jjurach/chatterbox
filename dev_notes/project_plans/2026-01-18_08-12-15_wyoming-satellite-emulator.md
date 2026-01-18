# Project Plan: Wyoming Satellite Emulator for Push-to-Talk Testing

**Created:** 2026-01-18 08:12:15
**Status:** Awaiting Approval
**Estimated Complexity:** Medium

---

## Objective

Develop a Python 3.10+ command-line tool (`wyoming-tester`) that emulates a Wyoming protocol satellite device for testing Home Assistant Assist "Push-to-Talk" (PTT) workflows. The tool will:

1. Send local `.wav` audio files to a Home Assistant Wyoming endpoint
2. Capture and display intent/response text from the AI pipeline
3. Save TTS audio responses locally
4. Extract conversation context for multi-turn testing
5. Provide verbose logging for protocol debugging

This tool enables rapid iteration on voice assistant pipelines without requiring physical satellite hardware.

---

## Implementation Steps

### Step 1: Project Setup & Dependencies
**Actions:**
- Create new Python package structure in project root: `wyoming_tester/`
- Create `__init__.py` and `cli.py` for the CLI entry point
- Create `setup.py` or `pyproject.toml` for package installation
- Define dependencies:
  - `wyoming` - Wyoming protocol library
  - `pydub` - Audio format conversion
  - `numpy` - Audio data manipulation (optional, may be pulled by pydub)
- Create `requirements.txt` with pinned versions

**Files Created:**
- `wyoming_tester/__init__.py`
- `wyoming_tester/cli.py`
- `wyoming_tester/protocol.py` (protocol handling)
- `wyoming_tester/audio.py` (audio processing)
- `setup.py` or `pyproject.toml`
- `requirements.txt`

---

### Step 2: CLI Argument Parser
**Actions:**
- Implement CLI using `argparse` or `click`
- Define required arguments:
  - `--uri` / `-u`: Wyoming endpoint URI (e.g., `tcp://192.168.1.50:10700`)
  - `--file` / `-f`: Path to input `.wav` file
- Define optional arguments:
  - `--context` / `-c`: Conversation ID for multi-turn testing
  - `--verbose` / `-v`: Enable verbose event logging
  - `--output` / `-o`: Custom output filename for TTS response (default: `response.wav`)
- Add input validation (file exists, URI format)

**Files Modified:**
- `wyoming_tester/cli.py`

---

### Step 3: Wyoming Protocol Connection Handler
**Actions:**
- Create `WyomingClient` class for TCP connection management
- Implement connection establishment to target URI
- Implement event serialization/deserialization (JSONL format)
- Create event sender method (for outgoing events)
- Create event listener method (for incoming events with timeout)
- Implement proper connection cleanup/teardown

**Reference:**
- Wyoming protocol uses JSONL (newline-delimited JSON) for events
- Audio is sent as raw PCM bytes interspersed with JSON events
- Need to handle both text and binary data streams

**Files Created/Modified:**
- `wyoming_tester/protocol.py`

---

### Step 4: Audio Processing Module
**Actions:**
- Implement audio file loader using `pydub`
- Create audio format validator (check current format)
- Implement audio conversion to Wyoming standard:
  - **Sample Rate:** 16kHz
  - **Bit Depth:** 16-bit (2 bytes per sample)
  - **Channels:** Mono (1 channel)
  - **Format:** PCM (raw, uncompressed)
- Create chunking logic to split audio into manageable chunks (e.g., 1024-byte chunks)
- Implement audio file saver for TTS response (WAV format)

**Files Created/Modified:**
- `wyoming_tester/audio.py`

---

### Step 5: PTT Workflow Implementation - Handshake
**Actions:**
- Implement `RunPipeline` event creation with parameters:
  - `start_stage="stt"` (Speech-to-Text)
  - `end_stage="tts"` (Text-to-Speech)
  - `conversation_id` (if provided via `--context`)
- Send `RunPipeline` event immediately after connection
- Wait for acknowledgment or proceed to audio transmission

**Files Modified:**
- `wyoming_tester/protocol.py`
- `wyoming_tester/cli.py`

---

### Step 6: PTT Workflow Implementation - Audio Transmission
**Actions:**
- Send `AudioStart` event with parameters:
  - `rate=16000` (16kHz)
  - `width=2` (16-bit = 2 bytes)
  - `channels=1` (Mono)
- Loop through audio chunks and send `AudioChunk` events containing raw PCM data
- Send `AudioStop` event after all chunks transmitted
- Implement timing/throttling if needed (test first without)

**Files Modified:**
- `wyoming_tester/protocol.py`
- `wyoming_tester/cli.py`

---

### Step 7: Response Capture - Intent/Text
**Actions:**
- Implement event listener loop to wait for server responses
- Parse and capture `intent-end` events (contains transcription + intent data)
- Parse and capture `handled-chunk` events (LLM text response chunks)
- Accumulate text response chunks into complete message
- Print formatted output:
  - User transcription
  - Intent detected
  - Assistant text response
  - Conversation ID

**Files Modified:**
- `wyoming_tester/protocol.py`
- `wyoming_tester/cli.py`

---

### Step 8: Response Capture - TTS Audio
**Actions:**
- Listen for incoming `AudioStart` event from server (TTS parameters)
- Collect all `AudioChunk` events containing Piper TTS audio
- Listen for `AudioStop` event (end of TTS transmission)
- Reconstruct complete audio from chunks
- Save audio to local file (default: `response.wav`) using `pydub`
- Print confirmation message with file path

**Files Modified:**
- `wyoming_tester/audio.py`
- `wyoming_tester/cli.py`

---

### Step 9: Conversation Context Management
**Actions:**
- Extract `conversation_id` from response events
- Print conversation ID prominently for reuse
- Support `--context` argument to pass conversation ID for multi-turn testing
- Document conversation ID behavior in help text

**Files Modified:**
- `wyoming_tester/cli.py`
- `wyoming_tester/protocol.py`

---

### Step 10: Verbose Logging
**Actions:**
- Implement logging using Python `logging` module
- Create verbose mode (`-v` / `--verbose`) that prints:
  - All outgoing events (formatted JSON)
  - All incoming events (formatted JSON)
  - Connection status messages
  - Audio processing details (format, chunk count, etc.)
- Use appropriate log levels (INFO for normal, DEBUG for verbose)
- Format output for readability

**Files Modified:**
- `wyoming_tester/cli.py`
- `wyoming_tester/protocol.py`
- `wyoming_tester/audio.py`

---

### Step 11: Error Handling & Edge Cases
**Actions:**
- Add try-catch blocks for:
  - Connection failures (DNS, timeout, refused)
  - File I/O errors (missing input file, write permission)
  - Audio format errors (unsupported format, corrupt file)
  - Protocol errors (unexpected events, malformed JSON)
- Implement graceful shutdown on Ctrl+C
- Add timeout for response waiting (configurable, default 30s)
- Print user-friendly error messages
- Exit with appropriate error codes

**Files Modified:**
- All modules

---

### Step 12: Installation & Entry Point
**Actions:**
- Configure `setup.py` / `pyproject.toml` with:
  - Package name: `wyoming-tester`
  - Entry point: `wyoming-tester` CLI command
  - Dependencies list
  - Python version requirement (>=3.10)
- Test installation with `pip install -e .`
- Verify CLI command is available in PATH

**Files Modified:**
- `setup.py` or `pyproject.toml`

---

### Step 13: Documentation
**Actions:**
- Create `README.md` in `wyoming_tester/` with:
  - Installation instructions
  - Usage examples
  - CLI argument reference
  - Troubleshooting guide
- Add inline code comments for complex logic
- Document Wyoming event flow in module docstring

**Files Created:**
- `wyoming_tester/README.md`

---

## Success Criteria

The project is complete when:

1. ✅ `wyoming-tester` command is installable via pip
2. ✅ Tool successfully connects to Wyoming endpoint at specified URI
3. ✅ WAV files are correctly converted to 16-bit, 16kHz, Mono PCM
4. ✅ Audio is successfully transmitted to Home Assistant
5. ✅ Text responses (intent/LLM output) are captured and displayed
6. ✅ TTS audio response is saved to local file
7. ✅ Conversation ID is extracted and displayed for reuse
8. ✅ `--verbose` flag shows all Wyoming events for debugging
9. ✅ Error handling gracefully manages common failure cases
10. ✅ Documentation is complete and accurate

---

## Testing Strategy

### Unit Testing (Optional)
- Audio conversion functions (format validation, chunk creation)
- Event serialization/deserialization
- CLI argument parsing

### Integration Testing (Required)
- **Test 1: Basic PTT Flow**
  - Input: `test_hello.wav` (any format)
  - Expected: Audio transmitted, text response received, TTS saved
  - Verify: `response.wav` exists and is playable

- **Test 2: Multi-Turn Conversation**
  - Input: First query without `--context`
  - Extract conversation ID from output
  - Input: Second query with `--context <ID>`
  - Verify: Responses reference previous context

- **Test 3: Verbose Logging**
  - Run with `--verbose` flag
  - Verify: All events printed (RunPipeline, AudioStart, AudioChunk, AudioStop, etc.)

- **Test 4: Error Handling**
  - Test with invalid URI (should fail gracefully)
  - Test with missing input file (should display clear error)
  - Test with unsupported audio format (should attempt conversion)

### Manual Testing Checklist
- [ ] Install tool with `pip install -e .`
- [ ] Run `wyoming-tester --help` (verify CLI works)
- [ ] Test basic PTT with sample audio
- [ ] Test multi-turn conversation
- [ ] Test verbose mode
- [ ] Test error cases (bad URI, missing file)
- [ ] Verify output audio plays correctly in media player

---

## Risk Assessment

### High Risk
**Dependency on Wyoming Library Behavior**
- **Issue:** Wyoming protocol library documentation may be incomplete or behavior may differ from specification
- **Mitigation:** Test against actual Home Assistant instance early; use verbose logging to observe actual event flow; reference Wyoming satellite source code if needed

### Medium Risk
**Audio Format Edge Cases**
- **Issue:** Some WAV formats may not convert cleanly (e.g., 24-bit, non-PCM encodings)
- **Mitigation:** Use `pydub` which wraps ffmpeg for robust format support; add format validation with clear error messages; test with diverse audio samples

**Event Timing & Synchronization**
- **Issue:** Unclear when to expect responses, how long to wait, or if events arrive out of order
- **Mitigation:** Implement configurable timeout; use verbose logging to observe event ordering; reference Home Assistant Wyoming implementation

### Low Risk
**CLI Argument Validation**
- **Issue:** Invalid arguments could cause confusing errors
- **Mitigation:** Add validation at CLI entry point; provide clear error messages with usage examples

**Installation on Different Platforms**
- **Issue:** Audio libraries may have platform-specific dependencies (ffmpeg)
- **Mitigation:** Document ffmpeg requirement in README; provide platform-specific installation instructions

---

## Notes

- This tool is intended for **testing and development** only, not production use
- The Wyoming protocol is designed for low-latency streaming; this tool uses file-based batch transmission which may differ slightly from real-time satellite behavior
- Conversation context management depends on Home Assistant configuration (conversation agent, history settings)
- TTS audio format depends on the configured TTS engine (Piper, Google, etc.)

---

## Dependencies on Existing Project Components

- **None** - This is a standalone tool, separate from the main `manage-ha` CLI
- May optionally be integrated into the main project later if desired
- Should be developed in a separate directory (e.g., `wyoming_tester/` or `tools/wyoming_tester/`)

---

## Approval Checkpoint

**This Project Plan is now awaiting developer approval.**

Please review and respond with:
- "Approved" / "Proceed" / "Yes" to begin implementation
- Questions or feedback if clarification is needed
- Requested changes if the plan needs adjustment

