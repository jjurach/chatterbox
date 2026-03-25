# Epic 10: Continuous Conversation & Wake Word (LOCAL Model) - Project Plan

**Document ID:** EPIC-10-WAKEWORD-2026
**Epic Title:** Continuous Conversation & Wake Word
**Status:** Planned
**Target Completion:** 2026-08-04
**Estimated Duration:** 2 weeks (~80 hours)
**Last Updated:** 2026-03-24
**Wake Word Strategy:** Use box3b's LOCAL voice model (no streaming to Home Assistant)

---

## Executive Summary

Epic 10 implements always-listening wake word detection and continuous conversation capabilities, transforming the device from a push-to-talk system into a true voice assistant that responds to voice activation. Wake word detection runs locally on the box3b device using a local voice model (no streaming to Home Assistant), ensuring privacy and low latency. The device listens for a customizable wake word, automatically transitions to recording when detected, processes audio through the full pipeline, and returns to idle listening after the conversation completes. This epic includes wake word model selection, integration, calibration, and 5-second red light state indication.

---

## Goals & Success Criteria

### Primary Goals
1. Implement always-listening wake word detection
2. Support custom/configurable wake words
3. Automatic state transitions on wake detection
4. Implement 5-second red light "listening" indicator
5. Handle false positive/negative rates
6. Enable continuous conversation workflows
7. Maintain low power consumption in listen mode
8. Integrate with existing voice pipeline

### Success Criteria
- [ ] Wake word detection latency <500ms
- [ ] False positive rate <2% (1 per 50 utterances)
- [ ] False negative rate <10% (1 per 10 wake words)
- [ ] Detection confidence >0.8 threshold
- [ ] Red light activates within 100ms of wake
- [ ] Red light deactivates appropriately after response
- [ ] Multiple wake words supported
- [ ] Custom wake word training possible
- [ ] Continuous conversation without push-button
- [ ] Power consumption in listen mode <500mW
- [ ] System stable over extended operation

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 7 (Recording & PCM Streaming):** Audio input pipeline
- **Epic 8 (Playback):** Audio output for responses
- **Epic 6 (Backend Deployment):** LLM processing backend

### Prerequisites
- Wake word model available (e.g., PocketSphinx, microWakeWord)
- LED for red light indicator controlled
- Audio preprocessing stable
- Device state machine operational
- Network connectivity maintained

### Blockers to Identify
- Wake word model accuracy on device
- Processing power constraints
- False positive rates in home environment
- Model size on device storage

---

## Detailed Task Breakdown

### Task 10.1: Wake Word Model Selection & Research
**Objective:** Research and select optimal wake word model
**Estimated Hours:** 8
**Acceptance Criteria:**
- [ ] Wake word models evaluated (PocketSphinx, microWakeWord, TinyWakeWord)
- [ ] Model accuracy compared
- [ ] Resource requirements analyzed
- [ ] Selection documented with rationale
- [ ] Model downloaded and prepared
- [ ] Custom wake word training capability evaluated

**Implementation Details:**

**Model Evaluation Matrix:**

| Aspect | PocketSphinx | microWakeWord | TinyWakeWord |
|--------|---|---|---|
| Accuracy | Medium | High | Very High |
| CPU Usage | Medium | Low | Very Low |
| Memory (ROM) | Large | Medium | Small |
| Custom Training | Yes | Limited | Limited |
| WLAN Dependency | No | No | No |

**Model Characteristics:**

```python
# microWakeWord (Recommended)
# - Optimized for on-device inference
# - Pre-trained models available
# - ~50KB model size
# - Accuracy 95%+

# PocketSphinx
# - Open-source speech recognition
# - Large model (5MB+)
# - More flexibility for custom training
# - Accuracy 85-90%

# TinyWakeWord
# - Very small model (<10KB)
# - ESP32 optimized
# - Limited pre-trained models
# - Accuracy ~90%
```

**Testing Plan:**
- Test each model with sample audio
- Measure accuracy on device
- Evaluate false positive rates
- Check resource consumption

---

### Task 10.2: Wake Word Model Integration on Device
**Objective:** Integrate selected wake word model on ESP32
**Estimated Hours:** 10
**Depends On:** Task 10.1
**Acceptance Criteria:**
- [ ] Model loaded into device memory
- [ ] Inference running on device
- [ ] Detection latency <500ms
- [ ] Model compatible with available RAM
- [ ] Model loading on startup working
- [ ] Model updates possible via OTA

**Implementation Details:**

**Wake Word Detector with microWakeWord:**

```cpp
#include <MicroWakeWord.h>

class WakeWordDetector {
  private:
    MicroWakeWord* ww_detector = nullptr;
    const char* WAKE_WORDS[] = {"hey cackle", "hey google"};
    const int NUM_WAKE_WORDS = 2;
    int current_ww_index = 0;

    // Confidence threshold
    const float CONFIDENCE_THRESHOLD = 0.8f;

    // Detection smoothing (avoid bouncing)
    int consecutive_detections = 0;
    const int DETECTION_THRESHOLD = 2;  // Need 2 consecutive detections

  public:
    bool initialize() {
      // Load wake word model
      const char* model_path = "/spiffs/hey_cackle.model";

      ww_detector = new MicroWakeWord(model_path);

      if (!ww_detector->begin()) {
        LOG_WAKEWORD_ERROR("Failed to initialize wake word detector");
        return false;
      }

      LOG_WAKEWORD_INFO("Wake word detector initialized");
      return true;
    }

    bool detect_wake_word(const int16_t* audio_samples, size_t sample_count) {
      if (!ww_detector) return false;

      // Run inference
      float confidence = ww_detector->detect(audio_samples, sample_count);

      // Check if confidence exceeds threshold
      if (confidence > CONFIDENCE_THRESHOLD) {
        consecutive_detections++;

        if (consecutive_detections >= DETECTION_THRESHOLD) {
          LOG_WAKEWORD_INFO("Wake word detected! Confidence: %.2f", confidence);
          consecutive_detections = 0;
          return true;
        }
      } else {
        consecutive_detections = 0;
      }

      return false;
    }

    float get_confidence() {
      return ww_detector ? ww_detector->get_confidence() : 0.0f;
    }

    void set_wake_word(int index) {
      if (index >= 0 && index < NUM_WAKE_WORDS) {
        current_ww_index = index;
        LOG_WAKEWORD_INFO("Wake word changed to: %s", WAKE_WORDS[index]);
      }
    }

    ~WakeWordDetector() {
      if (ww_detector) delete ww_detector;
    }
};
```

**Memory-Efficient Model Loading:**

```cpp
// Load model from flash/SPIFFS
bool load_model_from_spiffs() {
  File model_file = SPIFFS.open("/models/hey_cackle.model", "r");

  if (!model_file) {
    LOG_ERROR("Model file not found");
    return false;
  }

  size_t model_size = model_file.size();
  LOG_INFO("Model size: %d bytes", model_size);

  // Check available memory
  if (ESP.getFreeHeap() < model_size + 100000) {  // Need headroom
    LOG_ERROR("Not enough memory for model");
    return false;
  }

  // Load into memory
  uint8_t* model_data = new uint8_t[model_size];
  model_file.readBytes((char*)model_data, model_size);
  model_file.close();

  // Pass to detector
  return true;
}
```

**Testing Plan:**
- Load model successfully
- Run inference on test audio
- Measure latency
- Check memory usage
- Verify accuracy

---

### Task 10.3: Continuous Audio Processing for Wake Word
**Objective:** Implement continuous monitoring pipeline
**Estimated Hours:** 8
**Depends On:** Tasks 10.2, 7.1
**Acceptance Criteria:**
- [ ] Continuous audio capture from microphone
- [ ] Processing doesn't interfere with recording
- [ ] Memory usage stable (no leaks)
- [ ] Low CPU usage during listening (<30%)
- [ ] Efficient buffer management
- [ ] Audio quality maintained

**Implementation Details:**

**Continuous Listening Manager:**

```cpp
class ContinuousListeningManager {
  private:
    AudioRecorder recorder;
    WakeWordDetector wake_detector;
    CircularBuffer<int16_t> listening_buffer;
    const int WINDOW_SIZE = 512;  // 32ms at 16kHz

    TaskHandle_t listening_task_handle = nullptr;
    bool listening_enabled = true;

  public:
    bool initialize() {
      if (!recorder.initialize()) {
        return false;
      }

      if (!wake_detector.initialize()) {
        return false;
      }

      return true;
    }

    void start_listening() {
      if (listening_task_handle != nullptr) return;

      listening_enabled = true;

      xTaskCreatePinnedToCore(
        listening_task_static,
        "listening",
        4096,
        this,
        2,
        &listening_task_handle,
        1  // Core 1
      );
    }

    void stop_listening() {
      listening_enabled = false;

      if (listening_task_handle != nullptr) {
        vTaskDelete(listening_task_handle);
        listening_task_handle = nullptr;
      }
    }

    static void listening_task_static(void* pvParameters) {
      ContinuousListeningManager* self = (ContinuousListeningManager*)pvParameters;
      self->listening_loop();
    }

  private:
    void listening_loop() {
      int16_t audio_window[WINDOW_SIZE];

      while (listening_enabled) {
        // Read audio chunk
        int samples_read = recorder.read_samples(audio_window, WINDOW_SIZE);

        if (samples_read > 0) {
          // Add to buffer for wake word detection
          listening_buffer.write(audio_window, samples_read);

          // Run wake word detection on window
          if (wake_detector.detect_wake_word(audio_window, samples_read)) {
            // Wake word detected!
            on_wake_word_detected();
          }

          // Log statistics periodically
          static int frame_count = 0;
          if (++frame_count % 500 == 0) {  // Every ~16 seconds
            LOG_WAKEWORD_DEBUG("Listening active, heap: %d bytes",
                               ESP.getFreeHeap());
          }
        }

        // Yield to other tasks
        vTaskDelay(pdMS_TO_TICKS(5));
      }
    }

    void on_wake_word_detected() {
      LOG_WAKEWORD_INFO("Wake word detected!");

      // Trigger recording state
      state_machine.trigger(EVENT_WAKE_WORD_DETECTED);

      // Signal UI/LED
      signal_wake_detected();
    }

    void signal_wake_detected() {
      // Turn on red light
      // Play confirmation sound
      // Update display
    }
};
```

**Testing Plan:**
- Run continuous listening for hours
- Monitor memory usage
- Check CPU usage
- Verify no interference with recording

---

### Task 10.4: Red Light State Indicator
**Objective:** Implement visual feedback for device state
**Estimated Hours:** 6
**Depends On:** Task 10.3
**Acceptance Criteria:**
- [ ] Red light activates within 100ms of wake word
- [ ] Red light stays on during listening (5 seconds max)
- [ ] Red light off during idle
- [ ] Different LED patterns for different states
- [ ] PWM brightness control
- [ ] Configuration for LED behavior

**Implementation Details:**

**LED State Manager:**

```cpp
enum LedState {
  LED_IDLE,
  LED_LISTENING,
  LED_PROCESSING,
  LED_SPEAKING,
  LED_ERROR
};

class LEDManager {
  private:
    const int LED_PIN = 2;
    LedState current_state = LED_IDLE;
    unsigned long state_start_time = 0;

    // LED brightness (PWM 0-255)
    const int BRIGHTNESS_IDLE = 0;
    const int BRIGHTNESS_LISTENING = 255;  // Full red
    const int BRIGHTNESS_PROCESSING = 128; // Half brightness
    const int BRIGHTNESS_SPEAKING = 64;    // Dim

  public:
    void initialize() {
      pinMode(LED_PIN, OUTPUT);
      ledcSetup(0, 5000, 8);  // 5kHz, 8-bit PWM
      ledcAttachPin(LED_PIN, 0);

      digitalWrite(LED_PIN, LOW);  // Start off
    }

    void set_state(LedState state) {
      if (state == current_state) return;

      current_state = state;
      state_start_time = millis();

      update_led();
    }

    void update_led() {
      int brightness = 0;

      switch (current_state) {
        case LED_IDLE:
          brightness = BRIGHTNESS_IDLE;
          break;

        case LED_LISTENING: {
          // Blink pattern for listening
          unsigned long elapsed = millis() - state_start_time;
          int phase = (elapsed / 200) % 3;  // 200ms per phase
          brightness = (phase < 2) ? BRIGHTNESS_LISTENING : 50;
          break;
        }

        case LED_PROCESSING:
          brightness = BRIGHTNESS_PROCESSING;
          break;

        case LED_SPEAKING:
          brightness = BRIGHTNESS_SPEAKING;
          break;

        case LED_ERROR:
          // Fast blink for error
          brightness = ((millis() / 100) % 2) ? 255 : 0;
          break;

        default:
          brightness = 0;
      }

      ledcWrite(0, brightness);

      // Timeout for listening state (5 seconds max)
      if (current_state == LED_LISTENING) {
        unsigned long elapsed = millis() - state_start_time;
        if (elapsed > 5000) {
          set_state(LED_IDLE);
        }
      }
    }

    LedState get_state() {
      return current_state;
    }

    // Call periodically to update blinking patterns
    void tick() {
      update_led();
    }
};
```

**State Machine Integration:**

```cpp
// In device state machine
void on_state_change(DeviceState new_state) {
  switch (new_state) {
    case STATE_LISTENING:
      led_manager.set_state(LED_LISTENING);
      break;
    case STATE_PROCESSING:
      led_manager.set_state(LED_PROCESSING);
      break;
    case STATE_SPEAKING:
      led_manager.set_state(LED_SPEAKING);
      break;
    case STATE_IDLE:
      led_manager.set_state(LED_IDLE);
      break;
    case STATE_ERROR:
      led_manager.set_state(LED_ERROR);
      break;
  }
}
```

**Testing Plan:**
- Verify LED behavior in each state
- Check timing accuracy
- Test brightness levels
- Verify state transitions

---

### Task 10.5: False Positive/Negative Mitigation
**Objective:** Minimize false detections through calibration and filtering
**Estimated Hours:** 10
**Depends On:** Task 10.3
**Acceptance Criteria:**
- [ ] False positive rate <2%
- [ ] False negative rate <10%
- [ ] Confidence threshold calibrated
- [ ] Environmental adaptation working
- [ ] Background noise handling
- [ ] Confidence scores logged

**Implementation Details:**

**Confidence Filtering & Adaptation:**

```cpp
class WakeWordFilter {
  private:
    // Confidence history for smoothing
    static const int HISTORY_SIZE = 10;
    float confidence_history[HISTORY_SIZE];
    int history_index = 0;

    // Environment adaptation
    float dynamic_threshold = 0.8f;
    float background_noise_level = 0.0f;

    // Statistics
    int total_detections = 0;
    int false_positives = 0;
    int false_negatives = 0;

  public:
    bool should_trigger_wake(float confidence) {
      // Add to history
      confidence_history[history_index] = confidence;
      history_index = (history_index + 1) % HISTORY_SIZE;

      // Calculate smoothed confidence
      float smoothed = calculate_smoothed_confidence();

      // Adapt threshold based on environment
      adapt_threshold();

      // Trigger if meets threshold with smoothing
      bool should_trigger = smoothed > dynamic_threshold &&
                            confidence > dynamic_threshold * 0.9f;

      if (should_trigger) {
        total_detections++;
      }

      return should_trigger;
    }

  private:
    float calculate_smoothed_confidence() {
      float sum = 0.0f;
      for (int i = 0; i < HISTORY_SIZE; i++) {
        sum += confidence_history[i];
      }
      return sum / HISTORY_SIZE;
    }

    void adapt_threshold() {
      // Lower threshold if in high-noise environment
      if (background_noise_level > 0.5f) {
        dynamic_threshold = 0.75f;
      } else {
        dynamic_threshold = 0.80f;
      }

      // Log occasionally
      static int tick_count = 0;
      if (++tick_count % 1000 == 0) {
        LOG_WAKEWORD_DEBUG("Dynamic threshold: %.2f", dynamic_threshold);
      }
    }

  public:
    void log_false_positive() {
      false_positives++;
      LOG_WAKEWORD_WARN("False positive detected. Total: %d", false_positives);
    }

    void log_false_negative() {
      false_negatives++;
      LOG_WAKEWORD_WARN("False negative detected. Total: %d", false_negatives);
    }

    void print_statistics() {
      float fp_rate = total_detections > 0 ?
        (float)false_positives / total_detections * 100 : 0;
      Serial.printf("Wake word statistics:\n");
      Serial.printf("  Total detections: %d\n", total_detections);
      Serial.printf("  False positives: %d (%.1f%%)\n", false_positives, fp_rate);
      Serial.printf("  False negatives: %d\n", false_negatives);
    }
};
```

**Testing Plan:**
- Test in quiet environment
- Test in noisy environment
- Record false positive/negative rates
- Calibrate thresholds
- Evaluate background noise adaptation

---

### Task 10.6: Continuous Conversation Workflow
**Objective:** Enable multi-turn conversations without push-button
**Estimated Hours:** 8
**Depends On:** Tasks 10.3, 10.4
**Acceptance Criteria:**
- [ ] Wake word triggers conversation
- [ ] Multiple turns supported (ask follow-up questions)
- [ ] Auto-detect conversation end
- [ ] Return to idle listening when done
- [ ] Timeout handling (5-10 seconds of silence)
- [ ] User can interrupt with new wake word

**Implementation Details:**

**Conversation State Handler:**

```cpp
class ConversationStateHandler {
  private:
    enum ConversationPhase {
      PHASE_IDLE,
      PHASE_LISTENING_FOR_QUERY,
      PHASE_SENDING_TO_LLM,
      PHASE_RECEIVING_RESPONSE,
      PHASE_SPEAKING_RESPONSE,
      PHASE_WAITING_FOR_FOLLOWUP
    };

    ConversationPhase phase = PHASE_IDLE;
    unsigned long last_audio_time = 0;
    const unsigned long FOLLOWUP_TIMEOUT = 5000;  // 5 seconds of silence

  public:
    void on_wake_word_detected() {
      LOG_CONVERSATION("Wake word detected, starting conversation");
      phase = PHASE_LISTENING_FOR_QUERY;
      device_state.set_state(STATE_LISTENING);
      led_manager.set_state(LED_LISTENING);

      // Start recording
      audio_manager.start_recording();
    }

    void on_audio_received(const vector<int16_t>& audio) {
      last_audio_time = millis();

      if (phase == PHASE_LISTENING_FOR_QUERY) {
        // Accumulate audio for STT
        accumulate_audio(audio);
      } else if (phase == PHASE_WAITING_FOR_FOLLOWUP) {
        // Check if new query or just silence
        if (is_speech_detected(audio)) {
          phase = PHASE_LISTENING_FOR_QUERY;
        }
      }
    }

    void on_transcription_complete(const String& text) {
      LOG_CONVERSATION("Transcribed: %s", text.c_str());
      phase = PHASE_SENDING_TO_LLM;

      // Stop recording
      audio_manager.stop_recording();

      // Send to backend
      backend.process_query(text);
    }

    void on_llm_response_complete(const String& response) {
      LOG_CONVERSATION("LLM response received, playing");
      phase = PHASE_SPEAKING_RESPONSE;

      // Play response audio
      audio_player.play_tts(response);
    }

    void on_playback_complete() {
      LOG_CONVERSATION("Response complete, waiting for followup");
      phase = PHASE_WAITING_FOR_FOLLOWUP;
      last_audio_time = millis();

      // Continue listening for follow-up question
      audio_manager.start_recording();
    }

    void tick() {
      // Check for timeout waiting for followup
      if (phase == PHASE_WAITING_FOR_FOLLOWUP) {
        unsigned long elapsed = millis() - last_audio_time;

        if (elapsed > FOLLOWUP_TIMEOUT) {
          LOG_CONVERSATION("Followup timeout, returning to idle");
          phase = PHASE_IDLE;
          device_state.set_state(STATE_IDLE);
          audio_manager.stop_recording();
          led_manager.set_state(LED_IDLE);
        }
      }
    }

  private:
    void accumulate_audio(const vector<int16_t>& audio) {
      // Buffer audio for STT
    }

    bool is_speech_detected(const vector<int16_t>& audio) {
      // Simple energy-based detection
      float energy = 0.0f;
      for (auto sample : audio) {
        energy += sample * sample;
      }
      return energy > SPEECH_ENERGY_THRESHOLD;
    }
};
```

**Testing Plan:**
- Test wake word triggers conversation
- Test multi-turn conversation
- Test timeout handling
- Test return to idle listening
- Test interruption with new wake word

---

### Task 10.7: Custom Wake Word Training (Optional)
**Objective:** Enable users to define custom wake words
**Estimated Hours:** 8 (Optional)
**Depends On:** Task 10.2
**Acceptance Criteria (if implemented):**
- [ ] Process for custom wake word training documented
- [ ] Training data collection working
- [ ] Model fine-tuning possible
- [ ] Updated model deployed via OTA

**Implementation Details:**

**Custom Wake Word Training (Future Enhancement):**

```markdown
## Custom Wake Word Training Process

1. Collect training data:
   - User records wake word 10+ times
   - Various speaking styles, distances, accents
   - Background conditions

2. Fine-tune model:
   - Use TensorFlow Lite Model Maker
   - Transfer learning from pre-trained model
   - Optimize for device

3. Deploy:
   - Package as .tflite model
   - Deploy via OTA update
   - Test and validate

## Timeline: Post-Epic 10
```

---

### Task 10.8: Integration & System Testing
**Objective:** End-to-end testing of continuous listening and conversations
**Estimated Hours:** 12
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Full conversation flow working end-to-end
- [ ] Wake word detection reliable
- [ ] Continuous listening stable
- [ ] All metrics met (latency, accuracy, power)
- [ ] System stable over extended operation
- [ ] Edge cases handled

**Implementation Details:**

**Integration Test Suite:**

```cpp
void test_continuous_conversation() {
  // Setup
  listener.start_listening();
  Serial.println("Test 1: Wake word detection");

  // Simulate wake word audio
  // (In real test, would use actual microphone or pre-recorded audio)
  // Expected: LED goes red, listening starts

  Serial.println("Test 2: Multi-turn conversation");
  // Simulate conversation flow
  // Wake word → query → response → followup → response → idle

  Serial.println("Test 3: False positive mitigation");
  // Play speech that isn't wake word
  // Expected: No false trigger

  Serial.println("Test 4: Timeout handling");
  // After response, wait 5+ seconds
  // Expected: Return to idle

  Serial.println("Test 5: Extended operation (8 hours)");
  // Monitor for memory leaks, stability
  // Expected: Stable operation, <5% CPU, <500mW power
}

void test_statistics() {
  // Run 1000 test utterances
  // Track:
  // - Detection rate
  // - False positive rate
  // - False negative rate
  // - Average latency
  // - Power consumption
}
```

**Performance Benchmarks:**

```cpp
void benchmark_wake_word_latency() {
  // Measure time from wake word utterance to LED activation
  unsigned long start = micros();
  // Simulate wake word detection
  listener.detect_wake_word(test_audio, 512);
  unsigned long elapsed = micros() - start;

  Serial.printf("Wake word latency: %lu us\n", elapsed);
  assert(elapsed < 500000);  // <500ms
}

void benchmark_memory_usage() {
  uint32_t heap_start = ESP.getFreeHeap();
  listener.start_listening();
  delay(10000);  // Run for 10 seconds
  uint32_t heap_after = ESP.getFreeHeap();

  Serial.printf("Heap before: %u, after: %u, used: %u\n",
                heap_start, heap_after, heap_start - heap_after);

  assert((heap_start - heap_after) < 10000);  // <10KB leakage
}

void benchmark_power_consumption() {
  // Measure current draw during continuous listening
  // Setup ADC on current measurement pin
  // Expected: <500mW
}
```

**Testing Plan:**
- Execute full integration test suite
- Run 8-hour stability test
- Measure all key metrics
- Document results

---

### Task 10.9: Documentation & User Guide
**Objective:** Document wake word and continuous conversation features
**Estimated Hours:** 8
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Wake word feature documented
- [ ] Continuous conversation explained
- [ ] User guide created
- [ ] Troubleshooting guide written
- [ ] Configuration options documented
- [ ] Examples provided

**Implementation Details:**

**Documentation Structure:**
1. Always-Listening Overview
2. Wake Word Configuration
3. Continuous Conversation Workflow
4. LED States & Meanings
5. Troubleshooting False Positives/Negatives
6. Power Consumption Info
7. Advanced Configuration

**Testing Plan:**
- Verify documentation accuracy
- Follow guide successfully

---

## Technical Implementation Details

### Always-Listening Architecture

```
┌─────────────────┐
│  Microphone     │
└────────┬────────┘
         │ (16kHz audio)
    ┌────▼─────────┐
    │ Audio Buffer │
    └────┬─────────┘
         │ (512 samples = 32ms chunks)
    ┌────▼─────────────────┐
    │ Wake Word Detector    │ (always running)
    └────┬─────────────────┘
         │ (confidence score)
    ┌────▼──────────────┐
    │ Confidence Filter │ (smoothing, thresholding)
    └────┬──────────────┘
         │ (detection event)
    ┌────▼──────────────┐
    │ State Transition  │
    └────┬──────────────┘
         │ (trigger recording state)
    ┌────▼──────────────┐
    │ LED & Audio       │ (visual/audio feedback)
    └───────────────────┘
```

### Continuous Listening Power Profile

```
Listening State:
  - Audio capture: 80mW
  - Wake word inference: 150mW
  - Misc (LEDs, comms): 50mW
  - Total: ~280mW

Recording State:
  - All of above + transmission: ~400mW

Speaking State:
  - Audio playback: 150mW
  - Display: 100mW
  - Misc: 50mW
  - Total: ~300mW
```

---

## Estimated Timeline

**Week 1 (40 hours):**
- Task 10.1: Model selection (8 hrs)
- Task 10.2: Model integration (10 hrs)
- Task 10.3: Continuous processing (8 hrs)
- Task 10.4: LED manager (6 hrs)
- Task 10.5: Filter/mitigation (8 hrs - carry over)

**Week 2 (40 hours):**
- Task 10.5: Filter/mitigation (continued, 2 hrs)
- Task 10.6: Continuous conversation (8 hrs)
- Task 10.7: Custom training research (4 hrs - optional)
- Task 10.8: Integration testing (12 hrs)
- Task 10.9: Documentation (14 hrs)

**Total: ~80 hours (~2 weeks)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Wake word accuracy poor | Medium | High | Test extensively; calibrate thresholds |
| High false positive rate | Medium | High | Implement filtering; confidence smoothing |
| Power consumption too high | Low | Medium | Optimize inference; lower sampling rate |
| Background noise issues | Medium | Low | Noise adaptation; environmental testing |
| Model size too large | Low | Medium | Model quantization; OTA streaming |
| Interference with voice | Low | High | Careful buffer management; testing |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Wake word detection working reliably
- [ ] Continuous conversation enabled
- [ ] LED feedback functioning
- [ ] Red light state management correct
- [ ] Timeout handling working

### Performance
- [ ] Detection latency <500ms
- [ ] LED response <100ms
- [ ] Conversation latency <5 seconds
- [ ] Power consumption <500mW listening

### Reliability
- [ ] False positive rate <2%
- [ ] False negative rate <10%
- [ ] System stable 8+ hours
- [ ] No memory leaks

### Accuracy
- [ ] Wake word detection >90% accuracy
- [ ] Confidence threshold calibrated
- [ ] Environmental adaptation working

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic transforms the system from push-to-talk to always-listening as outlined in Phase 4 goals. Wake word detection enables true voice assistant behavior and continuous conversation workflows.

**Dependencies Met:** Epic 7, 8 (audio I/O)
**Enables:** Full voice assistant capabilities, user-friendly interaction

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-08-04 (Epic 9 completion + 2 weeks)
