# Epic 7: Recording & PCM Streaming - Project Plan

**Document ID:** EPIC-7-RECORDING-2026
**Epic Title:** Recording & PCM Streaming (Audio Input Pipeline)
**Status:** Planned
**Target Completion:** 2026-06-09
**Estimated Duration:** 2 weeks (~80 hours)
**Last Updated:** 2026-03-24
**Serial Logging Tool:** Available as separate utility script with sub-commands for log capture, viewing, searching, and export

---

## Executive Summary

Epic 7 implements voice recording on the ESP32-S3-BOX-3B device and PCM packet transmission to the backend through Home Assistant. This epic captures audio from the device's microphone, buffers it efficiently, streams it as PCM packets, and integrates with the Whisper STT service for speech-to-text processing. The focus is on reliable audio capture, efficient transmission, and integration with the Wyoming protocol established in Epic 6.

**Serial Logging Utility:** A separate command-line utility script (`chatterbox-logs`) provides operators with tools to capture, view, search, and export serial logs collected during audio processing and other device operations. This utility is independent of the main application and can be used standalone for troubleshooting.

---

## Goals & Success Criteria

### Primary Goals
1. Implement audio recording on ESP32-S3-BOX-3B hardware
2. Create efficient PCM buffer management with circular buffers
3. Stream audio to backend via Wyoming protocol
4. Integrate with Whisper for real-time STT
5. Implement serial logging for debugging
6. Enable push-to-talk and wake-word detection workflows
7. Achieve real-time audio processing (low latency)

### Success Criteria
- [ ] Audio recording from box3b microphone at 16kHz 16-bit mono
- [ ] PCM buffer maintained with <500ms latency
- [ ] Audio packets streamed reliably to backend
- [ ] Whisper STT integration <3 second latency for typical speech
- [ ] Recording quality acceptable for speech recognition (>90% accuracy)
- [ ] System handles continuous recording for 8+ hours
- [ ] Serial logging captures all audio events
- [ ] Wake word detection triggers recording correctly
- [ ] Push-to-talk mode functional
- [ ] Error recovery from network issues

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 1 (OTA & Foundation):** Device firmware framework
- **Epic 6 (Backend Deployment):** Backend ready to receive audio streams
- **Wyoming Protocol:** Fully operational for audio transmission

### Prerequisites
- ESP32-S3-BOX-3B hardware with microphone functional
- Audio driver support in ESP-IDF
- FFmpeg installed on backend (for audio processing)
- Whisper library integrated on backend
- Network connectivity between device and backend stable

### Blockers to Identify
- Audio quality issues on hardware
- PCM format compatibility
- Latency constraints
- Memory constraints on device

---

## Detailed Task Breakdown

### Task 7.1: Audio Hardware Initialization & Microphone Setup
**Objective:** Configure audio capture on ESP32-S3-BOX-3B
**Estimated Hours:** 8
**Acceptance Criteria:**
- [ ] Microphone initialized and functional
- [ ] Audio sampling configured (16kHz, 16-bit, mono)
- [ ] I2S driver configured correctly
- [ ] ADC working for audio input
- [ ] Hardware tests pass
- [ ] Serial output shows mic data

**Implementation Details:**

**ESP32 Audio Configuration (Arduino/PlatformIO):**

```cpp
#include <driver/i2s.h>

// Audio configuration constants
const int SAMPLE_RATE = 16000;          // 16kHz sampling
const int BITS_PER_SAMPLE = 16;         // 16-bit
const int CHANNELS = 1;                 // Mono
const int SAMPLES_PER_READ = 512;       // 512 samples = 32ms

class AudioRecorder {
  private:
    i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 4,
      .dma_buf_len = 512,
      .use_apll = true,
      .tx_desc_auto_clear = false,
      .fixed_mclk = I2S_FIXED_MCLK0,
    };

    i2s_pin_config_t pin_config = {
      .bck_io_num = 5,
      .ws_io_num = 6,
      .data_out_num = -1,           // Not used (RX only)
      .data_in_num = 7,             // Microphone data
      .mck_io_num = -1,
    };

  public:
    bool initialize() {
      // Install and start I2S driver
      esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, nullptr);
      if (err != ESP_OK) {
        Serial.printf("I2S driver install failed: %s\n", esp_err_to_name(err));
        return false;
      }

      // Set pin configuration
      err = i2s_set_pin(I2S_NUM_0, &pin_config);
      if (err != ESP_OK) {
        Serial.printf("I2S set pin failed: %s\n", esp_err_to_name(err));
        return false;
      }

      // Clear DMA buffer
      i2s_zero_dma_buffer(I2S_NUM_0);

      return true;
    }

    int read_samples(int16_t* buffer, int sample_count) {
      size_t bytes_read = 0;
      esp_err_t err = i2s_read(
        I2S_NUM_0,
        buffer,
        sample_count * sizeof(int16_t),
        &bytes_read,
        portMAX_DELAY
      );

      if (err != ESP_OK) {
        Serial.printf("I2S read failed: %s\n", esp_err_to_name(err));
        return 0;
      }

      return bytes_read / sizeof(int16_t);
    }
};
```

**Testing Plan:**
- Verify microphone connected and responding
- Test I2S driver initialization
- Verify audio samples appear in buffer
- Check audio quality (no clipping, proper levels)

---

### Task 7.2: PCM Buffer Management & Circular Buffers
**Objective:** Implement efficient circular buffer for audio streaming
**Estimated Hours:** 10
**Depends On:** Task 7.1
**Acceptance Criteria:**
- [ ] Circular buffer implemented and tested
- [ ] No buffer overruns or data loss
- [ ] Read/write operations thread-safe
- [ ] Memory efficient on resource-constrained device
- [ ] Latency <500ms end-to-end
- [ ] Unit tests verify buffer behavior

**Implementation Details:**

**Circular Buffer Implementation:**

```cpp
template<typename T, size_t BUFFER_SIZE = 32768>  // 1 second at 16kHz
class CircularBuffer {
  private:
    T buffer[BUFFER_SIZE];
    volatile size_t write_index = 0;
    volatile size_t read_index = 0;
    SemaphoreHandle_t mutex;

  public:
    CircularBuffer() {
      mutex = xSemaphoreCreateMutex();
    }

    bool write(const T* data, size_t count) {
      if (!xSemaphoreTake(mutex, portMAX_DELAY)) return false;

      // Check if buffer has space
      size_t available = available_write_space();
      if (available < count) {
        xSemaphoreGive(mutex);
        return false;  // Buffer full
      }

      // Write data
      for (size_t i = 0; i < count; i++) {
        buffer[write_index] = data[i];
        write_index = (write_index + 1) % BUFFER_SIZE;
      }

      xSemaphoreGive(mutex);
      return true;
    }

    size_t read(T* output, size_t count) {
      if (!xSemaphoreTake(mutex, portMAX_DELAY)) return 0;

      size_t available = available_read_size();
      size_t to_read = (count < available) ? count : available;

      for (size_t i = 0; i < to_read; i++) {
        output[i] = buffer[read_index];
        read_index = (read_index + 1) % BUFFER_SIZE;
      }

      xSemaphoreGive(mutex);
      return to_read;
    }

    size_t available_read_size() {
      if (write_index >= read_index) {
        return write_index - read_index;
      } else {
        return BUFFER_SIZE - read_index + write_index;
      }
    }

    size_t available_write_space() {
      return BUFFER_SIZE - available_read_size() - 1;
    }

    void clear() {
      xSemaphoreTake(mutex, portMAX_DELAY);
      write_index = 0;
      read_index = 0;
      xSemaphoreGive(mutex);
    }

    float get_fill_percentage() {
      return (float)available_read_size() / BUFFER_SIZE * 100.0f;
    }
};
```

**Test Suite:**

```cpp
void test_circular_buffer() {
  CircularBuffer<int16_t> buffer;

  // Test 1: Write and read
  int16_t test_data[10] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
  assert(buffer.write(test_data, 10));
  assert(buffer.available_read_size() == 10);

  // Test 2: Read data
  int16_t read_data[10];
  size_t read_count = buffer.read(read_data, 10);
  assert(read_count == 10);
  for (int i = 0; i < 10; i++) {
    assert(read_data[i] == test_data[i]);
  }

  // Test 3: Wraparound
  for (int i = 0; i < 5; i++) {
    buffer.write(test_data, 10);
    buffer.read(read_data, 5);
  }
  // Verify no data loss

  Serial.println("All circular buffer tests passed!");
}
```

**Testing Plan:**
- Unit tests for read/write operations
- Test wraparound behavior
- Test thread-safety with concurrent access
- Measure latency from recording to buffer to transmission

---

### Task 7.3: Audio Stream Transmission (Wyoming Protocol)
**Objective:** Stream PCM audio packets to backend via Wyoming
**Estimated Hours:** 10
**Depends On:** Tasks 7.1, 7.2
**Acceptance Criteria:**
- [ ] PCM packets transmitted to backend
- [ ] Wyoming protocol compliance
- [ ] Packet format correct for Whisper
- [ ] Handles transmission errors gracefully
- [ ] Latency <500ms for complete audio packet
- [ ] Network disconnection handled

**Implementation Details:**

**Audio Streaming Service:**

```cpp
class AudioStreamingService {
  private:
    CircularBuffer<int16_t> audio_buffer;
    WiFiClient wyoming_client;
    const char* WYOMING_HOST = "192.168.1.100";  // Backend IP
    const int WYOMING_PORT = 10700;
    bool streaming = false;

  public:
    bool start_streaming() {
      // Connect to Wyoming service
      if (!wyoming_client.connect(WYOMING_HOST, WYOMING_PORT)) {
        Serial.println("Failed to connect to Wyoming");
        return false;
      }

      streaming = true;

      // Start audio streaming task
      xTaskCreatePinnedToCore(
        stream_audio_task,
        "audio_stream",
        4096,
        this,
        3,  // Priority
        nullptr,
        1   // Core 1
      );

      return true;
    }

    static void stream_audio_task(void* pvParameters) {
      AudioStreamingService* self = (AudioStreamingService*)pvParameters;
      self->stream_audio();
    }

    void stream_audio() {
      int16_t chunk[512];  // 32ms of audio at 16kHz

      while (streaming) {
        // Read from buffer
        size_t samples_read = audio_buffer.read(chunk, 512);

        if (samples_read > 0) {
          // Send PCM packet to Wyoming
          send_pcm_packet(chunk, samples_read);

          // Log audio event
          log_audio_event("AUDIO_SENT", samples_read);
        }

        // Don't saturate CPU
        vTaskDelay(pdMS_TO_TICKS(10));
      }

      wyoming_client.stop();
      vTaskDelete(nullptr);
    }

    void send_pcm_packet(int16_t* data, size_t sample_count) {
      // Wyoming binary format:
      // [MAGIC: 'audio'][SAMPLE_RATE: u32][CHANNELS: u8][BITS: u8][DATA...]

      uint8_t header[10];
      header[0] = 'a';
      header[1] = 'u';
      header[2] = 'd';
      header[3] = 'i';  // MAGIC
      header[4] = (16000 >> 24) & 0xFF;  // Sample rate big-endian
      header[5] = (16000 >> 16) & 0xFF;
      header[6] = (16000 >> 8) & 0xFF;
      header[7] = 16000 & 0xFF;
      header[8] = 1;     // Channels (mono)
      header[9] = 16;    // Bits per sample

      // Send header
      wyoming_client.write(header, 10);

      // Send PCM data
      wyoming_client.write((uint8_t*)data, sample_count * sizeof(int16_t));
      wyoming_client.flush();
    }

    void stop_streaming() {
      streaming = false;
      audio_buffer.clear();
    }
};
```

**Backend Receiver (Python):**

```python
import asyncio
import struct

async def handle_audio_stream(reader, writer):
    """Handle incoming audio stream from device"""
    logger.info("Audio stream connected")

    buffer = bytearray()

    try:
        while True:
            # Read header
            header = await reader.readexactly(10)
            magic = header[0:4].decode()

            if magic != "audi":
                logger.warning("Invalid audio packet header")
                break

            sample_rate = struct.unpack(">I", header[4:8])[0]
            channels = header[8]
            bits = header[9]

            # Expected audio size
            expected_bytes = 512 * 2  # 512 samples * 2 bytes

            # Read PCM data
            pcm_data = await reader.readexactly(expected_bytes)
            buffer.extend(pcm_data)

            # Process audio through Whisper if buffer full
            if len(buffer) >= 16000 * 2:  # 1 second at 16kHz
                await process_audio(buffer)
                buffer = bytearray()

    except asyncio.CancelledError:
        logger.info("Audio stream closed")
    except Exception as e:
        logger.error(f"Error in audio stream: {e}")
    finally:
        writer.close()

async def process_audio(pcm_data):
    """Send audio to Whisper for STT"""
    # Convert bytes to numpy array
    audio_samples = np.frombuffer(pcm_data, dtype=np.int16)

    # Normalize to [-1, 1]
    audio = audio_samples.astype(np.float32) / 32768.0

    # Process with Whisper
    result = whisper_model.transcribe(
        audio,
        language="en",
        verbose=False
    )

    text = result["text"]
    logger.info(f"Transcribed: {text}")

    # Send to LLM for processing
    await process_user_input(text)
```

**Testing Plan:**
- Verify PCM packets received on backend
- Check audio quality and completeness
- Test with network interruptions
- Measure end-to-end latency

---

### Task 7.4: Whisper STT Integration
**Objective:** Integrate Whisper speech-to-text on backend
**Estimated Hours:** 8
**Depends On:** Task 7.3
**Acceptance Criteria:**
- [ ] Whisper model loaded and operational
- [ ] Real-time transcription working
- [ ] Accuracy >90% on common speech
- [ ] Latency <3 seconds for typical audio
- [ ] Language auto-detection working
- [ ] Punctuation and capitalization correct

**Implementation Details:**

**Whisper Integration Service:**

```python
import whisper
import numpy as np
from datetime import datetime

class WhisperSTTService:
    def __init__(self, model_size="base"):
        """Initialize Whisper STT service"""
        self.logger = logging.getLogger(__name__)

        # Load model (options: tiny, base, small, medium, large)
        self.logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)

        # Performance tracking
        self.total_processed = 0
        self.total_time = 0

    async def transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio using Whisper

        Args:
            audio_data: Audio samples as numpy array (float32, normalized)
            language: Language code (None for auto-detect)

        Returns:
            Dict with transcription results
        """
        start_time = datetime.utcnow()

        try:
            result = self.model.transcribe(
                audio_data,
                language=language,
                verbose=False,
                temperature=0.0,  # Deterministic
                no_speech_threshold=0.4,
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            self.total_processed += 1
            self.total_time += duration

            self.logger.info(
                f"Transcription completed in {duration:.2f}s: "
                f"{result['text']}"
            )

            return {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "duration_ms": int(duration * 1000),
                "confidence": self._calculate_confidence(result),
                "segments": result.get("segments", [])
            }

        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            raise

    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence score from segments"""
        if not result.get("segments"):
            return 0.0

        # Average confidence across segments
        confidences = [
            seg.get("confidence", 0.5)
            for seg in result["segments"]
        ]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def get_stats(self) -> Dict:
        """Get STT service statistics"""
        avg_time = (self.total_time / self.total_processed
                   if self.total_processed > 0 else 0)
        return {
            "total_processed": self.total_processed,
            "average_duration_ms": int(avg_time * 1000),
            "model": self.model.device,
        }
```

**WebSocket Handler for Streaming:**

```python
@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio streaming"""
    await websocket.accept()

    audio_buffer = bytearray()
    stt_service = WhisperSTTService()

    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_bytes()

            audio_buffer.extend(data)

            # Process if buffer has 1 second of audio
            if len(audio_buffer) >= 32000:  # 16kHz * 16-bit * 1 sec

                # Convert to numpy array
                audio_samples = np.frombuffer(
                    audio_buffer,
                    dtype=np.int16
                )
                audio_float = audio_samples.astype(np.float32) / 32768.0

                # Transcribe
                result = await stt_service.transcribe_audio(audio_float)

                # Send result
                await websocket.send_json({
                    "type": "transcription",
                    "text": result["text"],
                    "language": result["language"],
                    "confidence": result["confidence"]
                })

                # Clear buffer
                audio_buffer = bytearray()

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

**Testing Plan:**
- Test with various audio samples
- Verify accuracy metrics
- Measure transcription latency
- Test language detection
- Stress test with continuous audio

---

### Task 7.5: Serial Logging for Audio Events
**Objective:** Log audio events for troubleshooting and monitoring
**Estimated Hours:** 6
**Depends On:** Task 7.1
**Acceptance Criteria:**
- [ ] All audio events logged (record start/stop, errors)
- [ ] Buffer status logged periodically
- [ ] Network transmission logged
- [ ] Errors captured with context
- [ ] Logs searchable and indexed
- [ ] Performance minimal

**Implementation Details:**

**Audio Event Logging Macros:**

```cpp
// Logging levels for audio module
#define LOG_AUDIO_DEBUG(msg, ...) \
  log_event("AUDIO", "DEBUG", __func__, __LINE__, msg, ##__VA_ARGS__)

#define LOG_AUDIO_INFO(msg, ...) \
  log_event("AUDIO", "INFO", __func__, __LINE__, msg, ##__VA_ARGS__)

#define LOG_AUDIO_ERROR(msg, ...) \
  log_event("AUDIO", "ERROR", __func__, __LINE__, msg, ##__VA_ARGS__)

// Log event with structured format
void log_event(const char* module, const char* level,
               const char* func, int line,
               const char* fmt, ...) {
  // Timestamp
  time_t now = time(nullptr);
  struct tm timeinfo = *localtime(&now);
  char ts[32];
  strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);

  // Format message
  char buffer[256];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buffer, sizeof(buffer), fmt, args);
  va_end(args);

  // Output JSON log
  printf("{\"timestamp\":\"%s\",\"module\":\"%s\",\"level\":\"%s\","
         "\"function\":\"%s\",\"line\":%d,\"message\":\"%s\"}\n",
         ts, module, level, func, line, buffer);
}

// Log audio buffer status
void log_audio_status(CircularBuffer<int16_t>& buffer) {
  float fill_pct = buffer.get_fill_percentage();
  LOG_AUDIO_DEBUG("Buffer fill: %.1f%%", fill_pct);

  if (fill_pct > 90.0f) {
    LOG_AUDIO_ERROR("Buffer nearly full!");
  }
}
```

**Testing Plan:**
- Verify log format is valid JSON
- Test with high-volume logging
- Check no performance impact
- Verify log searchability

---

### Task 7.6: Push-to-Talk Mode Implementation
**Objective:** Enable manual recording trigger
**Estimated Hours:** 8
**Depends On:** Tasks 7.1, 7.2, 7.3
**Acceptance Criteria:**
- [ ] Button triggers recording on device
- [ ] Recording starts immediately
- [ ] Audio transmitted while button held
- [ ] Recording stops when button released
- [ ] Feedback to user (LED, sound)
- [ ] Debouncing working correctly

**Implementation Details:**

**Push-to-Talk Handler:**

```cpp
class PushToTalkHandler {
  private:
    const int BUTTON_PIN = 16;
    const int LED_PIN = 12;
    AudioStreamingService audio_service;
    volatile bool recording = false;

  public:
    void initialize() {
      // Setup button
      pinMode(BUTTON_PIN, INPUT_PULLUP);

      // Setup LED feedback
      pinMode(LED_PIN, OUTPUT);
      digitalWrite(LED_PIN, LOW);

      // Button interrupt
      attachInterrupt(
        digitalPinToInterrupt(BUTTON_PIN),
        button_isr,
        CHANGE
      );
    }

    static void button_isr() {
      // Handle button state change
      int button_state = digitalRead(BUTTON_PIN);

      if (button_state == LOW) {
        // Button pressed
        start_recording();
      } else {
        // Button released
        stop_recording();
      }
    }

    static void start_recording() {
      if (!recording) {
        recording = true;
        digitalWrite(LED_PIN, HIGH);  // LED feedback

        // Start audio streaming
        audio_service.start_streaming();

        LOG_AUDIO_INFO("PTT: Recording started");
      }
    }

    static void stop_recording() {
      if (recording) {
        recording = false;
        digitalWrite(LED_PIN, LOW);  // LED feedback

        // Stop streaming
        audio_service.stop_streaming();

        LOG_AUDIO_INFO("PTT: Recording stopped");
      }
    }
};
```

**Testing Plan:**
- Test button responsiveness
- Verify LED feedback
- Test debouncing
- Measure latency from button press to recording

---

### Task 7.7: Wake Word Detection Integration
**Objective:** Integrate wake word detection for always-listening mode
**Estimated Hours:** 10
**Depends On:** Tasks 7.1, 7.2
**Acceptance Criteria:**
- [ ] Wake word model integrated
- [ ] Detection triggers recording automatically
- [ ] False positive rate <5%
- [ ] False negative rate <10%
- [ ] Latency <500ms from speech to detection
- [ ] Can be disabled via configuration

**Implementation Details:**

**Wake Word Detection:**

```cpp
// Using microWakeWord library
#include <MicroWakeWord.h>

class WakeWordDetector {
  private:
    MicroWakeWord wake_word_model;
    CircularBuffer<int16_t>& audio_buffer;
    bool enabled = true;
    const float CONFIDENCE_THRESHOLD = 0.7f;

  public:
    WakeWordDetector(CircularBuffer<int16_t>& buffer)
      : audio_buffer(buffer) {}

    bool initialize() {
      // Load wake word model
      const char* MODEL_PATH = "/spiffs/hey_cackle.model";

      if (!wake_word_model.begin(MODEL_PATH)) {
        LOG_AUDIO_ERROR("Failed to load wake word model");
        return false;
      }

      // Start detection task
      xTaskCreatePinnedToCore(
        detection_task,
        "wake_word",
        4096,
        this,
        2,
        nullptr,
        0
      );

      return true;
    }

    static void detection_task(void* pvParameters) {
      WakeWordDetector* self = (WakeWordDetector*)pvParameters;
      self->detect_loop();
    }

    void detect_loop() {
      int16_t samples[512];

      while (true) {
        // Read audio chunk
        if (audio_buffer.read(samples, 512) > 0) {
          // Run inference
          float confidence = wake_word_model.detect(samples, 512);

          if (confidence > CONFIDENCE_THRESHOLD) {
            LOG_AUDIO_INFO("Wake word detected: %.2f confidence", confidence);
            on_wake_word_detected();
          }
        }

        vTaskDelay(pdMS_TO_TICKS(10));
      }
    }

    void on_wake_word_detected() {
      // Play sound
      play_audio_effect(AUDIO_EFFECT_WAKE);

      // Start recording
      audio_service.start_streaming();

      // Set device state to active
      device_state.set_state(DeviceState::ACTIVE);
    }

    void set_enabled(bool state) {
      enabled = state;
      LOG_AUDIO_INFO("Wake word detection %s", enabled ? "enabled" : "disabled");
    }
};
```

**Testing Plan:**
- Test with various wake word utterances
- Measure false positive/negative rates
- Test confidence threshold tuning
- Performance on device

---

### Task 7.8: Audio Quality & Noise Management
**Objective:** Optimize audio quality for speech recognition
**Estimated Hours:** 8
**Depends On:** Task 7.1
**Acceptance Criteria:**
- [ ] Noise reduction effective
- [ ] Gain normalization working
- [ ] No audio clipping
- [ ] Frequency response appropriate for speech
- [ ] Echo cancellation if needed
- [ ] Quality metrics logged

**Implementation Details:**

**Audio Preprocessing:**

```cpp
class AudioProcessor {
  private:
    // Noise gate parameters
    const float NOISE_GATE_THRESHOLD = 0.02f;
    const float NOISE_GATE_SMOOTHING = 0.95f;
    float noise_gate_level = 0.0f;

    // Automatic gain control
    const float TARGET_LEVEL = 0.7f;
    const float AGC_RATE = 0.001f;
    float current_gain = 1.0f;

  public:
    void process_audio(int16_t* samples, size_t count) {
      for (size_t i = 0; i < count; i++) {
        float sample = samples[i] / 32768.0f;

        // Noise gate
        sample = apply_noise_gate(sample);

        // Normalize gain
        sample = apply_agc(sample);

        // Clipping protection
        if (sample > 1.0f) sample = 1.0f;
        if (sample < -1.0f) sample = -1.0f;

        samples[i] = (int16_t)(sample * 32768.0f);
      }
    }

  private:
    float apply_noise_gate(float sample) {
      float abs_sample = fabsf(sample);

      // Update noise level estimate
      if (abs_sample > noise_gate_level) {
        noise_gate_level = abs_sample;
      } else {
        noise_gate_level *= NOISE_GATE_SMOOTHING;
      }

      // Gate out low signals
      if (abs_sample < NOISE_GATE_THRESHOLD) {
        return 0.0f;
      }

      return sample;
    }

    float apply_agc(float sample) {
      float level = fabsf(sample);

      // Adjust gain toward target
      if (level > 0.0f) {
        float target_gain = TARGET_LEVEL / level;
        current_gain += (target_gain - current_gain) * AGC_RATE;

        // Limit gain
        if (current_gain > 8.0f) current_gain = 8.0f;
        if (current_gain < 0.1f) current_gain = 0.1f;
      }

      return sample * current_gain;
    }
};
```

**Testing Plan:**
- Test with noisy environments
- Verify no clipping
- Measure frequency response
- Test with various speech patterns

---

### Task 7.9: Error Handling & Recovery
**Objective:** Handle network and hardware failures gracefully
**Estimated Hours:** 8
**Depends On:** Tasks 7.3, 7.4
**Acceptance Criteria:**
- [ ] Network disconnection handled gracefully
- [ ] Automatic reconnection working
- [ ] Audio not lost during network issues
- [ ] Device recovers to normal state
- [ ] Errors logged with context
- [ ] User feedback on errors

**Implementation Details:**

**Error Recovery Handler:**

```cpp
class AudioErrorHandler {
  private:
    enum AudioError {
      NETWORK_DISCONNECTED,
      WYOMING_UNAVAILABLE,
      BUFFER_OVERFLOW,
      MICROPHONE_FAILURE,
      TRANSMISSION_ERROR
    };

    int consecutive_errors = 0;
    const int MAX_RETRIES = 5;
    const int BACKOFF_MS = 1000;

  public:
    void handle_error(AudioError error) {
      switch (error) {
        case NETWORK_DISCONNECTED:
          handle_network_error();
          break;
        case BUFFER_OVERFLOW:
          handle_buffer_overflow();
          break;
        case TRANSMISSION_ERROR:
          handle_transmission_error();
          break;
        default:
          handle_unknown_error();
      }
    }

  private:
    void handle_network_error() {
      LOG_AUDIO_ERROR("Network disconnected");
      stop_streaming();

      // Attempt reconnection with backoff
      for (int attempt = 0; attempt < MAX_RETRIES; attempt++) {
        delay(BACKOFF_MS * (1 << attempt));  // Exponential backoff

        if (reconnect_to_wyoming()) {
          LOG_AUDIO_INFO("Reconnected to Wyoming");
          start_streaming();
          consecutive_errors = 0;
          return;
        }
      }

      LOG_AUDIO_ERROR("Failed to reconnect after %d attempts", MAX_RETRIES);
      device_state.set_state(DeviceState::ERROR);
    }

    void handle_buffer_overflow() {
      LOG_AUDIO_ERROR("Audio buffer overflow");

      // Clear buffer and restart
      audio_buffer.clear();
      stop_streaming();

      // Play error sound
      play_audio_effect(AUDIO_EFFECT_ERROR);

      // Restart recording
      delay(1000);
      start_streaming();
    }

    void handle_transmission_error() {
      LOG_AUDIO_ERROR("Transmission error");
      consecutive_errors++;

      if (consecutive_errors > 3) {
        LOG_AUDIO_ERROR("Too many consecutive errors, stopping");
        stop_streaming();
        device_state.set_state(DeviceState::ERROR);
      }
    }
};
```

**Testing Plan:**
- Simulate network disconnection
- Test buffer overflow scenarios
- Verify error recovery
- Check error messages and feedback

---

### Task 7.10: Integration Testing & Performance Validation
**Objective:** End-to-end testing of recording and streaming
**Estimated Hours:** 12
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Full audio chain working end-to-end
- [ ] Recording quality acceptable
- [ ] Latency <500ms for complete chain
- [ ] No data loss under normal conditions
- [ ] System stable over 8+ hours
- [ ] Whisper accuracy >90%

**Implementation Details:**

**Integration Test Suite:**

```cpp
void test_audio_chain() {
  // Test 1: Hardware initialization
  AudioRecorder recorder;
  assert(recorder.initialize());

  // Test 2: Circular buffer
  CircularBuffer<int16_t> buffer;
  int16_t test_data[512];
  for (int i = 0; i < 512; i++) test_data[i] = i;

  assert(buffer.write(test_data, 512));
  int16_t read_data[512];
  assert(buffer.read(read_data, 512) == 512);

  // Test 3: Wyoming connection
  AudioStreamingService streaming;
  assert(streaming.connect());

  // Test 4: Full recording flow
  assert(streaming.start_streaming());
  delay(5000);  // Record for 5 seconds
  streaming.stop_streaming();

  Serial.println("All integration tests passed!");
}
```

**Performance Benchmarks:**

```python
def test_whisper_latency():
    """Test Whisper transcription latency"""
    stt = WhisperSTTService()

    latencies = []
    for i in range(10):
        audio = generate_test_audio(duration=3)

        start = time.time()
        result = stt.transcribe_audio(audio)
        latency = (time.time() - start) * 1000

        latencies.append(latency)
        print(f"Transcription {i+1}: {latency:.0f}ms - {result['text']}")

    avg_latency = sum(latencies) / len(latencies)
    print(f"Average latency: {avg_latency:.0f}ms")
    assert avg_latency < 3000, "Latency exceeds 3 second SLA"

def test_recording_stability():
    """Test recording for extended period"""
    stt = WhisperSTTService()

    # Record for 8 hours
    for hour in range(8):
        for minute in range(60):
            audio = capture_test_audio(duration=1)
            result = stt.transcribe_audio(audio)
            assert result['text'] is not None

    print("8-hour stability test passed!")
```

**Testing Plan:**
- Execute full integration test suite
- Run 8-hour continuous recording test
- Measure accuracy with real speech samples
- Performance benchmarking with profiling

---

### Task 7.11: Documentation & Deployment
**Objective:** Document audio system and prepare for deployment
**Estimated Hours:** 6
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Audio subsystem documented
- [ ] Configuration guide created
- [ ] Troubleshooting guide written
- [ ] Hardware setup guide complete
- [ ] Integration guide for backend
- [ ] Examples provided

**Implementation Details:**

**Documentation Structure:**
1. Audio Architecture Overview
2. Hardware Setup (microphone connections, I2S pins)
3. Firmware Configuration
4. Backend Integration
5. Troubleshooting Common Issues
6. Performance Tuning

**Testing Plan:**
- Verify documentation accuracy
- New user follows setup successfully

---

## Technical Implementation Details

### Audio Processing Pipeline

```
Microphone (16kHz, 16-bit, mono)
    ↓
I2S Driver (512 sample chunks = 32ms)
    ↓
Circular Buffer (1 second = 32KB)
    ↓
Audio Processor (noise gate, AGC)
    ↓
Wyoming Protocol (PCM packets)
    ↓
Backend (Whisper STT)
    ↓
Transcription Result
    ↓
LLM Processing
    ↓
Response → TTS
```

### Buffer Sizes & Latency

- Microphone sample rate: 16kHz
- Bits per sample: 16-bit
- Channels: 1 (mono)
- I2S chunk: 512 samples = 32ms
- Circular buffer: 32KB = 1 second
- Network packet: ~1KB = 64ms of audio
- Total latency target: <500ms

---

## Estimated Timeline

**Week 1 (40 hours):**
- Tasks 7.1-7.2: Audio hardware & buffers (18 hrs)
- Task 7.3: Wyoming streaming (10 hrs)
- Task 7.4: Whisper integration (12 hrs - carry over)

**Week 2 (40 hours):**
- Task 7.4: Whisper integration (continued, 8 hrs)
- Tasks 7.5-7.9: Logging, PTT, wake word, quality, error handling (40 hrs)
- Tasks 7.10-7.11: Integration testing, documentation (12 hrs)

**Total: ~80 hours (~2 weeks)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Audio quality poor on hardware | Medium | High | Test early; optimize preprocessing |
| PCM transmission unreliable | Medium | High | Implement retransmission; error checking |
| Whisper latency too high | Low | Medium | Model optimization; quantization |
| Memory constraints on device | Medium | Medium | Optimize buffer sizes; periodic cleanup |
| Network bandwidth issues | Low | Medium | Compress audio; adaptive bitrate |
| Wake word false positives | Medium | Low | Tune threshold; better model |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Audio recording from box3b microphone
- [ ] PCM streaming to backend via Wyoming
- [ ] Whisper STT operational
- [ ] Push-to-talk mode functional
- [ ] Wake word detection working
- [ ] Full audio chain end-to-end

### Performance
- [ ] Recording latency <500ms
- [ ] STT latency <3 seconds
- [ ] No data loss in normal operation
- [ ] System stable for 8+ hours
- [ ] Speech accuracy >90%

### Reliability
- [ ] Recovers from network failures
- [ ] No memory leaks
- [ ] Graceful error handling
- [ ] Logs capture all issues

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic enables audio input as outlined in Phase 4. Recording is essential for the voice assistant workflow and enables wake word detection and conversation initiation.

**Dependencies Met:** Epic 1, 6 (backend ready)
**Enables:** Epic 8 (playback), Epic 10 (continuous conversation)

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-06-09 (Epic 6 completion + 2 weeks)
