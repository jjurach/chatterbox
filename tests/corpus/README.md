# Test Corpus — Wyoming Protocol STT Validation

**Status:** Complete (Task 3.3, 2026-02-19)
**Related Epic:** Epic 3 - Wyoming Protocol Implementation and Validation

## Overview

15 WAV files generated with Piper TTS for repeatable, automated validation of the
Chatterbox Wyoming STT service (Whisper-based). Used by the `ha_emulator` test
harness (Task 3.4).

## Audio Format

| Property | Value |
|---|---|
| Format | PCM WAV |
| Sample Rate | 22050 Hz (source; resampled to 16000 Hz by `AudioProcessor`) |
| Bit Depth | 16-bit |
| Channels | Mono |
| Voice Model | `en_US-ljspeech-high` (Piper) |

> **Note:** The WAV files are stored at 22050 Hz (Piper's native output). The
> `AudioProcessor` class resamples to 16000 Hz before sending via Wyoming protocol,
> which is what the Whisper STT service expects.

## Corpus Entries

| File | Expected Transcription | Category | Duration |
|---|---|---|---|
| `test_001_turn_on_lights.wav` | turn on the lights | home_control | 1.1s |
| `test_002_weather_kansas.wav` | what is the weather in kansas | weather | 1.8s |
| `test_003_turn_off_lights.wav` | turn off the lights | home_control | 1.3s |
| `test_004_play_music.wav` | play some music | media | 1.1s |
| `test_005_weather_tomorrow.wav` | what will the weather be like tomorrow | weather | 1.8s |
| `test_006_set_timer.wav` | set a timer for ten minutes | utility | 1.7s |
| `test_007_short_yes.wav` | yes | edge_case | 0.5s |
| `test_008_short_no.wav` | no | edge_case | 0.5s |
| `test_009_lock_the_door.wav` | lock the front door | home_control | 1.1s |
| `test_010_temperature_inside.wav` | what is the temperature inside | environment | 1.7s |
| `test_011_good_morning.wav` | good morning | edge_case | 0.7s |
| `test_012_long_complex.wav` | what is the current temperature in new york city and will it rain this afternoon | edge_case | 4.6s |
| `test_013_open_garage.wav` | open the garage door | home_control | 1.4s |
| `test_014_is_anyone_home.wav` | is anyone home | environment | 1.0s |
| `test_015_bedroom_lights_dim.wav` | turn on the bedroom lights at fifty percent | home_control | 2.3s |

## Categories

- **home_control** — Device commands (lights, locks, garage)
- **weather** — Weather queries (current and forecast)
- **media** — Media playback commands
- **utility** — Timer and scheduling commands
- **environment** — Indoor conditions queries
- **edge_case** — Short utterances, long utterances, minimal responses

## Regenerating the Corpus

The corpus was generated with [Piper TTS](https://github.com/rhasspy/piper):

```bash
# Requires: piper binary in PATH, en_US-ljspeech-high.onnx model
echo "turn on the lights" | piper \
  -m /path/to/en_US-ljspeech-high.onnx \
  -f tests/corpus/test_001_turn_on_lights.wav
```

Voice model used: `en_US-ljspeech-high` (available from
[Piper voices](https://github.com/rhasspy/piper/releases)).

## Usage

The `CorpusLoader` class in `src/ha_emulator/corpus.py` reads this directory:

```python
from ha_emulator.corpus import CorpusLoader
from pathlib import Path

loader = CorpusLoader(Path("tests/corpus"))
entries = loader.load_all()
for entry in entries:
    print(entry.wav_path, "→", entry.expected_text)
```

## Validation Expectations

Whisper STT should achieve ≥90% word accuracy (WER ≤ 0.10) on all entries.

- **Short utterances** (test_007, test_008, test_011): May have slightly lower
  accuracy due to minimal context, but expected to pass.
- **Long utterance** (test_012): Edge case; may hit latency limits.
- **Location names** (test_002, test_012): "kansas", "new york city" — Whisper
  typically handles these well.
