# Epic 1: Testing & Integration Plan

Comprehensive test plan for validating all Epic 1 deliverables: state machine MVP with visual display, OTA infrastructure, and OCR validation.

**Status:** Test Plan Ready (Awaiting Device Testing)
**Last Updated:** 2026-02-13

## Overview

This test plan covers end-to-end integration testing for:
1. ✅ State Machine with Visual Display (Task 1.1, 1.2)
2. ✅ OTA Deployment Tool (Task 1.3, 1.4)
3. ✅ OCR Validation Tool (Task 1.5)

## Prerequisites

### Hardware Required
- ESP32 S3 Box 3 device
- USB-C cable for initial flashing
- USB webcam (for OCR validation)
- WiFi network access
- Computer for running commands

### Software Required
- ESPHome 2025.5.0+
- Python 3.8+
- Required Python packages: `requests`, `easyocr`, `opencv-python`
- Git (for version control)

### Initial Setup Verification

```bash
# Check ESPHome is installed
esphome version
# Expected: ESPHome 2025.5.0 or higher

# Check Python version
python --version
# Expected: Python 3.8 or higher

# Check Python packages
pip list | grep -E "requests|easyocr|opencv"
# Expected: All three packages installed

# Check project files exist
ls -l firmware/voice-assistant.yaml
ls -l scripts/ota_deploy.py
ls -l scripts/ocr_validate.py
# Expected: All files present
```

## Test Phases

### Phase 1: Firmware Build & Flash (Initial Device Setup)

**Objective:** Successfully compile and flash firmware to device with state machine and display rendering.

#### Pre-Flash Verification

```bash
# Verify firmware configuration
cd firmware
esphome config voice-assistant.yaml
# Expected: No errors, shows device configuration

# Check font sizes
grep "font_state_letter" voice-assistant.yaml
# Expected: size: 120

# Check display pages
grep -A2 "uninitialized_page:" voice-assistant.yaml
# Expected: Shows state letter rendering with colors
```

**Human Intervention Required:** Flash firmware to device via USB

#### Actions Needed (Run on Device via USB)

```bash
# Connect device via USB
# Then run:
esphome run firmware/voice-assistant.yaml
# This will compile and flash the firmware to your device
# Watch for: "INFO Successfully compiled program" and upload progress
```

**Expected Outcome:**
- Device restarts after flashing
- Display shows large letter "N" on orange background
- Serial logs show state machine transitioning

#### Post-Flash Verification

```bash
# After device reboots, check logs
esphome logs firmware/voice-assistant.yaml
# Expected output:
# [I] [esphome.components.logger:213] Log initialized
# [I] [esphome.components.state_machine:XXX] 🔄 STATE MACHINE → UNINITIALIZED
# [I] [esphome.components.state_machine:XXX] 🔄 STATE MACHINE → IDLE
# [I] [esphome.components.voice_assistant:XXX] ✅ Home Assistant CLIENT CONNECTED
```

---

### Phase 2: Display & Visual Validation

**Objective:** Verify state machine cycles through all states with correct letters and colors.

#### Manual Verification Checklist

Create a checklist as you observe each state:

```
Display Verification Checklist
==============================

Initial Boot (Uninitialized):
  ☐ Letter "N" displayed on screen
  ☐ Background color is Orange (#FFA500)
  ☐ Letter is large and readable (120pt)
  ☐ Serial log shows: "STATE MACHINE → UNINITIALIZED"

Idle State (After Boot):
  ☐ Letter "H" displayed on screen
  ☐ Background color is Purple (#800080)
  ☐ White text visible against purple background
  ☐ Serial log shows: "STATE MACHINE → IDLE (ready for wake word)"

Listening State (After Wake Word):
  Trigger: Say wake word (e.g., "Hey Jarvis" or "Okay Nabu")
  ☐ Letter "S" displayed on screen
  ☐ Background color is Blue (#0000FF)
  ☐ Display changes immediately after wake word
  ☐ Serial log shows: "STATE MACHINE → LISTENING (recording speech)"

Thinking State (After Speech Ends):
  Trigger: Stop speaking after wake word
  ☐ Letter "A" displayed on screen
  ☐ Background color is Red (#FF0000)
  ☐ Display shows thinking letter
  ☐ Serial log shows: "STATE MACHINE → THINKING (processing)"

Replying State (While Getting Response):
  Trigger: Device generates response
  ☐ Letter "W" displayed on screen
  ☐ Background color is Yellow (#FFFF00)
  ☐ Black text visible against yellow background
  ☐ Serial log shows: "STATE MACHINE → REPLYING (speaking response)"

Back to Idle:
  Trigger: Response finishes
  ☐ Letter "H" displayed on screen (back to purple)
  ☐ Background color is Purple (#800080)
  ☐ Serial log shows: "STATE MACHINE → IDLE"

Error State (Optional):
  Trigger: Disconnect Home Assistant or force error
  ☐ Letter "P" displayed on screen
  ☐ Background color is Green (#008000)
  ☐ Serial log shows: "STATE MACHINE → ERROR"
```

**Expected Outcome:**
- All states cycle correctly with proper letters
- Colors match specification exactly
- State transitions are smooth and immediate
- Serial logs confirm all transitions

---

### Phase 3: OTA Deployment Testing

**Objective:** Verify OTA deployment tool can successfully update device firmware.

#### Pre-Deployment Setup

```bash
# 1. Ensure device has OTA password configured
# Check: Device was flashed with secrets.yaml containing ota_password

# 2. Get device IP address
esphome logs firmware/voice-assistant.yaml
# Look for: "WiFi connected. IP address: 192.168.X.X"
# Note this IP address

# 3. Build firmware binary for OTA deployment
esphome build firmware/voice-assistant.yaml
# Expected: Build succeeds, creates .bin file
# Note the path to .bin file (e.g., .esphome/build/esp32-s3-box-3/.../firmware.bin)
```

**Human Intervention Required:** Deploy firmware via OTA

#### Actions Needed (Run OTA Deployment)

```bash
# Get the firmware binary path from build output
# Format: .esphome/build/<device_name>/.pioenvs/<device_name>/firmware.bin

# Deploy to single device
python scripts/ota_deploy.py \
  --device <DEVICE_IP_OR_HOSTNAME> \
  --binary <PATH_TO_FIRMWARE.BIN> \
  --password <OTA_PASSWORD_FROM_SECRETS>

# Example:
# python scripts/ota_deploy.py \
#   --device 192.168.1.100 \
#   --binary .esphome/build/esp32-s3-box-3/.pioenvs/esp32-s3-box-3/firmware.bin \
#   --password "your_ota_password"
```

**Expected Output:**
```
📦 Deploying to 192.168.1.100 (192.168.1.100:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ✅ Deployment successful!
```

#### Post-Deployment Verification

```bash
# Check device logs to confirm update
esphome logs firmware/voice-assistant.yaml
# Expected: Fresh boot logs, state machine reinitializes

# Verify display still works
# Expected: Display shows state letters correctly after reboot

# Check no regressions
# Expected: State transitions still work, display colors unchanged
```

**Verification Checklist:**

```
OTA Deployment Checklist
========================

Pre-Deployment:
  ☐ Device IP address identified
  ☐ Firmware binary built successfully
  ☐ OTA password obtained from secrets.yaml
  ☐ Device is on WiFi and responding to ping

Deployment:
  ☐ OTA tool shows "📦 Deploying to <device>"
  ☐ Tool shows "⏳ Uploading..."
  ☐ Tool shows "✅ Deployment successful!"
  ☐ No "❌ Deployment failed" errors

Post-Deployment:
  ☐ Device reboots automatically
  ☐ Display shows state letters correctly
  ☐ Serial logs show fresh boot
  ☐ State machine transitions work
  ☐ All colors appear correct
```

---

### Phase 4: OCR Validation Testing

**Objective:** Verify OCR tool can successfully read and validate device display state.

#### Pre-Validation Setup

```bash
# 1. Check USB webcam is connected
ls -l /dev/video*
# Expected: /dev/video0 (or /dev/video1, etc.)

# 2. Test OCR dependencies are installed
python -c "import cv2; import easyocr; print('✅ All dependencies installed')"
# Expected: Script completes without error

# 3. Verify device display is visible to camera
# Physical: Position webcam to clearly see device display
# Expected: Display letters should be clearly visible to camera
```

**Human Intervention Required:** Set up camera and run OCR validation

#### Actions Needed (Run OCR Validation)

```bash
# Simple validation - detect current state once
python scripts/ocr_validate.py --device esp32.local

# Example output:
# ℹ️  [2026-02-13T15:30:45.123456] esp32.local: Detected H (92.1% confidence)
```

#### OCR Loop Testing

For stress testing and comprehensive validation:

```bash
# Run continuous validation loop for 2 minutes
python scripts/ocr_validate.py \
  --device esp32.local \
  --loop \
  --interval 5 \
  --duration 120 \
  --report ocr_validation_report.json

# During this time, manually trigger state changes:
# 1. Say wake word to trigger LISTENING state
# 2. Let response play to trigger REPLYING state
# 3. Wait for return to IDLE state
# Observe OCR tool detecting each state change
```

**Verification Checklist:**

```
OCR Validation Checklist
=======================

Single Validation:
  ☐ Tool initializes EasyOCR model
  ☐ Tool opens /dev/video0 successfully
  ☐ Tool detects a letter (N, H, S, A, W, or P)
  ☐ Confidence score displayed (target: >95%)
  ☐ No errors reported

Continuous Loop:
  ☐ Loop starts and shows iterations
  ☐ Each iteration detects correct state
  ☐ Confidence scores consistent (>85%)
  ☐ Can capture state transitions
  ☐ Loop stops gracefully on Ctrl+C

Report Generation:
  ☐ JSON report file created
  ☐ Report contains summary statistics
  ☐ Report lists all validation results
  ☐ Success rate shown (target: 100%)
  ☐ Confidence statistics included
```

#### Report Analysis

```bash
# After OCR validation loop, analyze report
python -m json.tool ocr_validation_report.json

# Check key metrics
python << 'EOF'
import json
with open('ocr_validation_report.json') as f:
    report = json.load(f)
    summary = report['summary']
    print(f"Total validations: {summary['total_validations']}")
    print(f"Success rate: {summary['success_rate']}")
    print(f"Average confidence: {summary['confidence_stats']['average']}")
EOF

# Expected output:
# Total validations: 24
# Success rate: 100.0%
# Average confidence: 91.5%
```

---

### Phase 5: Error Recovery Testing

**Objective:** Verify graceful handling of error conditions.

#### Test 5.1: Failed OTA Deployment Recovery

```bash
# Simulate wrong password error
python scripts/ota_deploy.py \
  --device <DEVICE_IP> \
  --binary firmware.bin \
  --password "wrong_password"

# Expected: Tool shows "❌ Authentication failed"
# Expected: Device continues running with old firmware
```

**Verification:**
```
Error Recovery Checklist
=======================

Wrong Password:
  ☐ OTA tool shows "Authentication failed"
  ☐ Device does NOT reboot
  ☐ Device continues with old firmware
  ☐ Display still shows state letters
  ☐ State machine still functioning

Connection Timeout:
  ☐ OTA tool retries automatically
  ☐ Shows "Connection timeout" after all retries fail
  ☐ Device unaffected
  ☐ Tool exits with error code 1

Invalid Binary:
  ☐ Tool sends invalid file
  ☐ Device rejects with "Bad request"
  ☐ Device not corrupted
  ☐ Can still deploy valid binary afterward
```

#### Test 5.2: OCR Error Recovery

```bash
# Simulate camera disconnect
# During OCR validation: unplug USB camera

# Expected: Tool shows "No letter detected"
# Expected: Tool continues trying (in loop mode)
# Expected: Tool recovers when camera reconnected

# Or simulate poor lighting
# During OCR validation: turn off lights

# Expected: Tool shows low confidence scores
# Expected: Tool continues running
# Expected: Accuracy improves when lights restored
```

---

### Phase 6: Documentation Verification

**Objective:** Verify all documentation is complete and accurate.

#### Documentation Checklist

```
Documentation Verification
===========================

Display Configuration:
  ☐ voice-assistant.yaml explains all changes
  ☐ Comments document state transitions
  ☐ Color values documented
  ☐ Font configuration documented

OTA Documentation:
  ☐ OTA_DEPLOY_README.md covers all features
  ☐ OTA_SECURITY.md explains password management
  ☐ OTA_QUICKSTART.md provides quick reference
  ☐ Example batch files provided
  ☐ Error troubleshooting documented

OCR Documentation:
  ☐ OCR_VALIDATE_README.md covers all usage
  ☐ Installation instructions complete
  ☐ Example commands for all modes
  ☐ Report format explained
  ☐ Troubleshooting guide included

General:
  ☐ EPIC_1_TEST_PLAN.md (this file) complete
  ☐ All README files readable and clear
  ☐ Code comments explain complex logic
  ☐ Example commands all work
```

#### Verify Documentation Links

```bash
# Check all documentation files exist
ls -l firmware/OTA_QUICKSTART.md
ls -l firmware/OTA_SECURITY.md
ls -l scripts/OTA_DEPLOY_README.md
ls -l scripts/OCR_VALIDATE_README.md
ls -l dev_notes/EPIC_1_TEST_PLAN.md

# Check all are readable
file firmware/*.md scripts/*.md dev_notes/*.md

# Check no broken links
grep -r "https://" firmware/*.md scripts/*.md | head -5
```

---

## Test Results Summary

### Template for Recording Results

```
Epic 1 Test Results - [DATE]
============================

Device: [DEVICE_IP/HOSTNAME]
Firmware Version: [VERSION]
Test Date: [DATE]
Tester: [NAME]

Phase 1: Firmware Build & Flash
  ☐ PASSED - Device successfully flashed
  ☐ FAILED - [Details]
  Notes: ____________________

Phase 2: Display & Visual Validation
  ☐ PASSED - All 6 states display correctly
  ☐ FAILED - [Details]
  Notes: ____________________

Phase 3: OTA Deployment
  ☐ PASSED - Firmware deployed successfully
  ☐ FAILED - [Details]
  Notes: ____________________

Phase 4: OCR Validation
  ☐ PASSED - All states recognized with >95% confidence
  ☐ FAILED - [Details]
  Notes: ____________________

Phase 5: Error Recovery
  ☐ PASSED - All error cases handled gracefully
  ☐ FAILED - [Details]
  Notes: ____________________

Phase 6: Documentation
  ☐ PASSED - All documentation complete and accurate
  ☐ FAILED - [Details]
  Notes: ____________________

OVERALL RESULT: [PASS/FAIL]
Issues Found: [List any issues]
Recommendations: [Any improvements needed]
Sign-off: [Date/Time]
```

---

## Success Criteria

### Definition of Done (All Must Pass)

- [x] State machine implementation works (Task 1.1 complete)
- [x] Display colors optimized (Task 1.2 complete)
- [x] OTA deployment tool created (Task 1.3 complete)
- [x] OTA security configured (Task 1.4 complete)
- [x] OCR validation tool created (Task 1.5 complete)
- [ ] **Firmware successfully flashes to device** (Phase 1)
- [ ] **All 6 states display correctly** (Phase 2)
- [ ] **OTA deployment succeeds** (Phase 3)
- [ ] **OCR validates states with >95% confidence** (Phase 4)
- [ ] **Error recovery works gracefully** (Phase 5)
- [ ] **All documentation tested and verified** (Phase 6)
- [ ] **No regressions in existing functionality** (All phases)

---

## Rollback Procedures

If testing reveals critical issues:

### Rollback to Previous Firmware

```bash
# If OTA deployment causes issues, can revert via serial
# Connect device via USB and run:
esphome upload firmware/voice-assistant.yaml --device /dev/ttyUSB0

# Or reload from Home Assistant backup
```

### Restore Configuration

```bash
# If configuration is corrupted
git checkout firmware/voice-assistant.yaml
esphome run firmware/voice-assistant.yaml
```

---

## Next Steps

1. ✅ Complete this test plan
2. ⏸️ **HUMAN INTERVENTION REQUIRED** - Flash firmware to device
3. Verify display rendering (Phase 2)
4. ⏸️ **HUMAN INTERVENTION REQUIRED** - Run OTA deployment
5. ⏸️ **HUMAN INTERVENTION REQUIRED** - Set up camera and run OCR validation
6. Test error recovery scenarios (Phase 5)
7. Verify all documentation (Phase 6)
8. Document results
9. Mark Epic 1 as complete

---

## Support & Troubleshooting

See individual documentation files for detailed troubleshooting:
- Device/Display issues → Check [voice-assistant.yaml](../firmware/voice-assistant.yaml)
- OTA issues → See [OTA_DEPLOY_README.md](../scripts/OTA_DEPLOY_README.md) and [OTA_SECURITY.md](../firmware/OTA_SECURITY.md)
- OCR issues → See [OCR_VALIDATE_README.md](../scripts/OCR_VALIDATE_README.md)

---

**Test Plan Created:** 2026-02-13
**Status:** Ready for Testing
**Ready to Proceed:** YES ✅

Next action: Flash firmware to device (Phase 1)
