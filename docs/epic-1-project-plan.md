# Epic 1: OTA & Foundation - Project Plan

## Epic Overview

Epic 1 establishes the foundational infrastructure for the Chatterbox device, focusing on Over-The-Air (OTA) update capabilities and a working state machine MVP that cycles through the 6 device states with visual indicators.

**Epic Scope:** Device State Machine MVP + OTA Infrastructure
**Target Device:** ESP32 S3 Box 3
**Timeline:** Foundation phase for subsequent epics

## Goals & Acceptance Criteria

### Goal 1: State Machine MVP with Visual Display
**Status:** In Progress (partially complete)

The device must cycle through all 6 states (N, H, S, A, W, P) with clear visual indicators on the screen.

**Acceptance Criteria:**
- [ ] State machine transitions correctly through: Uninitialized → Idle → Listening → Thinking → Replying → Idle
- [ ] Each state displays its corresponding letter on the screen (N, H, S, A, W, P)
- [ ] Display is large enough (minimum 100pt font) to be read by OCR from video feed
- [ ] Color matches specification (Orange, Purple, Blue, Red, Yellow, Green)
- [ ] State transitions are logged and visible in debug output
- [ ] Transitions can be manually triggered via Home Assistant

**Current Status:**
- ✅ Basic state machine implemented in voice-assistant.yaml
- ✅ Transitions triggered by voice assistant events
- ⏳ Need to add large letter display for each state
- ⏳ Need to update colors to match specification

### Goal 2: OTA Update Infrastructure
**Status:** Not Started

Establish a reliable mechanism to deploy firmware updates to devices over Wi-Fi.

**Acceptance Criteria:**
- [ ] OTA component configured in voice-assistant.yaml
- [ ] Python CLI tool created to deploy binaries to device(s)
- [ ] Tool supports single device and batch device deployment
- [ ] Deployment tool includes progress indication
- [ ] Deployment tool handles errors gracefully
- [ ] Documentation on how to use deployment tool
- [ ] Password protection on OTA endpoint

**Current Status:**
- ✅ Basic OTA platform configured (esphome platform)
- ⏳ Need deployment tool/script
- ⏳ Need password security configuration
- ⏳ Need tool testing

### Goal 3: OCR Validation Tool
**Status:** Not Started

Create a Python tool that validates device state by reading the display via /dev/video0 and using OCR to verify the displayed letter matches the expected state.

**Acceptance Criteria:**
- [ ] Tool reads video feed from /dev/video0
- [ ] Extracts the large letter from the display
- [ ] Uses CPU-based OCR library (e.g., pytesseract, EasyOCR)
- [ ] Returns confidence score for letter recognition
- [ ] Can run in automated validation loops
- [ ] Handles multiple devices
- [ ] Generates validation reports

**Current Status:**
- ⏳ Not started
- Research needed on OCR libraries suitable for live video

## Tasks Breakdown

### Task 1.1: Add Large Letters to Display States
**Owner:** TBD
**Depends On:** None
**Estimated Effort:** 4 hours

Update the state machine display pages to show the large letter (N, H, S, A, W, P) for each state.

**Subtasks:**
- Add text rendering to each state's lambda
- Set font size to minimum 100pt
- Position letter in center of screen
- Ensure letters are readable via OCR

**Resources:**
- ESPHome display documentation
- font configuration in voice-assistant.yaml (see line 424-449)

**Definition of Done:**
- Each state displays its letter clearly
- OCR tool can read letters with >95% confidence
- Color matches specification

### Task 1.2: Update State Colors to Specification
**Owner:** TBD
**Depends On:** None
**Estimated Effort:** 2 hours

Update the background colors for each state to match the specification:
- N (Orange), H (Purple), S (Blue), A (Red), W (Yellow), P (Green)

**Subtasks:**
- Update color values in voice-assistant.yaml
- Test colors on physical device
- Verify OCR can read letters against each color

**Definition of Done:**
- Colors match specification
- Letter contrast is sufficient for OCR

### Task 1.3: Create Python OTA Deployment Tool
**Owner:** TBD
**Depends On:** None (can be parallel)
**Estimated Effort:** 6 hours

Create a Python CLI tool for deploying firmware to devices.

**Subtasks:**
- Research ESPHome OTA protocol
- Create tool that accepts:
  - Device IP/hostname
  - Firmware binary path
  - Optional password
  - Optional batch device list (JSON/CSV)
- Implement progress indication
- Add error handling and retry logic
- Create tool documentation

**Technical Details:**
- Use ESPHome CLI API or direct OTA protocol
- Reference: `esphome upload device.yml --device <ip_address>`
- Support multiple deployment strategies (serial, OTA over LAN)

**Definition of Done:**
- Tool successfully deploys firmware to single device
- Tool supports batch deployment
- Tool has proper error messages
- Tool is documented

### Task 1.4: Secure OTA Configuration
**Owner:** TBD
**Depends On:** Task 1.3
**Estimated Effort:** 2 hours

Add password protection to the OTA endpoint.

**Subtasks:**
- Add password field to ota configuration in voice-assistant.yaml
- Document password management strategy
- Update deployment tool to use password

**Security Considerations:**
- Generate unique passwords per device
- Store passwords securely
- Use OTA protocol version 2 (more secure)

**Definition of Done:**
- OTA endpoint requires password
- Deployment tool successfully authenticates
- Documentation on password management

### Task 1.5: Create OCR Validation Tool
**Owner:** TBD
**Depends On:** Task 1.1 (letters on display)
**Estimated Effort:** 8 hours

Create Python tool that validates device state via OCR.

**Subtasks:**
- Research OCR libraries (pytesseract, EasyOCR, PaddleOCR)
- Create video feed reader for /dev/video0
- Implement letter extraction and recognition
- Create confidence scoring system
- Add device state tracking
- Create batch validation runner
- Generate validation reports

**Technical Details:**
- CPU-based OCR (no GPU required)
- Real-time video processing
- Tolerance for lighting conditions and angles

**Definition of Done:**
- Tool reads and recognizes all 6 letters
- Confidence scores >95% in normal conditions
- Can run automated validation loops
- Generates clear validation reports

### Task 1.6: Testing & Integration
**Owner:** TBD
**Depends On:** All tasks complete
**Estimated Effort:** 4 hours

End-to-end testing of OTA deployment and state machine validation.

**Test Plan:**
- [ ] Deploy firmware via OTA to device
- [ ] Verify state machine cycles through all states
- [ ] Verify all letters display correctly
- [ ] Verify colors match specification
- [ ] Run OCR validation tool
- [ ] Verify OCR tool correctly identifies all states
- [ ] Test error recovery (failed deployment, bad OCR)

**Definition of Done:**
- All tests pass
- No regressions in existing functionality
- Documentation is complete and tested

## Technical Architecture

### State Machine Flow

```
┌─────────────────┐
│  Uninitialized  │ (N - Orange)
│                 │
│  Display: "N"   │
└────────┬────────┘
         │ boot_successful
         ▼
┌─────────────────┐
│      Idle       │ (H - Purple)
│                 │
│  Display: "H"   │ ◄──┐
└────────┬────────┘    │
         │             │
         │ wake_word   │ tts_end
         │ detected    │
         ▼             │
┌─────────────────┐    │
│   Listening     │ (S - Blue)
│                 │
│  Display: "S"   │
└────────┬────────┘
         │ stt_end
         ▼
┌─────────────────┐
│    Thinking     │ (A - Red)
│                 │
│  Display: "A"   │
└────────┬────────┘
         │ tts_start
         ▼
┌─────────────────┐
│    Replying     │ (W - Yellow)
│                 │
│  Display: "W"   │
└────────┬────────┘
         │ tts_end
         └─────────────►
```

### OTA Deployment Flow

```
┌──────────────────┐
│ Deployment Tool  │
└────────┬─────────┘
         │
         ├─► Read firmware binary
         ├─► Connect to device OTA endpoint
         ├─► Authenticate (password)
         ├─► Upload firmware chunks
         └─► Verify and reboot device

         ▼
┌──────────────────┐
│  Device OTA      │
│  Component       │
└────────┬─────────┘
         │
         ├─► Receive firmware
         ├─► Write to flash
         ├─► Verify checksum
         └─► Reboot and run new firmware
```

## Current Configuration

### voice-assistant.yaml Status

**Already Implemented:**
- ✅ Basic state machine (lines 297-375)
- ✅ State-triggered display pages (lines 511-528)
- ✅ OTA component with esphome platform (lines 60-62)
- ✅ Voice assistant event hooks to state transitions
- ✅ Display setup and configuration

**Needs Implementation:**
- ⏳ Large text/letter rendering in display lambdas
- ⏳ Color updates for state backgrounds
- ⏳ OTA password configuration
- ⏳ Additional display states for error handling

## Dependencies & Prerequisites

### Hardware
- ESP32 S3 Box 3 device
- Connected to Wi-Fi network
- USB connection for initial flashing (Arduino 1.8.19 installed)

### Software
- ESPHome 2025.5.0+
- Python 3.8+
- OCR library (pytesseract or EasyOCR)
- Git for version control

### Knowledge
- ESPHome YAML syntax
- C++ lambda expressions (for display rendering)
- Python for deployment/validation tools
- OCR basics for validation tool

## Success Metrics

- ✅ Device cycles through all 6 states with correct visual indicators
- ✅ OTA deployment works reliably (>99% success rate)
- ✅ OCR validation tool achieves >95% accuracy
- ✅ All Epic 1 tests pass
- ✅ Documentation complete and tested
- ✅ Ready for Epic 2 (Wake Word Integration)

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| OCR struggles with lighting | Medium | High | Test with various lighting; implement preprocessing |
| OTA failures | Low | High | Implement retry logic; serial fallback |
| Display rendering issues | Low | Medium | Validate on physical device early |
| Integration complexity | Medium | Medium | Test incrementally; use mocks where possible |

## Notes

- Arduino 1.8.19 is available on the system for initial firmware flashing
- State machine component from external git source (muxa/esphome-state-machine)
- ESPHome min_version: 2025.5.0 in firmware config
- Display uses ILI9xxx driver with S3BOX model

## Next Steps

1. **Immediate:** Task 1.1 (Add letters to display)
2. **Parallel:** Task 1.2 (Update colors), Task 1.3 (Create OTA tool)
3. **Follow-up:** Task 1.4 (Secure OTA), Task 1.5 (OCR validator)
4. **Final:** Task 1.6 (Integration testing)

---

**Last Updated:** 2026-02-13
**Status:** In Planning
**Epic Owner:** TBD
