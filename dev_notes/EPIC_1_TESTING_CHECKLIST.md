# Epic 1 Testing Quick Checklist

Quick reference for testing all Epic 1 deliverables. Print this or keep handy while testing.

---

## Phase 1: Flash Firmware 🔧

**Requires:** USB cable, device connected

```bash
# Option 1: Build and Flash in one step
esphome run firmware/voice-assistant.yaml

# Option 2: Build first, then flash
esphome compile firmware/voice-assistant.yaml
esphome upload firmware/voice-assistant.yaml
```

**Verification after boot:**

```
☐ Device shows "N" on orange screen
☐ Serial logs show state transitions
☐ After ~10s, display changes to "H" on purple
☐ Device connects to Home Assistant
```

---

## Phase 2: Visual Validation 👁️

**Manual observation of device display**

| State | Letter | Color | When | Check |
|-------|--------|-------|------|-------|
| Uninitialized | N | Orange | Boot | ☐ |
| Idle | H | Purple | After boot | ☐ |
| Listening | S | Blue | After wake word | ☐ |
| Thinking | A | Red | After speech ends | ☐ |
| Replying | W | Yellow | While speaking | ☐ |
| Back to Idle | H | Purple | After reply | ☐ |
| Error (if triggered) | P | Green | On error | ☐ |

**Trigger state transitions:**
```
Say: "Hey Jarvis" (or configured wake word)
→ Should see S (blue) appear
Ask: "What's the time?"
→ Should see A (red) while processing
→ Should see W (yellow) while replying
→ Should return to H (purple) when done
```

---

## Phase 3: OTA Deployment 🚀

**Requires:** Device IP, OTA password, firmware binary

### Get device info:

```bash
# Get device IP from logs
esphome logs firmware/voice-assistant.yaml
# Look for: "WiFi connected. IP address: 192.168.X.X"
# Note the IP: _______________

# Get OTA password from secrets file
grep ota_password firmware/secrets.yaml
# Copy password: _______________

# Build firmware binary
esphome build firmware/voice-assistant.yaml
# Note the binary path
```

### Run deployment:

```bash
python scripts/ota_deploy.py \
  --device <YOUR_DEVICE_IP> \
  --binary <YOUR_BINARY_PATH> \
  --password <YOUR_PASSWORD>
```

**Verification:**

```
☐ Tool shows: "📦 Deploying to..."
☐ Tool shows: "⏳ Uploading..."
☐ Tool shows: "✅ Deployment successful!"
☐ Device reboots (display flickers)
☐ Display still shows state letters
☐ Device reconnects to Home Assistant
```

---

## Phase 4: OCR Validation 📹

**Requires:** USB webcam, camera pointing at display

### Setup:

```bash
# Check camera is visible
ls -l /dev/video0

# Verify OCR dependencies
python -c "import cv2; import easyocr; print('✅ OK')"

# Position camera to clearly see device display
# Ensure good lighting (avoid glare)
```

### Run validation:

```bash
# Single validation - detect current state
python scripts/ocr_validate.py --device esp32.local

# Should output something like:
# ✅ EasyOCR initialized successfully
# ℹ️  [...] Detected H (92.1% confidence)
```

**Verification:**

```
☐ Tool opens video device successfully
☐ Tool detects a letter (N/H/S/A/W/P)
☐ Confidence shown (should be >85%)
☐ No errors reported
```

### Run continuous loop:

```bash
# Run for 2 minutes, detect states as you trigger them
python scripts/ocr_validate.py \
  --device esp32.local \
  --loop \
  --interval 5 \
  --duration 120 \
  --report ocr_test_report.json

# During the loop, manually trigger state changes:
# 1. Say wake word → Look for "Detected S"
# 2. Let it respond → Look for "Detected A", "Detected W"
# 3. Watch it return to idle → Look for "Detected H"
# 4. Press Ctrl+C when done
```

**Verification:**

```
☐ Detects initial state (H - idle)
☐ Detects all state transitions correctly
☐ Confidence scores >85% for all
☐ Report file created with statistics
☐ Report shows 100% success rate
```

### Check report:

```bash
cat ocr_test_report.json | python -m json.tool
# Look for:
# "success_rate": "100.0%"
# "average": "90%+" (confidence)
```

---

## Phase 5: Error Recovery ⚠️

### Test wrong password:

```bash
python scripts/ota_deploy.py \
  --device <YOUR_IP> \
  --binary firmware.bin \
  --password "wrong_password"

# Expected: "❌ Authentication failed"
# Device should NOT reboot
```

✓ Verify: Device still shows display, state machine still works

### Test network error:

```bash
# Turn off WiFi on device, then try:
python scripts/ota_deploy.py \
  --device <YOUR_IP> \
  --binary firmware.bin \
  --password <YOUR_PASSWORD>

# Expected: "Connection timeout" after retries
```

✓ Verify: Device doesn't crash, can reconnect and try again

### Test OCR with bad lighting:

```bash
# While OCR loop is running:
# Turn off lights briefly

# Expected: Low confidence scores
# Tool continues running
```

✓ Verify: Turn lights back on → Confidence recovers

---

## Phase 6: Documentation Check ✅

```bash
# All files exist and readable?
ls -lh firmware/OTA_*.md
ls -lh scripts/*.md
ls -lh dev_notes/EPIC_1*.md

# All commands in docs work?
# ☐ esphome run ...
# ☐ python ota_deploy.py ...
# ☐ python ocr_validate.py ...

# All links in docs point to real files?
# ☐ Check firmware/voice-assistant.yaml exists
# ☐ Check scripts/devices.example.json exists
```

---

## Quick Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| Device won't flash | Restart device, check USB cable, try serial port explicitly |
| Display shows wrong letters | Rebuild firmware, verify color/font changes in yaml |
| OTA fails to connect | Check device IP, try ping, verify WiFi connected |
| OCR not detecting letters | Check camera position, improve lighting, verify device display is clear |
| Confidence scores too low | Move camera closer, improve lighting, ensure display is 120pt+ font |

---

## Test Results

Record results here:

```
Date Tested: _______________
Device IP: _______________
Firmware Version: _______________

Phase 1 (Flash):        ☐ PASS  ☐ FAIL
Phase 2 (Display):      ☐ PASS  ☐ FAIL
Phase 3 (OTA):          ☐ PASS  ☐ FAIL
Phase 4 (OCR):          ☐ PASS  ☐ FAIL
Phase 5 (Error Recov):  ☐ PASS  ☐ FAIL
Phase 6 (Docs):         ☐ PASS  ☐ FAIL

Overall Result:         ☐ PASS  ☐ FAIL

Issues Found:
_________________________________
_________________________________

Notes:
_________________________________
_________________________________
```

---

## When You're Done

- [ ] All phases passed
- [ ] Results documented above
- [ ] Save this checklist for records
- [ ] Commit test results to git:

```bash
git add dev_notes/EPIC_1_TESTING_CHECKLIST.md
git commit -m "docs: record Epic 1 test results - PASS"
```

---

**Status:** Ready to test
**Need Help?** See `dev_notes/EPIC_1_TEST_PLAN.md` for detailed instructions
