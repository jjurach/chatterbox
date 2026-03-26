# Task 6.20 Manual Verification Checklist

## Overview

This document provides a comprehensive checklist for manually verifying the Chatterbox Home Assistant integration end-to-end. The automated tests cover the programmatic aspects, but manual testing ensures real-world functionality across all user-facing flows.

## Prerequisites

Before starting manual verification, ensure:

- [ ] Chatterbox FastAPI server is running and accessible on the LAN
  - Example: `http://192.168.0.100:8765`
  - Server should respond to `GET /health` with status 200
- [ ] Home Assistant instance is running on the same LAN
  - Confirm version and accessibility
- [ ] HACS is installed in Home Assistant
  - HACS → About (confirm installed)
- [ ] API key is visible in Chatterbox logs
  - Logs should show: `API key: <uuid>`
  - Save this key for configuration steps
- [ ] Network connectivity between Chatterbox server and HA is confirmed
  - Test: `curl http://<chatterbox-ip>:8765/health`

## Section 1: Configuration Flow - Zeroconf Discovery Path

Zeroconf discovery allows Home Assistant to automatically detect the Chatterbox server on the local network without manual URL entry.

### Setup Steps

1. **Start Discovery Service**
   - [ ] Confirm Chatterbox server is running
   - [ ] Verify Zeroconf is advertised (check server logs for "Advertising service")
   - [ ] Wait 3-5 seconds for mDNS advertisement to propagate

2. **Access Home Assistant Configuration**
   - [ ] Open Home Assistant web UI
   - [ ] Navigate to Settings → Devices & Services
   - [ ] Click "+ Create Automation" or "+ New integration"

3. **Discover Integration**
   - [ ] Look for "Chatterbox" in discovered integrations
   - [ ] If not visible, try:
     - [ ] Wait 10 seconds and refresh page
     - [ ] Check that both devices are on same subnet/VLAN
     - [ ] Verify firewall doesn't block mDNS (port 5353)

4. **Select Discovered Device**
   - [ ] Click on the discovered "Chatterbox" entry
   - [ ] Confirm device hostname is displayed correctly
   - [ ] Confirm port number (should be 8765)

5. **Enter Configuration**
   - [ ] Copy API key from Chatterbox logs
   - [ ] Paste API key into the "API Key" field
   - [ ] Enter display name (e.g., "Living Room Chatterbox" or "Home Assistant Chatterbox")
   - [ ] Display name should be user-friendly for voice pipeline selection

6. **Test Connection**
   - [ ] Click "Test Connection" button
   - [ ] Should show "Connection successful" message
   - [ ] If failed, verify:
     - [ ] API key is correct (copy-paste from logs, no extra spaces)
     - [ ] Server is running and accessible
     - [ ] URL format is correct (http://<ip>:8765)

7. **Create Integration**
   - [ ] Click "Create" button
   - [ ] Should see confirmation: "Chatterbox created"
   - [ ] Integration should appear in Devices & Services list
   - [ ] Entry point should show configuration (URL, API key, name)

### Verification

- [ ] Integration appears in Settings → Devices & Services → Chatterbox
- [ ] No errors in Home Assistant logs (Settings → System → Logs)
- [ ] No errors in Chatterbox server logs

---

## Section 2: Configuration Flow - Manual URL Entry Path

Manual URL entry provides an alternative path for users whose Zeroconf discovery doesn't work (e.g., different subnets).

### Setup Steps

1. **Access Configuration Page**
   - [ ] Open Home Assistant web UI
   - [ ] Navigate to Settings → Devices & Services
   - [ ] Click "+ Create Automation" or "+ New integration"

2. **Search for Chatterbox**
   - [ ] Type "Chatterbox" in the search box
   - [ ] Click on "Chatterbox" integration result
   - [ ] If "Chatterbox" doesn't appear, check HACS installation (see HACS section)

3. **Select Manual Entry**
   - [ ] If Zeroconf discovered device appears, select "Manually entered URL"
   - [ ] If no discovery prompt, proceed directly to manual form

4. **Enter Server Details**
   - [ ] URL field:
     - [ ] Enter: `http://<ip-address>:8765`
     - [ ] Example: `http://192.168.0.100:8765`
     - [ ] If using hostname: `http://chatterbox.local:8765`
   - [ ] Verify format (scheme + netloc required):
     - [ ] ✓ `http://192.168.0.100:8765`
     - [ ] ✓ `https://example.com:8765`
     - [ ] ✗ `192.168.0.100:8765` (missing http://)
     - [ ] ✗ `http://` (missing host)

5. **Enter API Key**
   - [ ] Copy API key from Chatterbox logs
   - [ ] Paste into "API Key" field
   - [ ] Field may be marked optional but authentication requires it

6. **Enter Display Name**
   - [ ] Enter friendly name for voice pipeline selection
   - [ ] Examples: "Living Room", "Kitchen", "Bedroom"
   - [ ] Name appears in Settings → Voice Assistants → Conversation Agent dropdown

7. **Test Connection**
   - [ ] Click "Test Connection" button
   - [ ] Button should show spinner/loading state
   - [ ] Within 5-10 seconds, should show success or error
   - [ ] Success message: "Connection successful"
   - [ ] Error cases:
     - [ ] "Cannot connect": Check server is running, URL is correct, firewall allows connection
     - [ ] "Invalid API key": Check API key in logs, verify no extra spaces
     - [ ] Timeout: Check network connectivity, server may be slow

8. **Create Integration**
   - [ ] Click "Create" or "Submit" button
   - [ ] Should show confirmation message
   - [ ] Integration should appear in Devices & Services
   - [ ] Entry should be editable via "Options" button

### Verification

- [ ] Integration shows correct URL in Settings → Devices & Services → Options
- [ ] Integration shows correct API key status
- [ ] Integration shows correct display name
- [ ] No errors in HA logs
- [ ] No errors in Chatterbox server logs

---

## Section 3: Voice Pipeline Setup

After integration is added, configure Home Assistant to use Chatterbox as the conversation provider in voice pipelines.

### Setup Steps

1. **Access Voice Assistants Settings**
   - [ ] Home Assistant → Settings → Voice Assistants

2. **Select or Create Voice Assistant**
   - [ ] If existing voice assistant exists, click it
   - [ ] If new, click "+ Create Voice Assistant"

3. **Configure Conversation Agent**
   - [ ] Find the "Conversation Agent" dropdown
   - [ ] Click dropdown
   - [ ] Select "Chatterbox" from the list
   - [ ] Display name entered during integration setup should appear
   - [ ] Examples: "Living Room Chatterbox", "Chatterbox", etc.

4. **Configure Other Pipeline Steps** (if needed)
   - [ ] Speech-to-Text: Select STT provider (e.g., Whisper)
   - [ ] Text-to-Speech: Select TTS provider (e.g., Piper, Google Translate)
   - [ ] Wake Word Detection: Select wake word detector (if desired)

5. **Save Configuration**
   - [ ] Click "Save" or "Create" button
   - [ ] Should show confirmation
   - [ ] Voice assistant should appear in the list

### Verification

- [ ] Voice assistant appears in Settings → Voice Assistants list
- [ ] "Conversation Agent" shows "Chatterbox" (or your configured name)
- [ ] Other pipeline components are configured
- [ ] No errors in HA logs

---

## Section 4: Voice Command Test

Test actual voice interaction through the full pipeline.

### Prerequisites

- [ ] Voice pipeline is configured (Section 3 complete)
- [ ] Hardware capable of audio input and output available
  - Examples: Google Nest Hub, mobile device with HA app, browser

### Test Procedure

1. **Prepare Device**
   - [ ] Ensure volume is audible
   - [ ] Test that device is connected to HA (shows in list)
   - [ ] Test STT works with a simple phrase (if applicable)

2. **Speak Command**
   - [ ] Activate voice input:
     - [ ] Press microphone icon on device, OR
     - [ ] Say wake word if configured, OR
     - [ ] Use voice assistant button in HA UI
   - [ ] Speak a clear question:
     - [ ] "What is the weather like?"
     - [ ] "Tell me a joke"
     - [ ] "What time is it?"
   - [ ] Speak naturally, not robotic

3. **Verify STT (Speech-to-Text)**
   - [ ] Device should capture your voice
   - [ ] Transcription should appear in HA UI or logs
   - [ ] Transcription should be accurate (not critical, but check)

4. **Verify LLM Processing**
   - [ ] Chatterbox server should receive request (check logs)
   - [ ] Server logs should show: "Processing conversation turn"
   - [ ] Server should query LLM (OpenAI, Ollama, etc.)
   - [ ] LLM should generate response

5. **Verify TTS (Text-to-Speech)**
   - [ ] Server should send response back to HA
   - [ ] HA should synthesize speech with TTS provider
   - [ ] Audio response should be played on device
   - [ ] Response should be natural sounding, appropriate length

### Expected Results

- [ ] You speak: "What is the weather?"
- [ ] Transcript appears: "what is the weather"
- [ ] LLM response generated: "The weather today is sunny with a high of 75°F"
- [ ] Audio response played: LLM response heard clearly
- [ ] Conversation appears in HA history (if logging enabled)

### Troubleshooting

If voice command fails:

1. Check logs:
   - [ ] Home Assistant logs (Settings → System → Logs)
   - [ ] Chatterbox server logs
   - [ ] STT/TTS logs if separate services

2. Verify each pipeline step:
   - [ ] Test STT independently (speak, check transcription)
   - [ ] Test TTS independently (generate audio)
   - [ ] Test Chatterbox directly via curl:
     ```bash
     curl -X POST http://chatterbox-ip:8765/conversation \
       -H "Authorization: Bearer YOUR_API_KEY" \
       -H "Content-Type: application/json" \
       -d '{"text": "Hello", "language": "en"}'
     ```

---

## Section 5: Offline Behavior Test

Verify that the system gracefully handles server unavailability.

### Setup Steps

1. **Verify System is Working**
   - [ ] Complete Section 4: Voice Command Test successfully
   - [ ] Confirm at least one successful voice command

2. **Stop Chatterbox Server**
   - [ ] Locate Chatterbox service/container
   - [ ] Stop it gracefully (docker stop, systemctl stop, etc.)
   - [ ] Wait 3-5 seconds for graceful shutdown
   - [ ] Verify server is not responding: `curl http://ip:8765/health` → should timeout/fail

3. **Speak Command While Offline**
   - [ ] Using same voice device as Section 4
   - [ ] Activate voice input
   - [ ] Speak a command: "What is the weather?"
   - [ ] Device should:
     - [ ] Transcribe your voice (STT should work)
     - [ ] Attempt to reach Chatterbox (connection fails)
     - [ ] Return offline message via TTS

4. **Verify Offline Message**
   - [ ] Should hear: "Chatterbox is temporarily offline, please try again."
   - [ ] Message should be clear and immediate (within 3-5 seconds)
   - [ ] No timeout delay before response

5. **Check HA Notifications**
   - [ ] Home Assistant → Notifications panel (bell icon, top right)
   - [ ] Should see persistent notification:
     - [ ] Title: "Chatterbox Connection Error" or "Chatterbox Timeout"
     - [ ] Message: Should indicate server is unreachable
     - [ ] Notification should remain until server comes back online

6. **Check HA Logs**
   - [ ] Settings → System → Logs
   - [ ] Filter for "chatterbox" or "connection"
   - [ ] Should see warning log entries for connection failures
   - [ ] No error-level logs (warnings are expected)

### Expected Results

- [ ] Offline message is heard within 5 seconds
- [ ] Persistent notification appears in HA
- [ ] No HA UI crashes or errors
- [ ] Logs show graceful error handling
- [ ] HA continues to function normally (other automations, sensors, etc.)

### Verification

- [ ] System handles offline state gracefully
- [ ] User hears clear offline message
- [ ] HA admin sees notification of issue
- [ ] No HA restart required
- [ ] All error handling works as expected

---

## Section 6: Server Restart and Recovery

Verify that the system automatically recovers when the server comes back online.

### Prerequisites

- [ ] Chatterbox server is currently stopped (from Section 5)
- [ ] Offline notification is visible in HA
- [ ] No HA restart has been performed

### Setup Steps

1. **Restart Chatterbox Server**
   - [ ] Locate Chatterbox service/container
   - [ ] Start it: `docker start`, `systemctl start`, etc.
   - [ ] Wait for startup to complete:
     - [ ] Service should be listening on port 8765
     - [ ] `curl http://ip:8765/health` should return 200
     - [ ] Logs should show "Server started" or similar
   - [ ] Wait 3-5 seconds for full startup

2. **Speak Command to Re-verify Function**
   - [ ] Using same voice device and pipeline
   - [ ] Activate voice input
   - [ ] Speak command: "Hello, are you back online?"
   - [ ] Should:
     - [ ] Transcribe voice normally
     - [ ] Reach Chatterbox server successfully
     - [ ] LLM processes and generates response
     - [ ] TTS plays response

3. **Verify Offline Notification Clears**
   - [ ] Home Assistant → Notifications panel
   - [ ] Offline notification should be gone or marked as resolved
   - [ ] No new error notifications should appear

4. **Verify Logs are Clean**
   - [ ] Settings → System → Logs
   - [ ] Should see connection re-established (if logging enabled)
   - [ ] No new error messages for failed connections

### Expected Results

- [ ] Chatterbox server starts successfully
- [ ] First voice command after restart works normally
- [ ] LLM response is heard
- [ ] Offline notification disappears
- [ ] No HA restart was required

### Verification

- [ ] System automatically detects server recovery
- [ ] Full conversation pipeline works immediately after restart
- [ ] No manual HA intervention needed
- [ ] User experience is seamless

---

## Section 7: Options Flow - Reconfiguration

Test the ability to update integration settings after creation.

### Setup Steps

1. **Access Integration Options**
   - [ ] Home Assistant → Settings → Devices & Services
   - [ ] Find "Chatterbox" integration
   - [ ] Click on "Chatterbox" entry
   - [ ] Click "Options" button (if available) or three-dot menu

2. **Update Display Name**
   - [ ] Change current name to something new
   - [ ] Example: "Living Room" → "Upstairs Chatterbox"
   - [ ] Click "Test Connection" to verify settings
   - [ ] Should show success
   - [ ] Click "Save" or "Update"

3. **Verify Name Update in Voice Pipeline**
   - [ ] Settings → Voice Assistants
   - [ ] Check "Conversation Agent" dropdown
   - [ ] New name should appear (old name should be gone)
   - [ ] Voice pipeline should still work with new name

4. **Update API Key** (if testing with new key)
   - [ ] Return to Options
   - [ ] Clear current API key
   - [ ] Paste new API key
   - [ ] Click "Test Connection"
   - [ ] Should succeed if key is valid

5. **Update Server URL** (if testing with different server)
   - [ ] Return to Options
   - [ ] Change URL to different Chatterbox instance
   - [ ] Example: `http://192.168.0.150:8765`
   - [ ] Click "Test Connection"
   - [ ] Should succeed if server is reachable
   - [ ] Speak command to verify connection to new server

6. **Verify Integration Still Works**
   - [ ] After saving any option change
   - [ ] Speak voice command
   - [ ] LLM response should be heard
   - [ ] Check HA and server logs for any errors

### Expected Results

- [ ] All options can be updated
- [ ] Changes take effect immediately
- [ ] Voice pipeline continues to work with updated settings
- [ ] No HA restart required

### Verification

- [ ] Options flow works end-to-end
- [ ] Integration remains functional after reconfiguration
- [ ] Settings persist after save

---

## Section 8: HACS Installation Path (Optional)

For users installing via HACS (Home Assistant Community Store).

### Prerequisites

- [ ] HACS is installed and working in HA
- [ ] User has access to repository URL

### Setup Steps

1. **Add Custom Repository**
   - [ ] Home Assistant → HACS → Integrations
   - [ ] Click three-dot menu (top right) → "Custom repositories"
   - [ ] Enter repository URL: `https://github.com/phaedrus/hentown`
   - [ ] Select "Integration" as category
   - [ ] Click "Create"
   - [ ] Repository should appear in HACS

2. **Search for Chatterbox**
   - [ ] HACS → Integrations → Search bar
   - [ ] Type "Chatterbox"
   - [ ] Click on "Chatterbox" result

3. **Install Integration**
   - [ ] Click "Download" or "Install" button
   - [ ] Accept any dependency dialogs
   - [ ] Wait for download to complete (should be quick, < 1 MB)
   - [ ] See confirmation: "Integration installed"

4. **Restart Home Assistant**
   - [ ] HA requires restart after installing new integration
   - [ ] Settings → System → Restart
   - [ ] Click "Restart Home Assistant"
   - [ ] Wait for HA to come back online (3-5 minutes)

5. **Add Integration**
   - [ ] After HA comes back online
   - [ ] Settings → Devices & Services → "+ New Integration"
   - [ ] Search for "Chatterbox"
   - [ ] Proceed with manual URL entry (Section 2) or Zeroconf discovery (Section 1)

### Expected Results

- [ ] Integration appears in HACS
- [ ] Successfully downloads and installs
- [ ] Integration appears in HA after restart
- [ ] Configuration flow works after installation

### Verification

- [ ] HACS installation path is functional
- [ ] Integration can be installed and configured
- [ ] Works identically to manual installation

---

## Section 9: Error Scenarios

Test error handling and edge cases.

### Scenario 1: Wrong API Key

1. **Start with working integration** (from Section 1 or 2)
2. **Update API key to invalid value**:
   - [ ] Options → Change API key to random string
   - [ ] Click "Test Connection"
   - [ ] Should show error: "Cannot connect" or "Invalid API key"
   - [ ] Don't save (discard changes)

3. **Verify original key still works**:
   - [ ] Cancel options dialog
   - [ ] Speak voice command
   - [ ] Should still work with original key

### Scenario 2: Wrong Server URL

1. **Update URL to unreachable server**:
   - [ ] Options → Change URL to invalid IP
   - [ ] Example: `http://192.168.0.200:8765` (non-existent)
   - [ ] Click "Test Connection"
   - [ ] Should fail: "Cannot connect to server"
   - [ ] Don't save

2. **Verify original URL still works**:
   - [ ] Cancel options dialog
   - [ ] Speak voice command
   - [ ] Should still work with original URL

### Scenario 3: Malformed URL

1. **Enter invalid URL format**:
   - [ ] Options → Change URL to: `192.168.0.100:8765` (missing http://)
   - [ ] Click "Test Connection"
   - [ ] Should reject: "Invalid URL format"
   - [ ] URL field should show validation error
   - [ ] Don't save

2. **Enter valid URL again**:
   - [ ] Change back to: `http://192.168.0.100:8765`
   - [ ] Click "Test Connection"
   - [ ] Should succeed

### Scenario 4: Server Returns 500 Error

1. **Trigger server error** (if testing with real server):
   - [ ] This tests server-side error handling
   - [ ] Ask server admin to simulate error
   - [ ] Or use a mock server that returns 500

2. **Speak voice command**:
   - [ ] Should hear offline message
   - [ ] Should see persistent notification in HA
   - [ ] No crash or hanging

### Scenario 5: Network Timeout

1. **Simulate slow network**:
   - [ ] Update URL to server with high latency
   - [ ] Speak voice command
   - [ ] Wait for timeout (default 30 seconds)

2. **Verify graceful timeout**:
   - [ ] Should hear offline message within 35 seconds
   - [ ] Should see persistent notification
   - [ ] No hanging or UI freeze

---

## Section 10: Comprehensive Workflow Test

Complete end-to-end test combining multiple sections.

### Full Workflow

1. **Setup** (5 minutes)
   - [ ] Start Chatterbox server
   - [ ] Ensure HA is running
   - [ ] Have API key ready

2. **Discovery Configuration** (5 minutes)
   - [ ] Follow Section 1 steps
   - [ ] Verify integration created

3. **Voice Pipeline Setup** (3 minutes)
   - [ ] Follow Section 3 steps
   - [ ] Assign Chatterbox as conversation provider

4. **Voice Command Test** (3 minutes)
   - [ ] Follow Section 4 steps
   - [ ] Speak 3 different commands
   - [ ] Verify all work correctly

5. **Offline Test** (5 minutes)
   - [ ] Follow Section 5 steps
   - [ ] Stop server, speak command, verify offline message
   - [ ] Check notifications

6. **Recovery Test** (5 minutes)
   - [ ] Follow Section 6 steps
   - [ ] Start server, speak command, verify works
   - [ ] Check logs are clean

7. **Options Reconfiguration** (3 minutes)
   - [ ] Follow Section 7 steps
   - [ ] Update display name and verify

8. **Error Scenario Test** (3 minutes)
   - [ ] Follow Section 9 Scenario 1
   - [ ] Test invalid API key handling

9. **Final Verification** (2 minutes)
   - [ ] Speak final voice command
   - [ ] Verify response is correct and timely
   - [ ] Check no errors in logs
   - [ ] Confirm HA UI is responsive

### Expected Result

- [ ] Complete workflow takes ~35 minutes
- [ ] All 9 sections pass successfully
- [ ] System is stable and responsive
- [ ] No unexpected errors or crashes

---

## Checklist Summary

### Critical Path (Must Pass)

- [ ] Zeroconf discovery OR manual URL entry works
- [ ] Integration appears in Devices & Services
- [ ] Voice command reaches Chatterbox and gets response heard
- [ ] Offline behavior returns proper message
- [ ] Server restart restores normal operation
- [ ] HA doesn't require restart after server events

### Important Path (Should Pass)

- [ ] Options flow allows reconfiguration
- [ ] API key authentication is enforced
- [ ] Connection test validates /health endpoint
- [ ] All error cases handled gracefully
- [ ] Logs are clean (no unexpected errors)

### Nice-to-Have Path (Would Be Great)

- [ ] HACS installation works smoothly
- [ ] Zeroconf discovery is reliable across multiple users
- [ ] Multi-language support (French, Spanish, etc.)
- [ ] Performance is responsive (< 3s latency)

---

## Reporting Issues

If any test fails:

1. **Gather Information**
   - [ ] Record exact steps to reproduce
   - [ ] Capture error messages (screenshots or logs)
   - [ ] Note Chatterbox server version
   - [ ] Note Home Assistant version
   - [ ] Note API key format (if safe to share)

2. **Check Logs**
   - [ ] HA logs: Settings → System → Logs
   - [ ] Chatterbox server logs
   - [ ] Network connectivity (ping server)

3. **Report to Development**
   - [ ] Include section number and test name
   - [ ] Include steps to reproduce
   - [ ] Include relevant logs (sanitized)
   - [ ] Include version information

---

## Appendix A: Test Environment Setup

### Quick Setup Script

```bash
# Start Chatterbox server (Docker example)
docker run -d \
  -p 8765:8765 \
  -e OPENAI_API_KEY="your-key-here" \
  --name chatterbox \
  chatterbox:latest

# Verify server is running
curl http://localhost:8765/health

# Watch logs
docker logs -f chatterbox
```

### Network Verification

```bash
# Test server connectivity
curl -v http://192.168.0.100:8765/health

# Test API call
curl -X POST http://192.168.0.100:8765/conversation \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "language": "en"}'

# Monitor network
# Use tcpdump, Wireshark, or router monitoring
tcpdump -i any -n "port 8765"
```

---

## Appendix B: Debugging Tips

### If Voice Commands Don't Work

1. **Check each pipeline step independently:**
   ```bash
   # 1. Test STT (speak and check transcription appears)
   # 2. Test Chatterbox directly:
   curl -X POST http://192.168.0.100:8765/conversation \
     -H "Authorization: Bearer API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello", "language": "en"}'
   # 3. Test TTS (should hear audio response)
   ```

2. **Check logs:**
   - HA logs for Chatterbox errors
   - Chatterbox server logs for request processing
   - STT/TTS service logs

3. **Verify network:**
   - `ping 192.168.0.100` (server IP)
   - `curl http://192.168.0.100:8765/health`
   - Check firewall rules

### If Connection Test Fails

1. **Verify URL format:**
   - Must include scheme: `http://` or `https://`
   - Must include host: IP address or hostname
   - Port optional but recommended: `:8765`

2. **Test directly:**
   ```bash
   curl http://192.168.0.100:8765/health
   ```

3. **Check API key:**
   - Verify in Chatterbox logs
   - No extra spaces
   - Correct format (UUID or string)

### If Offline Message Doesn't Work

1. **Verify server is actually stopped:**
   ```bash
   curl http://192.168.0.100:8765/health
   # Should timeout or get "Connection refused"
   ```

2. **Check TTS is working:**
   - Test TTS independently
   - Check TTS service logs

3. **Check HA configuration:**
   - Verify voice pipeline still points to Chatterbox
   - Check that TTS is configured in pipeline

---

## Appendix C: Performance Baselines

Expected performance metrics:

- **Voice response latency:** 2-5 seconds (STT + LLM + TTS)
- **Connection test:** < 5 seconds
- **Options save:** < 2 seconds
- **UI response:** Immediate (< 500ms)

If performance is significantly worse, check:
- [ ] Network latency (`ping 192.168.0.100`)
- [ ] Server CPU/memory usage (`docker stats` or system monitor)
- [ ] LLM latency (check Chatterbox server logs)
- [ ] TTS latency (check TTS service)

---

## Sign-off

Once all sections have been tested and verified, the integration is ready for production use.

**Tester:** ___________________________
**Date:** ____________________________
**Status:** ☐ PASS | ☐ FAIL (with noted issues)

---

**Last Updated:** 2026-03-25
**Task:** Epic 6, Task 6.20 - Integration Tests & Manual Verification
