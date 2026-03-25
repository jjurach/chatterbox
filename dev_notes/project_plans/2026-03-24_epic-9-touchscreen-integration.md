# Epic 9: Touchscreen Integration & Device Coordination - Project Plan

**Document ID:** EPIC-9-TOUCHSCREEN-2026
**Epic Title:** Touchscreen Integration & Device Coordination
**Status:** Planned
**Target Completion:** 2026-07-15
**Estimated Duration:** 3 weeks (~120 hours)
**Last Updated:** 2026-03-24
**Architecture Research:** Evaluate both Arduino and ESPHome approaches; decide based on findings

---

## Executive Summary

Epic 9 implements touchscreen support on the ESP32-S3-BOX-3B and enables multi-device coordination. This epic involves research into the touchscreen hardware and evaluation of implementation approaches (Arduino vs. ESPHome), integration with the device state machine, and multi-device discovery/coordination for room-aware functionality. The touchscreen becomes an additional input method complementing voice interaction, while device coordination enables room-aware context sharing.

---

## Goals & Success Criteria

### Primary Goals (Touchscreen Integration)
1. Research and understand box3b touchscreen hardware specifications
2. Evaluate Arduino and ESPHome approaches
3. Implement touch detection and gesture recognition
4. Integrate with device state machine for state transitions
5. Create UI framework for on-screen feedback
6. Enable user interaction patterns (swipe, tap, long-press)
7. Handle concurrent voice and touch input
8. Enable multi-device discovery and coordination
9. Implement room-aware context sharing

### Success Criteria (Touchscreen & Coordination)
- [ ] Touchscreen hardware fully documented and understood
- [ ] Arduino vs. ESPHome evaluation completed with decision documented
- [ ] Touch detection working reliably
- [ ] Gesture recognition accurate (tap, swipe, long-press)
- [ ] Latency <100ms for touch response
- [ ] Integration approach selected based on evaluation findings
- [ ] UI framework functional and responsive
- [ ] At least 3 use cases implemented
- [ ] Touch doesn't interfere with voice functionality
- [ ] System stable with touch interaction
- [ ] Multi-device discovery working
- [ ] Room-aware context sharing functional
- [ ] Device coordination latency acceptable for distributed system

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 1 (OTA & Foundation):** Device firmware framework
- **Epic 7 (Recording):** Voice interaction foundation to complement
- **ESPHome Framework:** Available and compatible

### Prerequisites
- ESP32-S3-BOX-3B with touchscreen operational
- Touch controller specifications documented
- I2C/SPI communication verified
- Display driver working (Lovelace UI or similar)

### Blockers to Identify
- Touchscreen hardware compatibility
- Touch controller communication protocol
- Memory constraints for UI rendering
- Potential conflicts with display/audio

---

## Detailed Task Breakdown

### Task 9.1: Hardware Research & Documentation
**Objective:** Research touchscreen hardware specifications
**Estimated Hours:** 12
**Acceptance Criteria:**
- [ ] Touch controller identified and documented
- [ ] Communication protocol documented (I2C/SPI)
- [ ] Pin configuration documented
- [ ] Resolution and sensitivity specifications
- [ ] Power requirements documented
- [ ] Hardware capabilities documented
- [ ] Datasheets and reference docs collected

**Implementation Details:**

**Research Areas:**
1. Touch Controller Type (GT911, FT5206, GT1151, etc.)
2. Communication Bus (I2C address, SPI pins)
3. Interrupt pin configuration
4. Coordinate system and resolution
5. Calibration requirements
6. Multitouch support
7. Gesture recognition capabilities

**Documentation Template:**

```markdown
# ESP32-S3-BOX-3B Touchscreen Hardware

## Touch Controller
- **Model:** [e.g., GT911]
- **Communication:** I2C @ address 0x5D
- **Interrupt Pin:** GPIO XX
- **Reset Pin:** GPIO XX
- **Power:** 3.3V

## Display
- **Resolution:** 320x240 pixels
- **Type:** IPS LCD
- **Interface:** RGB

## Gestures Supported by Hardware
- Single tap
- Multi-touch (2-5 fingers)
- Long press
- Swipe/drag
- Pinch zoom (if supported)

## Coordinate System
- Origin: top-left (0,0)
- X range: 0-319
- Y range: 0-239

## Known Issues/Limitations
- [List any hardware quirks]
```

**Testing Plan:**
- Verify all specifications
- Test with actual hardware
- Document any discrepancies

---

### Task 9.2: ESPHome Driver Evaluation
**Objective:** Evaluate ESPHome's touchscreen driver capabilities
**Estimated Hours:** 12
**Depends On:** Task 9.1
**Acceptance Criteria:**
- [ ] ESPHome compatibility verified
- [ ] Available touchscreen drivers documented
- [ ] Capabilities and limitations identified
- [ ] Integration approach determined
- [ ] Proof-of-concept working
- [ ] Fallback strategy identified if ESPHome insufficient

**Implementation Details:**

**ESPHome Evaluation Criteria:**

```yaml
# esphome/chatterbox_touchscreen_eval.yaml

esphome:
  name: chatterbox-touchscreen
  platform: esp32
  board: esp32-s3-devkitc-1

# Touchscreen configuration
touchscreen:
  platform: gt911  # If supported
  id: my_touchscreen
  interrupt_pin: GPIO16
  reset_pin: GPIO17
  on_touch:
    - logger.log: "Touchscreen pressed"

# Display for feedback
display:
  - platform: ili9xxx
    model: ILI9341
    id: my_display
    # ...

# Logic to handle touch
binary_sensor:
  - platform: touchscreen
    touchscreen_id: my_touchscreen
    x_min: 0
    x_max: 100
    y_min: 0
    y_max: 100
    on_press:
      - logger.log: "Touch area pressed"
```

**Evaluation Matrix:**

| Aspect | ESPHome Native | Arduino Driver | Custom |
|--------|---|---|---|
| Effort | Low | Medium | High |
| Complexity | Low | Medium | High |
| Flexibility | Medium | High | Very High |
| Integration | Seamless | Good | Requires work |

**Decision:** [To be determined after evaluation]

**Testing Plan:**
- Test ESPHome driver with actual hardware
- Verify all gesture types
- Check latency
- Test reliability over time

---

### Task 9.3: Touch Detection & Raw Data Reading
**Objective:** Implement touch detection at driver level
**Estimated Hours:** 10
**Depends On:** Task 9.1
**Acceptance Criteria:**
- [ ] Touch data reading implemented
- [ ] Interrupt handling working
- [ ] Calibration completed
- [ ] Data validated
- [ ] Coordinate mapping verified
- [ ] Performance acceptable

**Implementation Details:**

**Touch Controller Driver (if custom implementation needed):**

```cpp
class TouchscreenDriver {
  private:
    static const int TOUCH_I2C_ADDR = 0x5D;
    static const int TOUCH_INT_PIN = 16;
    static const int TOUCH_RST_PIN = 17;

    struct TouchPoint {
      uint16_t x;
      uint16_t y;
      uint8_t id;
      uint8_t area;
    };

    static const int MAX_TOUCH_POINTS = 5;
    TouchPoint points[MAX_TOUCH_POINTS];
    uint8_t point_count = 0;

  public:
    bool initialize() {
      // Reset touch controller
      pinMode(TOUCH_RST_PIN, OUTPUT);
      digitalWrite(TOUCH_RST_PIN, LOW);
      delay(10);
      digitalWrite(TOUCH_RST_PIN, HIGH);
      delay(100);

      // Configure interrupt
      pinMode(TOUCH_INT_PIN, INPUT);
      attachInterrupt(
        digitalPinToInterrupt(TOUCH_INT_PIN),
        touch_interrupt,
        FALLING
      );

      return true;
    }

    static void touch_interrupt() {
      // Read touch data
      // Signal event
    }

    bool read_touch_data() {
      uint8_t data[20];

      // Read from touch controller via I2C
      if (!i2c_read(TOUCH_I2C_ADDR, 0x00, data, sizeof(data))) {
        return false;
      }

      // Parse touch data
      point_count = data[2] & 0x0F;  // Number of touch points
      if (point_count > MAX_TOUCH_POINTS) {
        point_count = MAX_TOUCH_POINTS;
      }

      // Extract touch points
      for (int i = 0; i < point_count; i++) {
        int offset = 4 + (i * 8);

        points[i].id = data[offset];
        points[i].x = ((data[offset + 1] & 0x0F) << 8) | data[offset + 2];
        points[i].y = ((data[offset + 3] & 0x0F) << 8) | data[offset + 4];
        points[i].area = data[offset + 5];
      }

      return true;
    }

    void get_touch_points(TouchPoint* output, uint8_t& count) {
      for (int i = 0; i < point_count; i++) {
        output[i] = points[i];
      }
      count = point_count;
    }

    uint8_t get_point_count() {
      return point_count;
    }
};
```

**Testing Plan:**
- Test touch data reading
- Verify coordinate accuracy
- Test with multitouch
- Check interrupt latency

---

### Task 9.4: Gesture Recognition
**Objective:** Implement gesture detection (tap, swipe, long-press)
**Estimated Hours:** 12
**Depends On:** Task 9.3
**Acceptance Criteria:**
- [ ] Tap detection working
- [ ] Swipe detection (4 directions) working
- [ ] Long-press detection working
- [ ] Gesture recognition accurate
- [ ] False positive rate <5%
- [ ] Gesture latency <200ms

**Implementation Details:**

**Gesture Recognizer:**

```cpp
enum GestureType {
  GESTURE_NONE,
  GESTURE_TAP,
  GESTURE_SWIPE_LEFT,
  GESTURE_SWIPE_RIGHT,
  GESTURE_SWIPE_UP,
  GESTURE_SWIPE_DOWN,
  GESTURE_LONG_PRESS,
  GESTURE_PINCH
};

struct Gesture {
  GestureType type;
  uint16_t start_x;
  uint16_t start_y;
  uint16_t end_x;
  uint16_t end_y;
  unsigned long duration;
};

class GestureRecognizer {
  private:
    // Gesture thresholds
    static const int SWIPE_MIN_DISTANCE = 50;  // pixels
    static const int TAP_MAX_DISTANCE = 10;     // pixels
    static const int LONG_PRESS_DURATION = 500; // ms

    // State tracking
    uint16_t start_x = 0;
    uint16_t start_y = 0;
    unsigned long press_time = 0;
    bool touching = false;

  public:
    Gesture recognize_gesture(TouchPoint point, bool just_released) {
      Gesture result = {.type = GESTURE_NONE};

      if (!touching && point.area > 0) {
        // Touch started
        touching = true;
        start_x = point.x;
        start_y = point.y;
        press_time = millis();

      } else if (touching && just_released) {
        // Touch released
        touching = false;

        unsigned long duration = millis() - press_time;
        uint16_t dx = abs(point.x - start_x);
        uint16_t dy = abs(point.y - start_y);

        // Classify gesture
        if (duration > LONG_PRESS_DURATION) {
          result.type = GESTURE_LONG_PRESS;
        } else if (dx < TAP_MAX_DISTANCE && dy < TAP_MAX_DISTANCE) {
          result.type = GESTURE_TAP;
        } else if (dx > dy && dx > SWIPE_MIN_DISTANCE) {
          // Horizontal swipe
          result.type = (point.x > start_x) ?
            GESTURE_SWIPE_RIGHT : GESTURE_SWIPE_LEFT;
        } else if (dy > dx && dy > SWIPE_MIN_DISTANCE) {
          // Vertical swipe
          result.type = (point.y > start_y) ?
            GESTURE_SWIPE_DOWN : GESTURE_SWIPE_UP;
        }

        result.start_x = start_x;
        result.start_y = start_y;
        result.end_x = point.x;
        result.end_y = point.y;
        result.duration = duration;
      }

      return result;
    }
};
```

**Testing Plan:**
- Test each gesture type individually
- Test gesture recognition accuracy
- Measure latency
- Test edge cases

---

### Task 9.5: UI Framework & On-Screen Feedback
**Objective:** Create UI framework for touch feedback
**Estimated Hours:** 14
**Depends On:** Task 9.4
**Acceptance Criteria:**
- [ ] UI rendering working on display
- [ ] Touch target visual feedback
- [ ] Button/area definitions clear
- [ ] Response time <100ms
- [ ] Multiple screen layouts supported
- [ ] Customizable touch regions

**Implementation Details:**

**UI Component Framework:**

```cpp
class UIComponent {
  protected:
    uint16_t x, y, width, height;
    bool enabled = true;

  public:
    virtual ~UIComponent() = default;

    virtual void draw(Display& display) = 0;
    virtual void on_touch(TouchPoint point) = 0;
    virtual bool contains_point(uint16_t tx, uint16_t ty) {
      return (tx >= x && tx < x + width &&
              ty >= y && ty < y + height);
    }
};

class UIButton : public UIComponent {
  private:
    String label;
    void (*callback)() = nullptr;
    bool pressed = false;

  public:
    UIButton(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
             String text, void (*cb)() = nullptr)
      : label(text), callback(cb) {
      this->x = x;
      this->y = y;
      this->width = w;
      this->height = h;
    }

    void draw(Display& display) override {
      uint16_t bg_color = pressed ? 0xFF00 : 0x0000;  // Green/Black
      uint16_t text_color = 0xFFFF;  // White

      // Draw button rectangle
      display.fillRect(x, y, width, height, bg_color);
      display.drawRect(x, y, width, height, 0xFFFF);

      // Draw text
      display.setCursor(x + 5, y + 5);
      display.setTextColor(text_color);
      display.print(label);
    }

    void on_touch(TouchPoint point) override {
      if (contains_point(point.x, point.y)) {
        pressed = true;
        if (callback) callback();
      } else {
        pressed = false;
      }
    }
};

class UIScreen {
  private:
    vector<UIComponent*> components;

  public:
    void add_component(UIComponent* component) {
      components.push_back(component);
    }

    void draw(Display& display) {
      for (auto comp : components) {
        comp->draw(display);
      }
    }

    void on_touch(TouchPoint point) {
      for (auto comp : components) {
        if (comp->contains_point(point.x, point.y)) {
          comp->on_touch(point);
          break;
        }
      }
    }
};
```

**Testing Plan:**
- Render various UI layouts
- Test button responsiveness
- Verify touch hit detection
- Check rendering performance

---

### Task 9.6: State Machine Integration
**Objective:** Integrate touchscreen input with device state machine
**Estimated Hours:** 10
**Depends On:** Tasks 9.4, 9.5
**Acceptance Criteria:**
- [ ] Touch triggers state transitions
- [ ] State-specific touch handlers
- [ ] Device state reflected in UI
- [ ] State machine logic verified
- [ ] All state transitions working
- [ ] Concurrent voice/touch handling

**Implementation Details:**

**State Machine Touch Integration:**

```cpp
class TouchStateHandler {
  private:
    DeviceStateMachine& state_machine;
    UIScreen current_screen;

  public:
    void handle_gesture(Gesture gesture) {
      DeviceState current_state = state_machine.get_state();

      switch (current_state) {
        case STATE_IDLE:
          handle_idle_touch(gesture);
          break;
        case STATE_LISTENING:
          handle_listening_touch(gesture);
          break;
        case STATE_PROCESSING:
          handle_processing_touch(gesture);
          break;
        case STATE_SPEAKING:
          handle_speaking_touch(gesture);
          break;
        default:
          break;
      }
    }

  private:
    void handle_idle_touch(Gesture gesture) {
      // In idle state, show menu
      if (gesture.type == GESTURE_TAP) {
        // Determine which button tapped
        if (is_tap_on_microphone_button(gesture)) {
          state_machine.trigger(EVENT_START_RECORDING);
        }
      }
    }

    void handle_listening_touch(Gesture gesture) {
      // While listening, allow cancel
      if (gesture.type == GESTURE_SWIPE_LEFT) {
        state_machine.trigger(EVENT_CANCEL);
      }
    }

    void handle_speaking_touch(Gesture gesture) {
      // While speaking, allow volume control
      if (gesture.type == GESTURE_SWIPE_UP) {
        increase_volume();
      } else if (gesture.type == GESTURE_SWIPE_DOWN) {
        decrease_volume();
      }
    }
};
```

**Testing Plan:**
- Test state transitions via touch
- Verify all gestures trigger correctly
- Test concurrent voice/touch
- Check state consistency

---

### Task 9.7: Use Case Implementation
**Objective:** Implement specific touch-based use cases
**Estimated Hours:** 16
**Depends On:** Task 9.6
**Acceptance Criteria:**
- [ ] At least 3 use cases fully implemented
- [ ] Use cases documented
- [ ] Use cases tested thoroughly
- [ ] Performance acceptable

**Use Cases to Implement:**

1. **Volume Control via Swipe**
   - Swipe up: increase volume
   - Swipe down: decrease volume
   - Long-press: mute/unmute

2. **Wake Word Toggle**
   - Tap icon to enable/disable wake word
   - Visual feedback (LED/icon change)
   - Settings persistent

3. **Quick Actions Menu**
   - Swipe right to show menu
   - Tap action icons (weather, time, news, etc.)
   - Direct query execution

**Implementation Details for Use Case 1 (Volume Control):**

```cpp
class VolumeControlUseCase {
  private:
    VolumeController& volume;
    UIButton volume_up_btn;
    UIButton volume_down_btn;
    UILabel volume_label;

  public:
    void handle_swipe(Gesture gesture) {
      if (gesture.type == GESTURE_SWIPE_UP) {
        volume.increase_volume();
        LOG_UI("Volume up: %d%%", volume.get_volume());
      } else if (gesture.type == GESTURE_SWIPE_DOWN) {
        volume.decrease_volume();
        LOG_UI("Volume down: %d%%", volume.get_volume());
      } else if (gesture.type == GESTURE_LONG_PRESS) {
        volume.toggle_mute();
      }

      // Update display
      update_volume_display();
    }

  private:
    void update_volume_display() {
      // Show volume level on screen
      int vol = volume.get_volume();
      volume_label.set_text(String(vol) + "%");
    }
};
```

**Testing Plan:**
- Test each use case thoroughly
- Verify user experience
- Check visual feedback
- Performance under various conditions

---

### Task 9.8: Concurrency & Voice/Touch Interaction
**Objective:** Handle simultaneous voice and touch input
**Estimated Hours:** 8
**Depends On:** Tasks 9.5, 9.6
**Acceptance Criteria:**
- [ ] Voice and touch can occur simultaneously
- [ ] No conflicts or data corruption
- [ ] Appropriate precedence handling
- [ ] User experience intuitive
- [ ] System remains stable

**Implementation Details:**

**Concurrent Input Handler:**

```cpp
class ConcurrentInputHandler {
  private:
    AudioInputManager audio;
    TouchInputManager touch;
    DeviceStateMachine state;
    InputPriorityManager priority;

  public:
    void process_inputs() {
      // Get audio input events
      AudioEvent audio_event = audio.get_next_event();

      // Get touch events
      Gesture touch_gesture = touch.get_next_gesture();

      // Determine priority and handle
      if (audio_event.type != AUDIO_EVENT_NONE &&
          touch_gesture.type != GESTURE_NONE) {
        // Both present - determine handling
        if (priority.should_prioritize_audio(audio_event)) {
          handle_audio(audio_event);
          // Queue touch for later or ignore
          if (!priority.can_handle_touch_now()) {
            queue_gesture(touch_gesture);
          } else {
            handle_touch(touch_gesture);
          }
        } else {
          handle_touch(touch_gesture);
          if (priority.can_handle_audio_now()) {
            handle_audio(audio_event);
          }
        }
      } else if (audio_event.type != AUDIO_EVENT_NONE) {
        handle_audio(audio_event);
      } else if (touch_gesture.type != GESTURE_NONE) {
        handle_touch(touch_gesture);
      }
    }
};
```

**Testing Plan:**
- Test simultaneous voice + touch
- Verify no data loss
- Check state consistency
- Test all combinations

---

### Task 9.9: Testing & Validation
**Objective:** Comprehensive testing of touchscreen system
**Estimated Hours:** 12
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] System stability verified
- [ ] Performance metrics met
- [ ] User experience validated
- [ ] Edge cases handled

**Implementation Details:**

**Test Categories:**

1. **Unit Tests:**
   - Touch driver functionality
   - Gesture recognition accuracy
   - UI component rendering
   - State transitions

2. **Integration Tests:**
   - Full touch pipeline
   - Gesture → state transition
   - Concurrent voice/touch
   - UI responsiveness

3. **System Tests:**
   - 24-hour continuous operation
   - Reliability with various interactions
   - Performance under load
   - Edge cases (rapid taps, etc.)

**Testing Plan:**
- Execute comprehensive test suite
- User acceptance testing
- Performance validation

---

### Task 9.10: Documentation & User Guide
**Objective:** Document touchscreen features and usage
**Estimated Hours:** 10
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Hardware documentation complete
- [ ] Feature guide written
- [ ] Use cases documented
- [ ] Troubleshooting guide created
- [ ] Examples provided

**Implementation Details:**

**Documentation Structure:**
1. Touchscreen Hardware Overview
2. Supported Gestures & Interactions
3. Use Cases & Workflows
4. Troubleshooting
5. Developer Guide for Custom Gestures

**Testing Plan:**
- Verify documentation accuracy
- User follows guide successfully

---

## Technical Implementation Details

### Touchscreen Architecture

```
Hardware Touch Controller
    ↓ (I2C interrupt)
Touch Driver
    ↓ (raw data)
Touch Data Parser
    ↓ (touch points)
Gesture Recognizer
    ↓ (gesture events)
State Handler
    ↓ (state changes)
UI Manager (feedback)
    ↓ (visual feedback)
Display
```

### Gesture Recognition Flow

```
Touch Down → Track coordinates
    ↓
Monitor for motion/duration
    ↓
Touch Release → Calculate gesture
    ↓
Classify (tap/swipe/long-press)
    ↓
Trigger action
```

---

## Estimated Timeline

**Week 1 (40 hours):**
- Tasks 9.1-9.2: Hardware research & ESPHome eval (24 hrs)
- Task 9.3: Touch detection (10 hrs)
- Task 9.4: Gesture recognition (6 hrs - carry over)

**Week 2 (40 hours):**
- Task 9.4: Gesture recognition (continued, 6 hrs)
- Task 9.5: UI framework (14 hrs)
- Task 9.6: State integration (10 hrs)
- Task 9.7: Use cases (10 hrs)

**Week 3 (40 hours):**
- Task 9.7: Use cases (continued, 6 hrs)
- Task 9.8: Concurrency (8 hrs)
- Task 9.9: Testing (12 hrs)
- Task 9.10: Documentation (14 hrs)

**Total: ~120 hours (~3 weeks)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Touchscreen hardware incompatible | Medium | High | Research early; prototype |
| ESPHome insufficient for needs | Medium | High | Have Arduino fallback plan |
| Gesture recognition inaccurate | Medium | Medium | Extensive testing; calibration |
| Memory constraints for UI | Low | Medium | Optimize rendering; minimal UI |
| Interference with audio/voice | Low | High | Careful buffer management |
| User experience confusing | Low | Low | User testing; clear documentation |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Touchscreen input recognized
- [ ] Gestures working accurately
- [ ] State transitions via touch
- [ ] UI feedback responsive
- [ ] At least 3 use cases functional

### Performance
- [ ] Touch latency <100ms
- [ ] Gesture recognition <200ms
- [ ] Screen update <100ms
- [ ] No interference with voice

### Reliability
- [ ] No false positives in gesture recognition
- [ ] System stable with continuous touch
- [ ] Concurrent voice/touch working
- [ ] Graceful error handling

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic adds touchscreen interaction as outlined in the enhanced user experience goals. Touch complements voice interaction for complete user control.

**Dependencies Met:** Epic 1, 7, 6
**Enables:** More sophisticated multi-modal interaction patterns

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-07-15 (Epic 8 completion + 3 weeks)
