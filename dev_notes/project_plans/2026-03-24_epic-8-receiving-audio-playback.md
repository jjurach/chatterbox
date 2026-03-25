# Epic 8: Receiving & Audio Playback - Project Plan

**Document ID:** EPIC-8-PLAYBACK-2026
**Epic Title:** Receiving & Audio Playback
**Status:** Planned
**Target Completion:** 2026-06-23
**Estimated Duration:** 1.5 weeks (~60 hours)
**Last Updated:** 2026-03-24

---

## Executive Summary

Epic 8 implements the return audio path, enabling the backend to send audio responses back to the ESP32-S3-BOX-3B device for playback through the speaker. This epic completes the bidirectional audio communication flow, allowing users to hear LLM responses. The focus is on receiving PCM audio from the backend, managing playback buffers, audio quality, speaker management, and handling transition sounds.

---

## Goals & Success Criteria

### Primary Goals
1. Receive audio responses from backend via Wyoming protocol
2. Implement efficient playback buffer management
3. Support speaker playback with proper volume control
4. Add transition sounds (start, end, error tones)
5. Handle concurrent playback and recording
6. Ensure audio quality matches input quality
7. Enable customization of voice responses

### Success Criteria
- [ ] Audio received from backend without data loss
- [ ] Playback latency <1 second from reception
- [ ] Speaker output at appropriate volume levels
- [ ] Transition sounds working correctly
- [ ] No interference between recording and playback
- [ ] Multiple audio streams supported
- [ ] Error audio played on failures
- [ ] Volume control functional and persistent
- [ ] Audio format compatibility validated
- [ ] System handles silence correctly

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 7 (Recording & PCM Streaming):** Recording working, audio format established
- **Epic 6 (Backend Deployment):** Backend ready to send responses
- **Wyoming Protocol:** Bidirectional communication functional

### Prerequisites
- ESP32-S3-BOX-3B speaker output working
- I2S driver for audio output configured
- Audio file format for transitions (WAV preferred)
- Speaker amplifier functional
- Volume control hardware (DAC or PWM)

### Blockers to Identify
- Speaker hardware issues
- Audio output buffering constraints
- Timing synchronization between input/output

---

## Detailed Task Breakdown

### Task 8.1: I2S Audio Output Configuration
**Objective:** Configure audio output on ESP32-S3-BOX-3B
**Estimated Hours:** 6
**Acceptance Criteria:**
- [ ] I2S output driver initialized
- [ ] Speaker responding to output
- [ ] Audio output at 16kHz, 16-bit, mono
- [ ] Volume control functional
- [ ] Output quality acceptable
- [ ] No distortion or clipping

**Implementation Details:**

**I2S Output Setup:**

```cpp
class AudioOutput {
  private:
    const int I2S_PORT = I2S_NUM_0;
    const int SAMPLE_RATE = 16000;
    const int BITS_PER_SAMPLE = 16;

    // I2S pin configuration
    const int BCK_PIN = 8;     // Bit clock
    const int WS_PIN = 9;      // Word select
    const int DOUT_PIN = 10;   // Data out
    const int MCLK_PIN = 11;   // Master clock

  public:
    bool initialize() {
      i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 512,
        .use_apll = true,
        .fixed_mclk = I2S_FIXED_MCLK0,
      };

      i2s_pin_config_t pin_config = {
        .bck_io_num = BCK_PIN,
        .ws_io_num = WS_PIN,
        .data_out_num = DOUT_PIN,
        .data_in_num = -1,        // Not used (TX only)
        .mck_io_num = MCLK_PIN,
      };

      // Install driver
      esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, nullptr);
      if (err != ESP_OK) {
        Serial.printf("I2S TX install failed: %s\n", esp_err_to_name(err));
        return false;
      }

      // Set pins
      err = i2s_set_pin(I2S_PORT, &pin_config);
      if (err != ESP_OK) {
        Serial.printf("I2S set pin failed: %s\n", esp_err_to_name(err));
        return false;
      }

      return true;
    }

    bool play_audio(const int16_t* data, size_t sample_count) {
      size_t bytes_written = 0;

      esp_err_t err = i2s_write(
        I2S_PORT,
        data,
        sample_count * sizeof(int16_t),
        &bytes_written,
        portMAX_DELAY
      );

      return (err == ESP_OK && bytes_written > 0);
    }
};
```

**Testing Plan:**
- Verify speaker produces sound
- Test output quality
- Check for distortion
- Measure output levels

---

### Task 8.2: Playback Buffer Management
**Objective:** Implement buffer for receiving and buffering audio for playback
**Estimated Hours:** 8
**Depends On:** Task 8.1
**Acceptance Criteria:**
- [ ] Playback buffer implemented
- [ ] No buffer overruns
- [ ] Handles asynchronous reception and playback
- [ ] Smooth audio without gaps
- [ ] Thread-safe operations
- [ ] Memory efficient

**Implementation Details:**

**Ring Buffer for Playback:**

```cpp
class PlaybackBuffer {
  private:
    static const size_t BUFFER_SIZE = 65536;  // 2 seconds at 16kHz
    int16_t buffer[BUFFER_SIZE];
    volatile size_t write_ptr = 0;
    volatile size_t read_ptr = 0;
    SemaphoreHandle_t mutex;
    SemaphoreHandle_t data_available;

  public:
    PlaybackBuffer() {
      mutex = xSemaphoreCreateMutex();
      data_available = xSemaphoreCreateBinary();
    }

    bool write(const int16_t* data, size_t count) {
      if (!xSemaphoreTake(mutex, portMAX_DELAY)) return false;

      // Check space
      size_t available = get_available_write_space_unsafe();
      if (available < count) {
        xSemaphoreGive(mutex);
        return false;
      }

      // Write with wraparound
      for (size_t i = 0; i < count; i++) {
        buffer[write_ptr] = data[i];
        write_ptr = (write_ptr + 1) % BUFFER_SIZE;
      }

      xSemaphoreGive(mutex);
      xSemaphoreGive(data_available);  // Signal data available

      return true;
    }

    size_t read(int16_t* output, size_t count) {
      // Wait for data if empty
      if (get_fill_level() == 0) {
        xSemaphoreTake(data_available, pdMS_TO_TICKS(100));
      }

      if (!xSemaphoreTake(mutex, portMAX_DELAY)) return 0;

      size_t available = get_available_read_space_unsafe();
      size_t to_read = (count < available) ? count : available;

      for (size_t i = 0; i < to_read; i++) {
        output[i] = buffer[read_ptr];
        read_ptr = (read_ptr + 1) % BUFFER_SIZE;
      }

      xSemaphoreGive(mutex);
      return to_read;
    }

    size_t get_fill_level() {
      xSemaphoreTake(mutex, portMAX_DELAY);
      size_t level = get_available_read_space_unsafe();
      xSemaphoreGive(mutex);
      return level;
    }

  private:
    size_t get_available_read_space_unsafe() {
      if (write_ptr >= read_ptr) {
        return write_ptr - read_ptr;
      } else {
        return BUFFER_SIZE - read_ptr + write_ptr;
      }
    }

    size_t get_available_write_space_unsafe() {
      return BUFFER_SIZE - get_available_read_space_unsafe() - 1;
    }
};
```

**Testing Plan:**
- Test fill/drain under various conditions
- Test wraparound behavior
- Measure latency
- Test thread safety

---

### Task 8.3: Wyoming Audio Reception
**Objective:** Receive audio responses from backend via Wyoming
**Estimated Hours:** 8
**Depends On:** Task 8.2
**Acceptance Criteria:**
- [ ] Audio received from Wyoming service
- [ ] Correct format handling
- [ ] No data loss
- [ ] Handles incomplete packets
- [ ] Reconnection on network failure
- [ ] Data logged for debugging

**Implementation Details:**

**Audio Reception Handler:**

```cpp
class AudioReceptionService {
  private:
    WiFiClient wyoming_client;
    PlaybackBuffer& playback_buffer;
    bool connected = false;

  public:
    AudioReceptionService(PlaybackBuffer& buffer) : playback_buffer(buffer) {}

    bool start_listening() {
      // Start reception task
      xTaskCreatePinnedToCore(
        reception_task,
        "audio_rx",
        4096,
        this,
        3,
        nullptr,
        1
      );
      return true;
    }

    static void reception_task(void* pvParameters) {
      AudioReceptionService* self = (AudioReceptionService*)pvParameters;
      self->receive_loop();
    }

    void receive_loop() {
      uint8_t buffer[2048];

      while (true) {
        // Ensure connected
        if (!connected) {
          if (!wyoming_client.connect(WYOMING_HOST, WYOMING_PORT)) {
            delay(1000);
            continue;
          }
          connected = true;
          LOG_AUDIO("Wyoming RX: Connected");
        }

        // Read from Wyoming
        int bytes_available = wyoming_client.available();
        if (bytes_available > 0) {
          int bytes_read = wyoming_client.read(buffer, sizeof(buffer));

          // Parse audio packets
          parse_audio_packets(buffer, bytes_read);
        }

        vTaskDelay(pdMS_TO_TICKS(10));

        // Check connection
        if (!wyoming_client.connected()) {
          connected = false;
          LOG_AUDIO("Wyoming RX: Disconnected");
        }
      }
    }

  private:
    void parse_audio_packets(uint8_t* data, size_t length) {
      for (size_t i = 0; i < length; i += 2) {
        if (i + 1 < length) {
          int16_t sample = (int16_t)(data[i] | (data[i+1] << 8));

          // Add to playback buffer
          if (!playback_buffer.write(&sample, 1)) {
            LOG_AUDIO_ERROR("Playback buffer full!");
          }
        }
      }
    }
};
```

**Testing Plan:**
- Verify audio packets received correctly
- Test with various packet sizes
- Verify format conversion
- Test error handling

---

### Task 8.4: Speaker Playback Management
**Objective:** Manage speaker playback from buffer
**Estimated Hours:** 6
**Depends On:** Tasks 8.1, 8.2, 8.3
**Acceptance Criteria:**
- [ ] Continuous playback from buffer
- [ ] Smooth audio without dropouts
- [ ] Proper ending of playback
- [ ] Silence handling
- [ ] No audio artifacts
- [ ] Resource efficient

**Implementation Details:**

**Playback Manager:**

```cpp
class PlaybackManager {
  private:
    AudioOutput audio_output;
    PlaybackBuffer& buffer;
    bool playing = false;

  public:
    PlaybackManager(PlaybackBuffer& playback_buffer)
      : buffer(playback_buffer) {}

    bool initialize() {
      return audio_output.initialize();
    }

    void start_playback() {
      if (playing) return;

      playing = true;

      // Start playback task
      xTaskCreatePinnedToCore(
        playback_task,
        "playback",
        4096,
        this,
        2,
        nullptr,
        1
      );

      LOG_AUDIO("Playback started");
    }

    void stop_playback() {
      playing = false;
      LOG_AUDIO("Playback stopped");
    }

    static void playback_task(void* pvParameters) {
      PlaybackManager* self = (PlaybackManager*)pvParameters;
      self->playback_loop();
    }

    void playback_loop() {
      int16_t chunk[512];

      while (playing) {
        // Read from buffer
        size_t samples_read = buffer.read(chunk, 512);

        if (samples_read > 0) {
          // Play audio
          audio_output.play_audio(chunk, samples_read);
        } else {
          // Buffer empty, wait a bit
          vTaskDelay(pdMS_TO_TICKS(10));
        }

        // Check if playback should continue
        if (samples_read == 0 && buffer.get_fill_level() == 0) {
          // Buffer empty and no more data
          if (!expecting_more_data()) {
            break;
          }
        }
      }

      playing = false;
      vTaskDelete(nullptr);
    }

    bool is_playing() {
      return playing;
    }

    size_t get_buffer_level() {
      return buffer.get_fill_level();
    }

  private:
    bool expecting_more_data() {
      // Check if Wyoming connection still active
      // and response not yet complete
      return true;  // For now, always expect more
    }
};
```

**Testing Plan:**
- Play various audio samples
- Check for dropouts
- Verify proper ending
- Measure latency

---

### Task 8.5: Volume Control & Speaker Management
**Objective:** Implement volume control and speaker settings
**Estimated Hours:** 6
**Depends On:** Task 8.1
**Acceptance Criteria:**
- [ ] Volume control functional (0-100%)
- [ ] Settings persistent across restarts
- [ ] Volume feedback to user
- [ ] Speaker mute functionality
- [ ] Independent from input levels
- [ ] Protection from clipping at high volumes

**Implementation Details:**

**Volume Controller:**

```cpp
class VolumeController {
  private:
    int volume_level = 80;  // 0-100
    const int VOLUME_PIN = 33;  // PWM pin
    const int VOLUME_MIN = 0;
    const int VOLUME_MAX = 255;

  public:
    void initialize() {
      // Setup PWM for volume control
      pinMode(VOLUME_PIN, OUTPUT);
      ledcSetup(0, 5000, 8);  // 5kHz PWM, 8-bit resolution
      ledcAttachPin(VOLUME_PIN, 0);

      // Load saved volume from EEPROM
      load_volume_from_eeprom();
      apply_volume();
    }

    void set_volume(int level) {
      if (level < VOLUME_MIN) level = VOLUME_MIN;
      if (level > VOLUME_MAX) level = VOLUME_MAX;

      volume_level = level;
      apply_volume();
      save_volume_to_eeprom();

      LOG_AUDIO_INFO("Volume set to %d%%", level);
    }

    int get_volume() {
      return volume_level;
    }

    void increase_volume() {
      set_volume(volume_level + 10);
    }

    void decrease_volume() {
      set_volume(volume_level - 10);
    }

  private:
    void apply_volume() {
      // Convert percentage to PWM value
      int pwm_value = (volume_level * VOLUME_MAX) / 100;
      ledcWrite(0, pwm_value);
    }

    void save_volume_to_eeprom() {
      EEPROM.write(EEPROM_VOLUME_ADDR, volume_level);
      EEPROM.commit();
    }

    void load_volume_from_eeprom() {
      volume_level = EEPROM.read(EEPROM_VOLUME_ADDR);
      if (volume_level == 255) {  // Uninitialized
        volume_level = 80;
      }
    }
};
```

**Testing Plan:**
- Test volume adjustment
- Verify persistence
- Check for clipping at high volume
- Test mute functionality

---

### Task 8.6: Transition Sounds & Audio Effects
**Objective:** Add sound effects for state transitions
**Estimated Hours:** 8
**Depends On:** Task 8.4
**Acceptance Criteria:**
- [ ] Start listening sound
- [ ] End listening sound
- [ ] Error sound
- [ ] Success sound
- [ ] Configurable sounds
- [ ] Sounds load correctly
- [ ] Proper timing between sounds and speech

**Implementation Details:**

**Audio Effects Manager:**

```cpp
enum AudioEffect {
  EFFECT_START_LISTENING,
  EFFECT_END_LISTENING,
  EFFECT_ERROR,
  EFFECT_SUCCESS,
  EFFECT_NOTIFICATION
};

class AudioEffectsManager {
  private:
    // Embedded audio data (WAV format)
    // These would be actual WAV data embedded as const arrays
    const uint8_t effect_start[] = {/* WAV data */};
    const size_t effect_start_len = 4096;  // Size in bytes

    PlaybackManager& playback;

  public:
    bool play_effect(AudioEffect effect) {
      const uint8_t* data = nullptr;
      size_t length = 0;

      switch (effect) {
        case EFFECT_START_LISTENING:
          data = effect_start;
          length = effect_start_len;
          break;
        case EFFECT_END_LISTENING:
          // ... other effects
          break;
        case EFFECT_ERROR:
          // ... error sound
          break;
        default:
          return false;
      }

      if (data && length > 0) {
        // Play effect through playback manager
        return playback.play_raw_audio(data, length);
      }

      return false;
    }

    void play_startup_sound() {
      play_effect(EFFECT_START_LISTENING);
    }

    void play_error_sound() {
      play_effect(EFFECT_ERROR);
    }
};
```

**Sound Compilation from WAV Files:**

```bash
#!/bin/bash
# Convert WAV files to C header files

for wav_file in sounds/*.wav; do
  name=$(basename "$wav_file" .wav)
  echo "Converting $wav_file..."

  # Use sox or ffmpeg to convert to raw PCM
  sox "$wav_file" -t raw -r 16000 -b 16 -c 1 "sounds/${name}.raw"

  # Convert to C header
  xxd -i "sounds/${name}.raw" "include/${name}_audio.h"
done
```

**Testing Plan:**
- Verify sounds play correctly
- Test timing between sounds
- Check audio quality
- Test all effect types

---

### Task 8.7: Concurrent Recording & Playback
**Objective:** Handle simultaneous recording and playback
**Estimated Hours:** 8
**Depends On:** Tasks 8.4, 7.3
**Acceptance Criteria:**
- [ ] No interference between record and playback
- [ ] Both streams maintained independently
- [ ] Audio quality maintained
- [ ] Resource usage acceptable
- [ ] Proper mixing handled (if needed)
- [ ] Edge cases handled (simultaneous start/stop)

**Implementation Details:**

**Concurrent Audio Manager:**

```cpp
class ConcurrentAudioManager {
  private:
    AudioRecorder recorder;
    AudioReceptionService receiver;
    PlaybackManager playback;
    RecordingBuffer recording_buffer;
    PlaybackBuffer playback_buffer;

    bool recording = false;
    bool playing = false;

  public:
    bool initialize() {
      return recorder.initialize() &&
             playback.initialize();
    }

    bool start_recording() {
      if (!recording) {
        recording = true;
        receiver.start_listening();
        LOG_AUDIO("Recording started");
      }
      return true;
    }

    bool stop_recording() {
      if (recording) {
        recording = false;
        receiver.stop_listening();
        LOG_AUDIO("Recording stopped");
      }
      return true;
    }

    bool start_playback() {
      if (!playing) {
        playing = true;
        playback.start_playback();
        LOG_AUDIO("Playback started");
      }
      return true;
    }

    bool stop_playback() {
      if (playing) {
        playing = false;
        playback.stop_playback();
        LOG_AUDIO("Playback stopped");
      }
      return true;
    }

    bool is_recording() { return recording; }
    bool is_playing() { return playing; }

    // Statistics
    size_t get_record_buffer_fill() {
      return recording_buffer.get_fill_level();
    }

    size_t get_playback_buffer_fill() {
      return playback_buffer.get_fill_level();
    }
};
```

**Testing Plan:**
- Start recording, then playback
- Start playback, then recording
- Stop in various orders
- Verify audio quality in both streams
- Check resource usage

---

### Task 8.8: Error Handling & Recovery
**Objective:** Handle failures in playback gracefully
**Estimated Hours:** 6
**Depends On:** Task 8.4
**Acceptance Criteria:**
- [ ] Buffer underrun handled
- [ ] Network disconnection detected
- [ ] Automatic recovery attempted
- [ ] User feedback on errors
- [ ] Logs capture issues
- [ ] System remains stable

**Implementation Details:**

**Playback Error Handler:**

```cpp
class PlaybackErrorHandler {
  private:
    PlaybackManager& playback;
    int consecutive_errors = 0;
    const int MAX_ERRORS = 5;

  public:
    void handle_buffer_underrun() {
      LOG_AUDIO_ERROR("Playback buffer underrun");
      consecutive_errors++;

      if (consecutive_errors > MAX_ERRORS) {
        // Too many errors, stop playback
        playback.stop_playback();
        play_error_effect();
      }
    }

    void handle_network_error() {
      LOG_AUDIO_ERROR("Network error during playback");

      // Stop playback
      playback.stop_playback();

      // Try to reconnect
      if (attempt_reconnect()) {
        consecutive_errors = 0;
      } else {
        consecutive_errors++;
        if (consecutive_errors > 3) {
          play_error_effect();
        }
      }
    }

    void reset_errors() {
      consecutive_errors = 0;
    }

  private:
    bool attempt_reconnect() {
      // Attempt to reconnect to Wyoming
      return false;  // Placeholder
    }

    void play_error_effect() {
      effects_manager.play_error_sound();
    }
};
```

**Testing Plan:**
- Simulate buffer underrun
- Test network disconnection
- Verify recovery attempts
- Check error sounds play

---

### Task 8.9: Integration & System Testing
**Objective:** Full end-to-end testing of audio I/O
**Estimated Hours:** 10
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Full conversation audio flow working
- [ ] Recording and playback synchronized
- [ ] No audio artifacts or quality loss
- [ ] System stable over extended run
- [ ] Performance metrics met
- [ ] All edge cases handled

**Implementation Details:**

**Integration Test Suite:**

```cpp
void test_audio_io_flow() {
  // Test 1: Playback only
  PlaybackBuffer buffer;
  PlaybackManager playback(buffer);

  int16_t test_samples[1000];
  for (int i = 0; i < 1000; i++) {
    test_samples[i] = i % 32768;  // Sawtooth wave
  }

  assert(buffer.write(test_samples, 1000));
  playback.start_playback();
  delay(1000);  // Play for 1 second
  playback.stop_playback();

  // Test 2: Recording and playback
  ConcurrentAudioManager audio;
  assert(audio.initialize());

  audio.start_recording();
  delay(2000);
  audio.start_playback();
  delay(2000);
  audio.stop_recording();
  audio.stop_playback();

  Serial.println("Audio I/O tests passed!");
}
```

**Performance Benchmark:**

```cpp
void benchmark_latency() {
  PlaybackBuffer buffer;
  unsigned long start_time = millis();

  // Write 1 second of audio
  for (int i = 0; i < 16000; i++) {
    buffer.write(&test_data[i], 1);
  }

  unsigned long write_time = millis() - start_time;
  Serial.printf("Write time for 1s audio: %lu ms\n", write_time);

  // Read it back
  start_time = millis();
  int16_t chunk[512];
  for (int i = 0; i < 32; i++) {  // 32 chunks of 512 samples
    buffer.read(chunk, 512);
  }
  unsigned long read_time = millis() - start_time;
  Serial.printf("Read time for 1s audio: %lu ms\n", read_time);

  assert(write_time < 100);  // Should be very fast
  assert(read_time < 100);
}
```

**Testing Plan:**
- Execute full integration test
- Run 8-hour stability test
- Measure audio quality (spectrum analysis)
- Test all error conditions

---

### Task 8.10: Documentation & Deployment
**Objective:** Document playback system and prepare for deployment
**Estimated Hours:** 4
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Audio playback documented
- [ ] Configuration documented
- [ ] Troubleshooting guide created
- [ ] Integration guide for full system
- [ ] Examples provided

**Implementation Details:**

**Documentation Structure:**
1. Playback Architecture
2. Buffer Management Details
3. Speaker Configuration
4. Volume Control Setup
5. Audio Effects
6. Integration with Recording
7. Troubleshooting

**Testing Plan:**
- Verify documentation accuracy
- Follow setup guides successfully

---

## Technical Implementation Details

### Audio Output Pipeline

```
Backend LLM Response
    ↓
Wyoming Protocol (receives PCM)
    ↓
Audio Reception Service
    ↓
Playback Buffer (ring buffer)
    ↓
Playback Manager (reads chunks)
    ↓
Volume Control
    ↓
I2S Output Driver
    ↓
Speaker Amplifier
    ↓
Audio Output (speaker)
```

### Buffer Synchronization

```
Recording Path:          Playback Path:
Microphone → Buffer → Wyoming → Backend → Wyoming → Buffer → Speaker

Both streams may run concurrently
Buffers are independent (no mixing needed initially)
```

---

## Testing Plan

### Unit Tests
- Buffer write/read operations
- Volume control
- Effect playback
- Error handling

### Integration Tests
- Full audio I/O chain
- Concurrent recording + playback
- Network reception
- Speaker output quality

### System Tests
- 8-hour continuous operation
- Various audio samples
- Error recovery
- Performance benchmarks

---

## Estimated Timeline

**Week 1 (30 hours):**
- Tasks 8.1-8.3: Output configuration, buffers, reception (22 hrs)
- Task 8.4: Playback management (6 hrs)
- Task 8.5: Volume control (2 hrs - carry over)

**Week 2 (30 hours):**
- Task 8.5: Volume control (continued, 4 hrs)
- Task 8.6: Audio effects (8 hrs)
- Task 8.7: Concurrent audio (8 hrs)
- Task 8.8: Error handling (6 hrs)
- Tasks 8.9-8.10: Testing and documentation (4 hrs)

**Total: ~60 hours (~1.5 weeks)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Speaker quality issues | Low | Medium | Test with actual hardware early |
| Audio dropout/underrun | Medium | High | Buffer management, monitoring |
| Interference with recording | Medium | High | Independent buffer streams |
| Volume control instability | Low | Low | EEPROM persistence testing |
| Network latency issues | Low | Medium | Buffer size optimization |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Audio plays from backend responses
- [ ] Volume control working
- [ ] Transition sounds playing
- [ ] Recording and playback simultaneous
- [ ] Error handling graceful

### Performance
- [ ] Playback latency <1 second
- [ ] Speaker output quality acceptable
- [ ] No audio dropouts
- [ ] System handles 8+ hour operation

### Reliability
- [ ] Recovers from buffer underrun
- [ ] Network errors handled
- [ ] System remains stable
- [ ] Audio quality maintained

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic completes the bidirectional audio flow outlined in Phase 4, enabling complete voice conversations through the device speaker.

**Dependencies Met:** Epic 7 (recording), Epic 6 (backend)
**Enables:** Epic 10 (continuous conversation), full voice assistant functionality

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-06-23 (Epic 7 completion + 2 weeks)
