# Mellona Integration: Chatterbox Migration Notes

This document explains how mellona is integrated into chatterbox and provides chatterbox-specific setup guidance.

## Mellona Version & Installation

**Mellona version required:** >= 0.1.0

**Installation in chatterbox's venv:**

Mellona is installed as an editable dependency from the sibling `../mellona` module:

```toml
# In pyproject.toml
[tool.poetry.dependencies]
mellona = { path = "../mellona", editable = true }
```

Install or update mellona in chatterbox's virtual environment:

```bash
cd /home/phaedrus/hentown/modules/chatterbox
pip install -e ../mellona
```

## Chatterbox STT/TTS Architecture

Chatterbox provides two services that wrap mellona's providers:

### WhisperSTTService (Speech-to-Text)

**Location:** `src/chatterbox/services/stt.py:WhisperSTTService`

This service wraps mellona's STT providers (primarily **FasterWhisper**) while maintaining backward compatibility with the existing chatterbox interface.

**Key implementation details:**

- Uses `get_manager().get_stt_provider("faster_whisper")` to get the STT provider
- Accepts raw PCM bytes (S16_LE format) and sample rate (default 16000 Hz)
- Converts PCM bytes to temporary WAV files (mellona requires file paths)
- Returns results in the chatterbox format:
  ```python
  {
      "text": str,           # Transcribed text
      "language": str,       # Detected language code
      "confidence": float,   # Always 0.0 (mellona doesn't provide confidence)
  }
  ```
- Supports both `transcribe(audio_data, sample_rate)` and `transcribe_file(file_path)` methods

**Configuration in mellona:**

The STT service uses the FasterWhisper provider configured in mellona. Configure it in `~/.config/mellona/config.yaml`:

```yaml
providers:
  faster_whisper:
    model: base              # tiny, base, small, medium, large
    device: cpu              # cpu or cuda for GPU

stt_profiles:
  default:
    provider: faster_whisper
    model: base
```

### PiperTTSService (Text-to-Speech)

**Location:** `src/chatterbox/services/tts.py:PiperTTSService`

This service wraps mellona's TTS providers (primarily **Piper**) while maintaining backward compatibility with the existing chatterbox interface.

**Key implementation details:**

- Uses `get_manager().get_tts_provider("piper")` to get the TTS provider
- Accepts voice name (default "en_US-lessac-medium") and sample rate (default 22050 Hz)
- Returns raw PCM audio bytes (S16_LE format) at the configured sample rate
- Supports both `synthesize(text)` and `synthesize_to_file(text, file_path)` methods
- Voice loading is a no-op (mellona manages lifecycle)

**Configuration in mellona:**

Configure Piper in `~/.config/mellona/config.yaml`:

```yaml
providers:
  piper:
    voice: en_US-lessac-medium    # Default voice
    sample_rate: 22050             # Sample rate in Hz

tts_profiles:
  default:
    provider: piper
    voice: en_US-lessac-medium
```

## Python API: Using STT and TTS in Chatterbox

### Basic STT Usage

```python
from chatterbox.services.stt import WhisperSTTService
import asyncio

async def transcribe_audio():
    stt = WhisperSTTService(model_size="base", device="cpu")

    # From raw PCM bytes
    audio_bytes = b"..."  # Your 16-bit PCM audio
    result = await stt.transcribe(audio_bytes, sample_rate=16000)
    print(f"Transcribed: {result['text']}")

    # From file
    result = await stt.transcribe_file("audio.wav")
    print(f"Transcribed: {result['text']}")

asyncio.run(transcribe_audio())
```

### Basic TTS Usage

```python
from chatterbox.services.tts import PiperTTSService
import asyncio

async def synthesize_text():
    tts = PiperTTSService(voice="en_US-lessac-medium", sample_rate=22050)

    # Get raw audio bytes
    audio_bytes = await tts.synthesize("Hello, world!")
    print(f"Synthesized: {len(audio_bytes)} bytes of audio")

    # Or save to file
    await tts.synthesize_to_file("Hello, world!", "output.wav")

asyncio.run(synthesize_text())
```

## Common Patterns

### Checking Provider Availability

```python
from mellona import get_manager

manager = get_manager()
stt_provider = manager.get_stt_provider("faster_whisper")
tts_provider = manager.get_tts_provider("piper")

if stt_provider:
    print("STT provider available")
if tts_provider:
    print("TTS provider available")
```

### PCM to WAV Conversion Pattern

(Used internally by WhisperSTTService)

```python
import wave
import tempfile

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    """Convert PCM bytes to WAV file and return path."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp.name, "wb") as wav_file:
            wav_file.setnchannels(1)          # Mono
            wav_file.setsampwidth(2)          # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        return tmp.name
```

### WAV from Bytes Pattern

(Used internally by PiperTTSService)

```python
import wave

def bytes_to_wav(pcm_bytes: bytes, output_path: str, sample_rate: int = 22050):
    """Write PCM bytes to WAV file."""
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)        # Mono
        wav_file.setsampwidth(2)        # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
```

## Configuration File Location

Mellona uses the default configuration file location: **`~/.config/mellona/config.yaml`**

Example configuration for chatterbox:

```yaml
# ~/.config/mellona/config.yaml
default_provider: ollama

providers:
  # STT Providers
  faster_whisper:
    model: base
    device: cpu

  # TTS Providers
  piper:
    voice: en_US-lessac-medium
    sample_rate: 22050

# STT Configuration
stt_profiles:
  default:
    provider: faster_whisper
    model: base

# TTS Configuration
tts_profiles:
  default:
    provider: piper
    voice: en_US-lessac-medium
```

## Gotchas & Known Issues

### 1. Temp File Cleanup

WhisperSTTService creates temporary WAV files for transcription. They should be automatically cleaned up, but if the service crashes, check `/tmp/` for orphaned `.wav` files.

### 2. Model Caching

Both FasterWhisper and Piper download and cache models on first use:

- **FasterWhisper models:** `~/.cache/mellona/whisper/`
- **Piper models:** `~/.cache/mellona/piper/`

First-run downloads can be slow (1-2GB for large Whisper models, 50-200MB for Piper voices).

### 3. GPU Support

To enable GPU support (CUDA) for FasterWhisper:

```bash
pip install faster-whisper[gpu]
```

Then configure in `~/.config/mellona/config.yaml`:

```yaml
providers:
  faster_whisper:
    device: cuda  # Instead of cpu
```

### 4. Audio Format Requirements

- **STT input:** Mellona expects file paths (WAV, MP3, etc. - format auto-detected)
- **TTS output:** Mellona returns raw PCM bytes in S16_LE format
- **Chatterbox format:** Both services expect/return raw PCM bytes (S16_LE)

### 5. Confidence Scores

Mellona's STT providers don't expose per-segment confidence scores. The `confidence` field in WhisperSTTService results is always `0.0`. If you need segment-level confidence, use FasterWhisper directly instead of mellona.

## Migration from Old Services

If you're migrating from direct FasterWhisper/Piper usage to mellona:

### Before (Old Pattern)
```python
from faster_whisper import WhisperModel
from piper import PiperTTS

whisper = WhisperModel("base")
result = whisper.transcribe("audio.wav")
```

### After (Mellona Pattern)
```python
from chatterbox.services.stt import WhisperSTTService

stt = WhisperSTTService(model_size="base")
result = await stt.transcribe_file("audio.wav")
```

The mellona approach:
- ✅ Centralizes configuration
- ✅ Supports multiple providers (Groq, FasterWhisper, LocalWhisper)
- ✅ Manages model caching
- ✅ Provides unified error handling

## Troubleshooting

### "FasterWhisper STT provider not available"

**Cause:** faster-whisper not installed or mellona not configured

**Fix:**
```bash
pip install faster-whisper
# Ensure mellona is installed and configured
pip install mellona
```

### "Piper TTS provider not available"

**Cause:** piper-tts not installed or mellona not configured

**Fix:**
```bash
pip install piper-tts
# Ensure mellona is installed
pip install mellona
```

### "RuntimeError: STT provider not available"

The provider failed to initialize. Check:
1. Is `~/.config/mellona/config.yaml` configured?
2. Is faster-whisper installed?
3. Check logs for more details

### "Model download takes forever"

Models are downloaded to cache directories on first use. This is normal for:
- FasterWhisper models (1-2GB for `large`)
- Piper voices (50-200MB)

You can pre-download models:
```bash
# For FasterWhisper
from mellona import MellonaClient
import asyncio

async def preload():
    client = MellonaClient()
    manager = client._manager
    stt_provider = manager.get_stt_provider("faster_whisper")
    # Just accessing the provider triggers model download
```

## See Also

- [Mellona STT/TTS Integration Guide](./mellona-stt-tts-integration.md) — Full Mellona API documentation
- [Mellona Provider Reference](./mellona-provider-reference.md) — All providers and their configuration
- [Mellona Config Example](./mellona-config-example.yaml) — Example configuration file
