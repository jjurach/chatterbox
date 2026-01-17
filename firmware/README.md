# ESPHome Voice Assistant with State Machine

This document outlines the process of updating the `voice-assistant.yaml` to implement a more robust, state-driven voice assistant.

## Initial Request

The initial request was to improve the functionality of the ESPHome voice assistant, which was based on the `esp32-s3-box-3`. The original implementation had several limitations:

*   The device would get stuck in a state where it was listening for a wake word, but the wake word button would never reappear.
*   The smiley-face house icon never changed to indicate the device's state.
*   There was no concept of a "loop" or a state diagram sequence to return the device to its default, quiet, listening state.

The request also included a desire for a more feature-rich experience, such as:

*   A house-face that looks awake while listening and asleep otherwise.
*   A face that looks ill or dead if the device hasn't initialized successfully.
*   The ability for the device to play PCM packets transmitted to it by Home Assistant.

## Implementation Steps

To address these requirements, the following steps were taken:

### 1. Research

The first step was to research existing ESPHome voice assistant projects to see if there was a pre-existing solution that could be adapted. The research revealed that a "fake alexa" based on the `esp32-s3-box-3` and ESPHome was a common project, but that the existing solutions did not provide the desired level of state management and UI feedback.

Further research into ESPHome state machine implementations led to the discovery of the `esphome-state-machine` custom component by `muxa`.

### 2. State Machine Implementation

The `esphome-state-machine` component was integrated into the `voice-assistant.yaml` file. This involved the following changes:

*   **Adding the `esphome-state-machine` component:** The `external_components` section was updated to include the `esphome-state-machine` component from its GitHub repository.

*   **Defining the state machine:** A `state_machine` component was added to the `voice-assistant.yaml` file with the following states:
    *   `uninitialized`
    *   `idle`
    *   `listening`
    *   `thinking`
    *   `replying`
    *   `error`

*   **Defining the state machine inputs:** The `state_machine` component was configured with the following inputs to trigger state transitions:
    *   `boot_successful`
    *   `wake_word_detected`
    *   `stt_end`
    *   `tts_start`
    *   `tts_end`
    *   `silence_detected`
    *   `va_error`
    *   `error_cleared`

*   **Defining the state machine transitions:** The `state_machine` component was configured with transitions between the states based on the defined inputs.

### 3. Display Logic Update

The display logic was updated to reflect the current state of the state machine. This was achieved by adding `on_enter` actions to each state in the `state_machine` component. These actions show the corresponding page on the display.

The following pages were created:

*   `uninitialized_page`
*   `idle_page`
*   `listening_page`
*   `thinking_page`
*   `replying_page`
*   `error_page`

### 4. Code Cleanup

The `voice-assistant.yaml` file was cleaned up to remove unused code. This included removing:

*   The old `voice_assistant_phase` global variable and its associated scripts.
*   Unused event handlers from the `wifi`, `api`, and `media_player` components.
*   Unused pages from the `display` component.

## How to Use

To use the new configuration, simply run the following command:

```
esphome run voice-assistant.yaml
```

The device will now boot into the `uninitialized` state, and then transition to the `idle` state. When the wake word is detected, the device will transition to the `listening` state, and so on. The display will update to reflect the current state of the device.
