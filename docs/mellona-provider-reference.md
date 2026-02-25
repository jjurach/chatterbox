# Mellona Provider Reference (STT/TTS)

This document lists STT/TTS providers available in Mellona, their configuration, and how to use them in chatterbox.

## Speech-to-Text (STT) Providers

### Groq STT

**What it does:** Cloud-based Whisper transcription via Groq's API. Fast, accurate speech-to-text.

**Best for:** Production transcription, real-time audio processing.

**Credentials:**
- **Environment variable:** `GROQ_API_KEY`
- **Keyring key:** `mellona/groq_api_key`
- **Config file key:** `providers.groq.api_key`

**Configuration:**

```yaml
providers:
  groq:
    api_key: ${GROQ_API_KEY}
    # Optional: override default model
    # model: whisper-large-v3
```

**API Key:** Obtain from [Groq Console](https://console.groq.com) (free tier available)

**Usage:**

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    response = client.transcribe("audio.wav", provider="groq")
    print(response.text)
    # response.language, response.duration_seconds also available
```

**Parameters:**
- `language` — BCP-47 code (e.g., "en", "fr", "es"). Auto-detected if not provided.
- `prompt` — Context hint to help transcription (e.g., "technical jargon: quantum computing")
- `temperature` — Transcription randomness (0.0–1.0, usually not needed)
- `response_format` — "text" (default), "json", "verbose_json", "srt", "vtt"

**Default Model:** `whisper-large-v3`

**Pricing:** Pay-as-you-go based on audio minutes. Check [Groq pricing](https://groq.com/pricing)

---

### FasterWhisper

**What it does:** Local Whisper-compatible STT using faster-whisper (optimized C++ implementation). Fast, accurate speech-to-text with no cloud dependencies.

**Best for:** Development, testing, privacy-critical applications, local transcription with high performance.

**Credentials:** None required (local execution, no auth)

**Configuration:**

```yaml
providers:
  faster_whisper:
    model: base                         # Model size: tiny, base, small, medium, large
    device: cpu                         # Device: cpu or cuda (if NVIDIA available)
```

**Setup:**

1. Install faster-whisper: `pip install faster-whisper`
2. For CUDA support (GPU acceleration): `pip install faster-whisper[gpu]`
3. Configure in your Mellona config file

**Available Models:**
- `tiny` — Fastest, lowest accuracy (~39M parameters)
- `base` — Balanced speed/accuracy (~74M parameters, default)
- `small` — Higher accuracy (~244M parameters)
- `medium` — High accuracy (~769M parameters)
- `large` — Highest accuracy (~1.5B parameters)

**Usage:**

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    response = client.transcribe("audio.wav", provider="faster_whisper")
    print(response.text)
```

**Parameters:**
- `language` — BCP-47 code (e.g., "en", "fr", "es"). Auto-detected if not provided.

**Performance Notes:**
- First run downloads the model (~42MB for tiny, ~1.5GB for large)
- Models are cached in `~/.cache/mellona/whisper/`
- CUDA/GPU acceleration significantly faster for large models
- CPU adequate for small/tiny models and real-time use

**Pricing:** Free (runs locally, hardware cost only)

---

### LocalWhisper

**What it does:** Local Whisper-compatible STT endpoint. No cloud calls, full data privacy.

**Best for:** Development, testing, privacy-critical applications, running on local hardware.

**Credentials:** None required (local endpoint, no auth)

**Configuration:**

```yaml
providers:
  local_whisper:
    url: http://localhost:9090          # Default
    timeout: 300                         # Optional, in seconds
    # Or via environment:
    # url: ${LOCAL_WHISPER_URL}
```

**Setup:**

Use any Whisper-compatible local service:

**Option A: Whisper.cpp with HTTP server**
```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make server
./server
# Listens on http://localhost:8000
```

**Option B: Ollama with Whisper**
```bash
ollama pull whisper
# Then set url: http://localhost:11434/api/audio/transcriptions
```

**Option C: Docker**
```bash
docker run -p 9000:9000 openai/whisper:latest
# Then set url: http://localhost:9000
```

**Usage:**

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    response = client.transcribe("audio.wav", provider="local_whisper")
    print(response.text)
```

**Parameters:** Same as Groq STT (language, prompt, temperature, response_format)

**Default URL:** `http://localhost:9090`

**Default Timeout:** 300 seconds (audio transcription can be slow)

**Pricing:** Free (runs locally, hardware cost only)

---

## Text-to-Speech (TTS) Providers

### Piper TTS

**What it does:** Local text-to-speech synthesis using Piper (open-source, offline, multi-voice support).

**Best for:** Applications requiring natural-sounding speech synthesis, privacy-critical use cases, demo/testing scenarios.

**Credentials:** None required (local execution, no auth)

**Configuration:**

```yaml
providers:
  piper:
    voice: en_US-lessac-medium          # Voice model name
    sample_rate: 22050                  # Sample rate in Hz (optional)
```

**Setup:**

1. Install piper-tts: `pip install piper-tts`
2. Configure in your Mellona config file (voice models auto-download on first use)

**Available Voices:**

Piper supports multiple voices across languages. Common English voices:
- `en_US-lessac-medium` — Default, natural-sounding male voice
- `en_US-libritts-high` — High-quality female voice
- `en_US-ryan-medium` — Medium-quality male voice
- `en_GB-alan-medium` — British English male voice

See [Piper voice list](https://github.com/rhasspy/piper/blob/master/VOICES.md) for complete list.

**Usage:**

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    response = client.synthesize("Hello, world!", provider="piper")
    # response.audio_data contains WAV bytes
    # response.duration_seconds is the audio duration
```

**Parameters:**
- `output_format` — "wav" (default) or "pcm" (raw audio)
- `sample_rate` — Sample rate in Hz (optional, overrides config)

**Performance Notes:**
- First use of a voice downloads the model (~30-200MB depending on voice)
- Models cached in `~/.cache/mellona/piper/`
- Synthesis is fast even on CPU
- Output is always 16-bit PCM audio

**Pricing:** Free (runs locally, hardware cost only)

---

## Configuration Priority Chain

When initializing a provider, Mellona resolves configuration in this order (first-found-wins):

1. **Environment variables** (highest priority)
   ```bash
   export OPENROUTER_API_KEY=sk-...
   export GROQ_API_KEY=gsk-...
   export OLLAMA_URL=http://localhost:11434
   ```

2. **OS Keyring** (if `keyring.enabled: true` and keyring is installed)

3. **Config file** (lowest priority)
   ```yaml
   providers:
     groq:
       api_key: gsk-...
   ```

**Example:**
If you set `GROQ_API_KEY` in the environment AND configure it in `~/.config/mellona/config.yaml`, the environment variable wins.

---

## See Also

- [Mellona STT/TTS Integration Guide](./mellona-stt-tts-integration.md) — How to use STT and TTS
- [Mellona Migration Notes](./mellona-migration-notes.md) — Chatterbox-specific setup
