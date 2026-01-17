# STT/TTS Services Guide

This guide explains how to use the Speech-to-Text (Whisper) and Text-to-Speech (Piper) services in Chatterbox3B.

## Overview

Chatterbox3B now provides dedicated STT and TTS services through:
- **Wyoming Protocol** - Native integration with ESP32 and other Wyoming clients
- **REST API** - JSON-based API for HTTP clients
- **Agent Tools** - LangChain tools for agent-driven speech processing

## Architecture

### Service Modes

The server can run in different modes to suit your needs:

| Mode | Description | Wyoming | REST | Agent |
|------|-------------|---------|------|-------|
| `full` | Voice assistant with all features | ✓ | ✓ | ✓ |
| `stt_only` | Transcription service only | ✓ | ✓ | ✗ |
| `tts_only` | Speech synthesis service only | ✓ | ✓ | ✗ |
| `combined` | STT + TTS without agent | ✓ | ✓ | ✓ |

## Configuration

### Environment Variables

Set these variables to configure the services:

```bash
# Server mode
CHATTERBOX_SERVER_MODE=full              # full, stt_only, tts_only, combined

# STT Configuration
CHATTERBOX_STT_MODEL=base                # tiny, base, small, medium, large
CHATTERBOX_STT_DEVICE=cpu                # cpu, cuda
CHATTERBOX_STT_LANGUAGE=                 # Leave empty for auto-detect

# TTS Configuration
CHATTERBOX_TTS_VOICE=en_US-lessac-medium
CHATTERBOX_TTS_SAMPLE_RATE=22050

# Ollama Configuration (for 'full' or 'combined' modes)
CHATTERBOX_OLLAMA_BASE_URL=http://localhost:11434/v1
CHATTERBOX_OLLAMA_MODEL=llama3.1:8b
CHATTERBOX_OLLAMA_TEMPERATURE=0.7

# REST API
CHATTERBOX_ENABLE_REST=true
CHATTERBOX_REST_PORT=8080

# Server binding
CHATTERBOX_HOST=0.0.0.0
CHATTERBOX_PORT=10700
```

### CLI Arguments

Override settings via command-line:

```bash
# Start server in STT-only mode
chatterbox3b-server --mode stt_only

# Enable REST API
chatterbox3b-server --rest --rest-port 8080

# Enable debugging
chatterbox3b-server --debug
```

## Using Wyoming Protocol

### STT via Wyoming

The STT service expects audio in this format:
- Sampling rate: 16000 Hz
- Channels: 1 (mono)
- Format: S16_LE (signed 16-bit little endian)
- Chunk size: 2048-3200 bytes per message

**Client sequence:**
1. Send `AudioStart`
2. Send multiple `AudioChunk` events with audio data
3. Send `AudioStop`
4. Send `Transcribe` event
5. Receive `Transcript` event with transcribed text

### TTS via Wyoming

**Client sequence:**
1. Send `Synthesize` event with text
2. Receive `AudioStart`
3. Receive multiple `AudioChunk` events with audio data
4. Receive `AudioStop`

### Example: Wyoming Client

```python
import asyncio
from wyoming.event import Event
from wyoming.asr import Transcribe
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.client import AsyncClient

async def example_stt():
    """Transcribe audio via Wyoming protocol."""
    async with AsyncClient("localhost", 10700) as client:
        # Send audio
        await client.write_event(AudioStart())

        # Read audio file
        with open("audio.wav", "rb") as f:
            audio_data = f.read()

        # Send in chunks
        for i in range(0, len(audio_data), 2048):
            chunk = audio_data[i:i+2048]
            await client.write_event(AudioChunk(audio=chunk))

        await client.write_event(AudioStop())
        await client.write_event(Transcribe())

        # Read response
        event = await client.read_event()
        print(f"Transcription: {event.text}")
```

## Using REST API

Enable the REST API with:
```bash
chatterbox3b-server --rest
```

The API will be available at `http://localhost:8080`

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "ok",
  "mode": "full",
  "services": {
    "stt": true,
    "tts": true,
    "agent": true
  }
}
```

### Speech-to-Text

**Transcribe audio file:**

```bash
curl -X POST http://localhost:8080/stt \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

Response:
```json
{
  "text": "Hello world",
  "language": "en",
  "confidence": 0.95
}
```

**Transcribe file (uses file path):**

```bash
curl -X POST http://localhost:8080/stt/file \
  -F "file=@audio.wav"
```

Supports WAV, MP3, FLAC formats.

### Text-to-Speech

**Synthesize text to speech:**

```bash
curl -X POST http://localhost:8080/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output speech.wav
```

Returns WAV audio file.

### Chat (Requires `full` or `combined` mode)

**Send text to agent:**

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the current time?"}'
```

Response:
```json
{
  "response": "The current time is 3:45 PM."
}
```

### Full Pipeline (Requires `full` mode)

**Complete STT → Agent → TTS pipeline:**

```bash
curl -X POST http://localhost:8080/stt-chat-tts \
  -F "file=@question.wav" \
  --output response.wav
```

Response:
```json
{
  "transcription": "What is the weather?",
  "language": "en",
  "agent_response": "I don't have weather information.",
  "audio_bytes": 44100,
  "audio_format": "wav"
}
```

## Using Agent Tools

When the server is in `full` or `combined` mode, the agent has access to STT and TTS tools.

### Available Tools

1. **`transcribe_audio`** - Transcribe audio file to text
   - Input: File path (string)
   - Output: Transcription with confidence

2. **`synthesize_speech`** - Convert text to speech
   - Input: Text and optional output path
   - Output: Path to generated WAV file

### Example: Using Tools in Agent

```python
from cackle.agent import VoiceAssistantAgent

agent = VoiceAssistantAgent(
    ollama_base_url="http://localhost:11434/v1",
    ollama_model="llama3.1:8b",
)

# The agent can now use transcribe_audio and synthesize_speech tools
response = await agent.process_input(
    "Transcribe the audio file at /tmp/recording.wav and tell me what it says"
)
```

The agent will automatically:
1. Use the `transcribe_audio` tool to transcribe the file
2. Process the transcription
3. Generate a response

## Whisper Models

### Model Sizes

Available Whisper model sizes (larger = more accurate but slower):

- `tiny` - ~39M parameters (fastest)
- `base` - ~74M parameters
- `small` - ~244M parameters
- `medium` - ~769M parameters
- `large` - ~1.5B parameters (most accurate, slowest)

**Recommendation:** Start with `base` for a good balance of speed and accuracy.

### Language Support

Whisper supports 99 languages. Set the language with:

```bash
CHATTERBOX_STT_LANGUAGE=en  # English
CHATTERBOX_STT_LANGUAGE=es  # Spanish
CHATTERBOX_STT_LANGUAGE=    # Auto-detect (default)
```

## Piper Voices

### Available Voices

Piper includes voices for multiple languages and genders:

- English: `en_US-lessac-medium`, `en_US-grayson-medium`, etc.
- Spanish: `es_ES-tux-medium`, etc.
- French: `fr_FR-siwis-medium`, etc.
- See full list: https://github.com/rhasspy/piper/blob/master/voices.json

### Voice Configuration

```bash
CHATTERBOX_TTS_VOICE=en_US-grayson-medium
CHATTERBOX_TTS_SAMPLE_RATE=22050
```

## Performance Considerations

### Model Loading

Models are loaded on server startup to provide low-latency responses:
- STT model loads on startup (can take 10-30 seconds)
- TTS voice loads on startup (can take 5-10 seconds)

### Memory Usage

Approximate memory requirements:
- Whisper `tiny`: 500 MB
- Whisper `base`: 700 MB
- Whisper `large`: 2.5+ GB
- Piper TTS: 100-200 MB

### GPU Acceleration

To use GPU acceleration:

```bash
CHATTERBOX_STT_DEVICE=cuda  # Requires NVIDIA GPU and CUDA
```

Then run on a machine with GPU:
```bash
pip install -e ".[cuda]"  # Install CUDA-enabled packages
```

## Troubleshooting

### Models Take Too Long to Load

Models download on first use:
- Check your internet connection
- Models cache in `~/.cache/huggingface/hub/`
- Use smaller models (`tiny`, `base`) for faster loading

### Memory Issues

If you get out-of-memory errors:
1. Use smaller Whisper model (`tiny` instead of `large`)
2. Enable GPU acceleration if available
3. Run in `stt_only` or `tts_only` mode instead of `full`

### Audio Quality Issues

For better transcription:
1. Use higher Whisper model (`base` or `small`)
2. Ensure audio is clear with minimal background noise
3. Reduce background noise before sending to STT

### Ollama Not Found

Ensure Ollama is running:
```bash
ollama serve
```

In another terminal:
```bash
ollama pull llama3.1:8b
chatterbox3b-server
```

## Examples

### Running STT-Only Service

```bash
export CHATTERBOX_SERVER_MODE=stt_only
export CHATTERBOX_STT_MODEL=base
export CHATTERBOX_HOST=0.0.0.0
export CHATTERBOX_PORT=10700

chatterbox3b-server
```

### Running Full Voice Assistant with REST API

```bash
export CHATTERBOX_SERVER_MODE=full
export CHATTERBOX_ENABLE_REST=true
export CHATTERBOX_REST_PORT=8080

chatterbox3b-server
```

### Using Custom Ollama Model

```bash
ollama pull mistral:7b

export CHATTERBOX_OLLAMA_MODEL=mistral:7b
chatterbox3b-server
```

## API Reference

### STT Service

```python
from cackle.services import WhisperSTTService

stt = WhisperSTTService(
    model_size="base",
    device="cpu",
    language=None,  # Auto-detect
    compute_type="int8"
)

# Load model (called automatically on first use)
await stt.load_model()

# Transcribe audio
result = await stt.transcribe(audio_bytes)
# Returns: {
#   "text": "transcribed text",
#   "language": "en",
#   "confidence": 0.95
# }

# Transcribe file
result = await stt.transcribe_file("/path/to/audio.wav")
```

### TTS Service

```python
from cackle.services import PiperTTSService

tts = PiperTTSService(
    voice="en_US-lessac-medium",
    sample_rate=22050
)

# Load voice (called automatically on first use)
await tts.load_voice()

# Synthesize text
audio_bytes = await tts.synthesize("Hello world")

# Synthesize to file
await tts.synthesize_to_file("Hello world", "/tmp/speech.wav")
```

## Additional Resources

- [Whisper Documentation](https://github.com/openai/whisper)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Wyoming Protocol](https://github.com/rhasspy/wyoming)
