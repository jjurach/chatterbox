# Project Plan: Fix run-server.sh Restart AND Wyoming Response Flow

**Created:** 2026-01-18 22:52 UTC
**Updated:** 2026-01-18 23:00 UTC - Added Wyoming response transmission analysis

---

## Objective

1. **Fix server restart issues**: `scripts/run-server.sh` should reliably stop old server, release port, and start new server without manual `kill -9` intervention
2. **Fix Wyoming response flow**: Ensure STT Whisper transcriptions are properly transmitted back to Wyoming satellite clients

---

## Problem Analysis

### Current Issues

1. **Restart Command Fails**: `scripts/run-server.sh restart` completes but leaves no server running
   - Old process doesn't fully terminate
   - Port remains in TIME_WAIT state
   - New process cannot bind to port
   - Error: "address already in use"

2. **Manual Intervention Required**: Developers must explicitly `kill -9` the process during development
   - SIGTERM + timeout of 30 seconds insufficient
   - SIGKILL sent but process still holds socket
   - Port doesn't release immediately after process death
   - Kernel TCP TIME_WAIT state persists

3. **Socket Cleanup Inadequate**:
   - Wyoming AsyncServer doesn't set SO_REUSEADDR
   - No handling of TIME_WAIT state
   - Immediate restart attempts fail

---

## Wyoming Response Transmission Flow Analysis

### Current State (After STT Transcription)

The Wyoming server successfully:
- Receives audio from client (AudioStart → AudioChunk → AudioStop)
- Buffers 102,538 bytes of PCM audio
- Runs Whisper transcription (1+ second)
- Gets transcript text: `"Hey Jarvis, what is the capital of France?"`
- Creates Transcript event and calls `await self.write_event(event_to_send)`

### Response Path: How Does It Get Back to Client?

**Wyoming Protocol Architecture**:
- Single TCP connection per client
- **Bidirectional event streaming** on the same socket
- No polling required
- No new connections created
- No Home Assistant involvement (local satellite-only mode)

**Flow Diagram**:
```
Client                           Server
|                                |
|-- AudioStart ----------------->|
|-- AudioChunk x101 ------------>|
|-- AudioStop ------------------>|
|                      [Processing STT]
|<--------- Transcript event -----|
|                                |
```

### Current Issue: Event Type Mismatch

**Server sends**:
- `response_event.event()` returns an `Event` object
- Type: `event.type == "transcript"`
- Data: `event.data == {"text": " Hey Jarvis, what is the capital of France?"}`

**Client expects** (wyoming_tester/cli.py line 149):
```python
if isinstance(event, Transcript):  # ← This check FAILS!
```

**Why it fails**:
- `wyoming_tester/protocol.py` receives_event() constructs: `Event.from_dict(event_dict)`
- Creates generic `Event` object, NOT a `Transcript` object
- `isinstance(event, Transcript)` returns False
- Client treats it as "Unhandled event type"
- Event loop continues until timeout (10 seconds)
- Client exits, logging "Disconnected"

### Root Cause

The event type detection logic is broken:
- Server correctly sends: Event with `type="transcript"`
- Client expects: object of class `Transcript` via `isinstance()`
- Client receives: object of class `Event` with `type="transcript"`
- **Mismatch**: Class type check fails, but semantic type is correct

### Solution Approach

**Two implementation options**:

**Option A**: Fix client event detection (Recommended)
- Change wyoming_tester/protocol.py to properly deserialize Event objects
- Convert `Event(type="transcript")` to actual `Transcript` object
- Use Wyoming's event factory/constructors
- Benefit: Works with real Wyoming protocol
- Effort: Low (update receive_event)

**Option B**: Fix server event transmission
- Verify we're sending the right Event format
- Check if Wyoming expects different payload structure
- Benefit: Aligns with library conventions
- Effort: Medium (may require Wyoming patching)

**Recommended**: Option A - fix client to properly handle Wyoming's Event objects

---

## Root Causes

1. **Wyoming's asyncio.start_server()**: Doesn't set `reuse_address=True` by default
   - asyncio supports `reuse_address` parameter in `create_server()`
   - Wyoming's AsyncTcpServer doesn't pass this parameter
   - Workaround: We must extend/monkeypatch or increase wait time

2. **Zombie Process Cleanup**: Current logic waits for process death but doesn't guarantee socket release
   - Process death ≠ socket release
   - Kernel TIME_WAIT state can last 60+ seconds
   - Current wait time of 2 seconds insufficient

3. **Restart Logic**: SIGTERM → wait 30s → SIGKILL → sleep 2 → restart (5s total)
   - Many scenarios fail at the restart attempt
   - No detection of port availability
   - No retry logic for start command

---

## Implementation Steps

### Phase 0: Fix Wyoming Response Event Detection (PREREQUISITE)

**Step 0.1: Update wyoming_tester/protocol.py receive_event()**
- After deserializing Event from JSON, reconstruct proper Wyoming event type
- Use Wyoming's event factory to convert generic Event → specific event class
- Map `event.type == "transcript"` → construct `Transcript` object from event.data
- Preserve payload for audio events
- Test: Ensure `isinstance(event, Transcript)` works after receiving

**Step 0.2: Verify event data structure**
- Check if Transcript expects specific data fields in event.data
- Document expected structure for transcript, synthesize, audio events
- Add logging to show received event type and data

**Step 0.3: Test end-to-end STT response**
- Run Wyoming test client
- Verify Transcript event is recognized
- Print received transcription text to console

---

### Phase 1: Improve Process Termination (run-server.sh)

**Step 1.1: Enhance stop command with aggressive cleanup**
- Keep SIGTERM with 30-second graceful shutdown timeout
- After SIGTERM fails, send SIGKILL immediately (don't wait)
- After SIGKILL, wait 15+ seconds for socket cleanup (increase from 2s)
- Use `fuser` to detect if process still holds port
- Force cleanup of zombie processes using `wait` command

**Step 1.2: Add port availability check**
- Create helper function `is_port_available()` using `ss` or `lsof`
- In stop command: after process termination, verify port is free
- If port still in use after wait, attempt additional cleanup:
  - Check for zombie processes
  - Try `fuser -k` to force-close port holders
  - Maximum retry with exponential backoff

**Step 1.3: Add socket SO_REUSEADDR handling**
- Create helper function `cleanup_stale_connections()`
- Use `ss` to list sockets in TIME_WAIT state on target port
- If found, wait for natural cleanup OR use `fuser` as last resort
- Document this in script comments

### Phase 2: Fix restart command logic

**Step 2.1: Improve restart sequencing**
- Change current: `cmd_stop` → `sleep 5` → `cmd_start`
- New approach: `cmd_stop` → verify port free → `cmd_start`
- Add retry logic to `cmd_start` (up to 3 attempts with 5s between)
- Fail fast if port still in use after 3 retries

**Step 2.2: Add diagnostic output**
- On restart failure, show:
  - Current port status (netstat/ss output)
  - Any processes still holding port (fuser output)
  - Suggest manual cleanup if needed
  - Log suggestion to use `kill -9 <pid>` if automated cleanup fails

### Phase 3: Optimize start command

**Step 3.1: Better startup validation**
- Increase initial sleep from 2s to 3s before checking process
- Add secondary check: verify Wyoming server actually listening (nc or curl)
- Timeout after 10s if server doesn't become accessible
- Better error messages distinguishing port binding vs. startup crash

**Step 3.2: Safer PID tracking**
- Ensure PID file is written AFTER confirming process is truly running
- Add process validity check (not just `kill -0`)
- Verify Wyoming server actually bound to port before declaring success

---

## Additional Implementation Steps

### Phase X: Claude Command Configuration Standardization

**Step X.1: Remove hardcoded model specifications**
- Identify all scripts and commands that invoke `claude` with `--model` parameter
- Remove specific model names (e.g., `claude-3-5-sonnet-20241022`) from command invocations
- Allow claude CLI to use its default model selection

**Step X.2: Update documentation and examples**
- Update any documentation that shows claude command usage with model specifications
- Ensure examples demonstrate default model usage rather than hardcoded models
- Add notes about letting claude choose appropriate models automatically

**Step X.3: Test default model behavior**
- Verify that `claude` commands work without `--model` parameter
- Confirm that default model selection provides adequate performance
- Document the default model behavior for future reference

---

## Success Criteria

### Restart Functionality (Part 1)

1. **`restart` command completes successfully**
   - ✅ Old server fully terminated
   - ✅ Port becomes available
   - ✅ New server starts and becomes listening
   - ✅ No "address already in use" errors

2. **No manual `kill -9` needed**
   - ✅ SIGTERM + SIGKILL logic fully cleans up process
   - ✅ Socket cleanup handling addresses TIME_WAIT state
   - ✅ Port immediately available for reuse

3. **Reliability across fast restarts**
   - ✅ Multiple consecutive restarts work without failure
   - ✅ Restart within 20 seconds (graceful cleanup)
   - ✅ Status command shows accurate running/stopped state

4. **Clear error diagnostics**
   - ✅ If restart fails, show port status and cleanup suggestions
   - ✅ Log actual `ss`/`lsof` output for debugging
   - ✅ Suggest manual fixes if automatic cleanup insufficient

### Wyoming STT Response Flow (Part 2)

5. **Wyoming client receives STT transcript**
   - ✅ Client recognizes Transcript event (isinstance check passes)
   - ✅ Transcription text printed to console
   - ✅ No timeout during response reception
   - ✅ Client exits cleanly after receiving response

6. **Response transmission integrity**
   - ✅ Original audio text preserved in transmission
   - ✅ Proper Wyoming event format (type="transcript", data with text)
   - ✅ No data corruption or truncation
   - ✅ Works with longer transcriptions (>100 characters)

### Claude Command Configuration (Part 3)

7. **Claude commands use default model selection**
   - ✅ No hardcoded model names in claude command invocations
   - ✅ Commands work without `--model` parameter
   - ✅ Default model provides expected functionality
   - ✅ Documentation reflects default model usage

---

## Testing Strategy

### Part 1: Restart Functionality Tests

1. **Single restart test**
   ```bash
   ./scripts/run-server.sh start
   ./scripts/run-server.sh restart
   ./scripts/run-server.sh status  # Should show running
   ```

2. **Fast repeated restart test**
   ```bash
   for i in {1..3}; do
     ./scripts/run-server.sh restart
     ./scripts/run-server.sh status
     sleep 2
   done
   ```

3. **Edge cases**
   - Start → kill process externally → restart
   - Start → corrupt PID file → restart
   - Multiple start commands (should error appropriately)

### Part 2: Wyoming STT Response Flow Tests

4. **Basic transcription response test**
   ```bash
   ./scripts/run-server.sh start
   sleep 5
   python -m wyoming_tester.cli --uri tcp://localhost:10700 --file tests/data/audio/test_audio.wav
   # Expected output:
   # 🎤 Transcription: Hey Jarvis, what is the capital of France?
   # (no timeout, no unhandled event warnings)
   ```

5. **Response event type detection test**
   - Run wyoming_tester with verbose logging
   - Verify `isinstance(event, Transcript)` returns True
   - Confirm event.text contains transcription
   - No "Unhandled event type" log messages

6. **Chat demo full pipeline test**
   ```bash
   scripts/chat-demo.sh
   # Should show:
   # ✓ Server is running and accessible
   # ✓ Pipeline test completed successfully
   # ✓ Demo script finished successfully
   ```

7. **Stress test: Multiple consecutive requests**
   ```bash
   for i in {1..5}; do
     python -m wyoming_tester.cli --uri tcp://localhost:10700 --file tests/data/audio/test_audio.wav
     sleep 2
   done
   # All should complete without timeout or errors
   ```

---

## Risk Assessment

### Low Risk

- **Changes to stop logic**: Increasing wait times and adding port checks
  - Impact: More robust cleanup, no breaking changes
  - Rollback: Remove new checks, revert to simple approach

- **Adding helper functions**: `is_port_available()`, `cleanup_stale_connections()`
  - Impact: Better error handling, diagnostic output
  - Rollback: Remove helper functions, use simplified logic

### Medium Risk

- **Using fuser/ss commands**: May not be available on all systems
  - Mitigation: Check command availability before using
  - Fallback: Use netstat or lsof if available
  - Document requirements in script comments

- **Aggressive cleanup with fuser -k**: Could affect other processes on same port
  - Mitigation: Only use after confirming our PID holds port
  - Fallback: Give user option to cleanup manually if uncertain

### Low Risk - Testing Impact

- All changes are to the script itself, not to core server code
- Wyoming STT pipeline works correctly (separate from restart issues)
- Existing functionality preserved if cleanup improvements fail

---

## Files to Modify

1. **`wyoming_tester/protocol.py`** (PHASE 0 - PREREQUISITE)
   - `receive_event()`: Fix event type detection
   - Convert generic `Event` objects to proper Wyoming event classes
   - Import Wyoming event classes (Transcript, Synthesize, AudioStart, AudioChunk, AudioStop)
   - Map event.type → proper class constructor

2. **`scripts/run-server.sh`** (PHASE 1-3)
   - `is_running()`: Add port availability check
   - `cmd_stop()`: Improve SIGKILL handling and wait times
   - Add helper functions: `is_port_available()`, `cleanup_stale_connections()`
   - `cmd_restart()`: Add port verification and retry logic
   - `cmd_start()`: Enhance startup validation

---

## Implementation Notes

### Socket Binding & TIME_WAIT

The core issue is Linux TCP TIME_WAIT state:
- Socket in TIME_WAIT prevents immediate reuse
- Default timeout: 60 seconds (sysctl net.ipv4.tcp_fin_timeout)
- asyncio.start_server() doesn't set SO_REUSEADDR by default
- Solution: Wait longer OR use SO_REUSEADDR (requires Wyoming patch)

**Our approach**: Increase wait time + port availability checks, since patching Wyoming is outside scope.

### Command Dependencies

Scripts will use standard Linux tools:
- `ss` (more modern, preferred)
- `netstat` (fallback if ss unavailable)
- `lsof` (for detailed socket info)
- `fuser` (for force-closing sockets, last resort)
- `ps` (already used)
- `kill` (already used)

All tools are standard on Linux. Script should gracefully handle missing tools.

---

## Acceptance Criteria

- [x] Script properly terminates old server before starting new one
- [x] `restart` command succeeds without "address already in use" error
- [x] Port verified available before starting new server
- [x] No manual `kill -9` needed during development workflow
- [x] Diagnostic output helps troubleshoot failures
- [x] Works reliably across multiple consecutive restarts