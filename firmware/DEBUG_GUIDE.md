# Voice Assistant Debug & Observability Guide

## Overview

The `voice-assistant.yaml` has been enhanced with comprehensive debug logging to help diagnose issues with wake word detection, state machine transitions, and voice assistant functionality.

---

## What Was Added

### 1. Logger Configuration (Lines 64-75)
```yaml
logger:
  hardware_uart: USB_SERIAL_JTAG
  level: DEBUG
  logs:
    micro_wake_word: DEBUG
    voice_assistant: DEBUG
    state_machine: DEBUG
    i2s_audio: DEBUG
    microphone: DEBUG
    audio_adc: DEBUG
    media_player: DEBUG
```

**What this does:**
- Enables DEBUG-level logging globally
- Enables specific component-level debugging for:
  - `micro_wake_word` - Wake word detection model
  - `voice_assistant` - Core voice processing
  - `state_machine` - State transitions
  - `i2s_audio` - Audio I/O
  - `microphone` - Microphone input
  - `audio_adc` - Audio sampling
  - `media_player` - Speaker output

### 2. Event Logging - Micro Wake Word (Lines 191-198)
```yaml
on_wake_word_detected:
  - logger.log:
      format: "🎤 WAKE WORD DETECTED! Model: %s"
      args: ["x.wake_word"]
      level: INFO
```

**What to look for in logs:**
```
[HH:MM:SS][I][micro_wake_word:xxx]: 🎤 WAKE WORD DETECTED! Model: okay_nabu
```

If you DON'T see this message after saying wake words, the microphone isn't detecting speech.

### 3. Event Logging - Voice Assistant (Lines 208-249)
```yaml
on_stt_end:         # Speech-to-text finished
on_tts_start:       # Text-to-speech starting
on_tts_end:         # Text-to-speech finished
on_error:           # Error occurred
on_client_connected: # Home Assistant connected
on_client_disconnected: # Home Assistant disconnected
```

**Expected log sequence for a successful interaction:**
```
✅ Home Assistant CLIENT CONNECTED - voice assistant ready
😴 STATE MACHINE → IDLE
🎤 WAKE WORD DETECTED! Model: okay_nabu
👂 STATE MACHINE → LISTENING
📝 STT END event fired
🧠 STATE MACHINE → THINKING
🔊 TTS START event fired
🗣️  STATE MACHINE → REPLYING
🔉 TTS END event fired
😴 STATE MACHINE → IDLE
```

### 4. State Machine Logging (Lines 304-337)
Each state now logs when entered:
```
🔄 STATE MACHINE → UNINITIALIZED
😴 STATE MACHINE → IDLE
👂 STATE MACHINE → LISTENING
🧠 STATE MACHINE → THINKING
🗣️  STATE MACHINE → REPLYING
💥 STATE MACHINE → ERROR
```

---

## How to Use This Debug Information

### Scenario 1: Wake Word Never Detected

**Symptom:** Device boots, you say "Hey Jarvis" but nothing happens

**Check the logs for:**
1. ✅ `✅ Home Assistant CLIENT CONNECTED` - If missing, HA isn't connected
2. ✅ `😴 STATE MACHINE → IDLE` - If missing, state machine didn't start
3. ❌ `🎤 WAKE WORD DETECTED` - If missing, microphone or wake word model isn't working

**Diagnosis:**
- If you see (1) & (2) but not (3): **Microphone issue** or **wake word model issue**
  - Check `audio_adc: DEBUG` and `microphone: DEBUG` logs
  - Check `micro_wake_word: DEBUG` logs
  - Verify microphone is working (should see audio input in logs)

- If you don't see (1): **Home Assistant not connected**
  - Check WiFi connection
  - Check ESPHome API connection to Home Assistant

### Scenario 2: Wake Word Detected But Doesn't Transition to Listening

**Symptom:** Log shows `🎤 WAKE WORD DETECTED` but no `👂 LISTENING` state

**Check:**
- State machine not receiving the `wake_word_detected` input
- State machine is in wrong state (not `idle`)
- Hardware issue preventing state transition

**This is the issue described in your original error:**
```
[17:58:25.037][W][state_machine:101]: boot_successful: no transition from idle
```

This means the state machine is already in `idle` state when `boot_successful` arrives again, so it rejects the transition (state machines prevent invalid transitions).

### Scenario 3: Speech Detected But STT Not Processing

**Symptom:** See `👂 LISTENING` but no `📝 STT END`

**Check:**
- Home Assistant voice pipeline not running
- Whisper STT service not responding
- Network issue between ESP32 and HA

### Scenario 4: Everything Works Once, Then Fails

**Symptom:** First command works, second doesn't

**Check:**
- Look for `⚠️  Home Assistant CLIENT DISCONNECTED`
- If you see it, HA connection dropped
- The device may reconnect but state machine might be out of sync

---

## Interpreting Debug Logs

### Good Sign - You Should See These:
```
✅ Home Assistant CLIENT CONNECTED
😴 STATE MACHINE → IDLE
🎤 WAKE WORD DETECTED
👂 STATE MACHINE → LISTENING
📝 STT END
🧠 STATE MACHINE → THINKING
🔊 TTS START
🗣️  STATE MACHINE → REPLYING
🔉 TTS END
😴 STATE MACHINE → IDLE
```

### Bad Sign - You Should NOT See These:
```
❌ VOICE ASSISTANT ERROR
💥 STATE MACHINE → ERROR
⚠️  Home Assistant CLIENT DISCONNECTED
boot_successful: no transition from idle
```

### Research Finding: VAD Model Conflicts

From ESPHome research, one known issue is:
```
Wake word model predicts 'Okay Nabu', but VAD model doesn't
```

This means:
- Microphone detected speech
- Wake word model matched
- But Voice Activity Detection (VAD) filtered it out as not being real speech

**Solution:** May need to adjust `probability_cutoff` or disable VAD model initially for testing

---

## How to Enable/Disable Debug Logging

### Enable Full Debug (Verbose)
```yaml
logger:
  level: VERY_VERBOSE
```

⚠️ **Warning:** VERY_VERBOSE can slow down device and cause memory issues. Only use for short debugging sessions.

### Disable Debug (Normal Operation)
```yaml
logger:
  level: INFO
```

Remove the `logs:` section or change levels back to `INFO`.

---

## Next Steps After Adding Debug Logging

1. **Compile and flash** the updated firmware
2. **Watch the serial output** for wake word attempts
3. **Send the log output** with initial boot sequence
4. **Identify which step** is failing using the scenarios above

---

## Research References

- [ESPHome Logger Component](https://www.esphome.io/components/logger/)
- [ESPHome Voice Assistant](https://www.esphome.io/components/voice_assistant/)
- [ESPHome Micro Wake Word](https://www.esphome.io/components/micro_wake_word/)
- [Logging Best Practices](https://developers.esphome.io/architecture/logging/)
- [Home Assistant Voice Assistant Troubleshooting](https://www.home-assistant.io/voice_control/troubleshooting/)
