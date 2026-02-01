# Testing with Wyoming Satellite Emulator

This guide explains how to use the background server runner script and Wyoming satellite emulator for testing and debugging the chatterbox voice assistant integration.

## Overview

The testing workflow involves:
1. Starting the chatterbox-server in the background using the runner script
2. Using the Wyoming satellite emulator to send test audio and receive responses
3. Monitoring server logs for debugging and troubleshooting

## Prerequisites

- Python environment with chatterbox installed (`pip install -e .`)
- Wyoming tester tool available (`pip install -e wyoming_tester/`)
- Audio test files (WAV format, 16-bit, 16kHz recommended)
- ffmpeg installed for audio format conversion

## Background Server Management

The `scripts/run-server.sh` script provides reliable background process management with logging and PID tracking.

### Starting the Server

```bash
# Start the server in background
./scripts/run-server.sh start
```

**Expected Output:**
```
[2026-01-18 14:07:05] Starting server...
[2026-01-18 14:07:05] Launching server in background...
[2026-01-18 14:07:05] All output will be logged to: /path/to/project/tmp/chatterbox-server.log
[2026-01-18 14:07:05] SUCCESS: Server started successfully
PID: 12345
Log file: /path/to/project/tmp/chatterbox-server.log

To monitor startup logs:
  tail -f /path/to/project/tmp/chatterbox-server.log

To check server status:
  ./scripts/run-server.sh status
```

### Checking Server Status

```bash
./scripts/run-server.sh status
```

**When Running:**
```
[2026-01-18 14:07:10] Checking server status...
SUCCESS: Server is running
PID: 12345
Command: chatterbox-server
Started: Sat Jan 18 14:07:05 2026
Log file: /path/to/project/tmp/chatterbox-server.log

To view recent logs (last 20 lines):
  tail -n 20 /path/to/project/tmp/chatterbox-server.log

To follow logs in real-time:
  tail -f /path/to/project/tmp/chatterbox-server.log

To view logs interactively:
  less /path/to/project/tmp/chatterbox-server.log
```

### Stopping the Server

```bash
./scripts/run-server.sh stop
```

**Expected Output:**
```
[2026-01-18 14:07:15] Stopping server...
[2026-01-18 14:07:15] Sending SIGTERM to process 12345...
SUCCESS: Server stopped
Log file remains at: /path/to/project/tmp/chatterbox-server.log

To view shutdown logs:
  tail -n 20 /path/to/project/tmp/chatterbox-server.log
```

### Restarting the Server

```bash
./scripts/run-server.sh restart
```

This stops the current server (if running) and starts a new instance.

### Getting Help

```bash
./scripts/run-server.sh help
```

Shows complete usage instructions and examples.

## Safe Log File Viewing

All server output is logged to `./tmp/chatterbox-server.log`. Here are safe ways to view logs without overwhelming your terminal:

### View Recent Activity (Last 10-20 lines)

```bash
# Last 20 lines - good for checking recent errors or activity
tail -n 20 ./tmp/chatterbox-server.log

# Last 10 lines - quick status check
tail -n 10 ./tmp/chatterbox-server.log
```

### Follow Logs in Real-Time

```bash
# Follow new log entries as they arrive (Ctrl+C to stop)
tail -f ./tmp/chatterbox-server.log
```

**Tip:** Use this when starting the server to monitor startup progress and initial errors.

### Interactive Log Viewing

```bash
# Use less for searchable, scrollable log viewing
less ./tmp/chatterbox-server.log
```

**Navigation in less:**
- `Space` or `Page Down`: Next page
- `b` or `Page Up`: Previous page
- `/pattern`: Search forward for "pattern"
- `?pattern`: Search backward for "pattern"
- `n`: Next search match
- `N`: Previous search match
- `q`: Quit

### View Specific Time Ranges

```bash
# Show logs from the last hour
tail -f ./tmp/chatterbox-server.log | grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')"

# Show error messages only
grep "ERROR" ./tmp/chatterbox-server.log | tail -n 20
```

## Wyoming Satellite Emulator Testing

Once the server is running in the background, use the Wyoming tester to simulate satellite device interactions.

### Basic Test Run

```bash
# Test with a WAV file (server should be running on localhost:10700)
wyoming-tester --uri tcp://localhost:10700 --file test_audio.wav
```

**Expected Output:**
```
🎤 Transcription: What time is it?
🤖 Intent: get_time
💬 Conversation ID: abc123-def456
💬 Response: The current time is 2:07 PM.
🔊 TTS audio saved to: response.wav
```

### Multi-Turn Conversations

```bash
# First interaction
wyoming-tester -u tcp://localhost:10700 -f question1.wav

# Follow-up using conversation ID from previous response
wyoming-tester -u tcp://localhost:10700 -f follow_up.wav --context abc123-def456
```

### Verbose Debugging

```bash
# Enable detailed Wyoming protocol logging
wyoming-tester -u tcp://localhost:10700 -f test.wav --verbose
```

This shows all Wyoming protocol events for debugging connection issues.

### Testing Different Scenarios

#### 1. Simple Commands
```bash
# Create a simple WAV file with speech
# Then test:
wyoming-tester -u tcp://localhost:10700 -f hello.wav
```

#### 2. Complex Queries
```bash
# Test with more complex audio
wyoming-tester -u tcp://localhost:10700 -f complex_query.wav
```

#### 3. Error Conditions
```bash
# Test server error handling
wyoming-tester -u tcp://localhost:10700 -f malformed_audio.wav
```

## Complete Testing Workflow

### 1. Initial Setup
```bash
# Ensure server is installed
pip install -e .

# Start server in background
./scripts/run-server.sh start

# Verify server is running
./scripts/run-server.sh status
```

### 2. Monitor Server Logs
```bash
# In a separate terminal, follow logs
tail -f ./tmp/chatterbox-server.log
```

### 3. Run Wyoming Tests
```bash
# In another terminal, run tests
wyoming-tester -u tcp://localhost:10700 -f test.wav --verbose
```

### 4. Debug and Iterate
- Check server logs for any errors or unexpected behavior
- Modify server code as needed
- Restart server: `./scripts/run-server.sh restart`
- Re-run Wyoming tests

### 5. Cleanup
```bash
# Stop the background server when done
./scripts/run-server.sh stop
```

## Troubleshooting

### Server Won't Start
```bash
# Check the log file for startup errors
tail -n 50 ./tmp/chatterbox-server.log

# Common issues:
# - Missing dependencies
# - Configuration errors
# - Port already in use (check with: netstat -tlnp | grep 10700)
```

### Wyoming Connection Issues
```bash
# Test basic connectivity (server should respond)
curl -v tcp://localhost:10700

# Check server logs for connection attempts
tail -f ./tmp/chatterbox-server.log | grep -i wyoming
```

### Audio Processing Issues
```bash
# Verify audio file format
ffmpeg -i test.wav

# Check server logs for STT/TTS errors
grep -i "stt\|tts\|audio" ./tmp/chatterbox-server.log | tail -n 20
```

### Log File Management
```bash
# Check log file size
ls -lh ./tmp/chatterbox-server.log

# Archive old logs if needed
mv ./tmp/chatterbox-server.log ./tmp/chatterbox-server.log.$(date +%Y%m%d_%H%M%S)
```

## Advanced Usage

### Custom Server Configuration
The server can be started with custom arguments by modifying the `SERVER_CMD` in the script or running manually:

```bash
# Run with debug logging
chatterbox-server --debug > ./tmp/chatterbox-server.log 2>&1 &

# Run with specific mode
chatterbox-server --mode stt_only > ./tmp/chatterbox-server.log 2>&1 &
```

### Multiple Test Sessions
```bash
# Run multiple test sessions in parallel
for i in {1..3}; do
    wyoming-tester -u tcp://localhost:10700 -f test$i.wav --output response$i.wav &
done
wait
```

### Automated Testing
```bash
# Create a test script
cat > test_wyoming.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting server..."
./scripts/run-server.sh start
sleep 3

echo "Running Wyoming tests..."
wyoming-tester -u tcp://localhost:10700 -f hello.wav
wyoming-tester -u tcp://localhost:10700 -f time.wav

echo "Stopping server..."
./scripts/run-server.sh stop

echo "Test complete!"
EOF

chmod +x test_wyoming.sh
./test_wyoming.sh
```

## File Locations

- **Runner Script:** `scripts/run-server.sh`
- **PID File:** `tmp/chatterbox-server.pid`
- **Log File:** `tmp/chatterbox-server.log`
- **Test Audio:** Place WAV files in project root or specify full paths
- **TTS Responses:** `response.wav` (or custom filename with `--output`)

This setup provides a robust testing environment for developing and debugging Wyoming protocol integrations with reliable background process management and comprehensive logging.
---
Last Updated: 2026-02-01
