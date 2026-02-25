# Mellona Speech-to-Text and Text-to-Speech Integration Guide

This guide explains how to use Mellona's STT and TTS features for audio processing in chatterbox.

## Overview: What Mellona Provides for Audio Processing

Mellona provides a unified interface for:

- **Speech-to-Text (STT)**: Convert audio files to text using cloud or local providers
- **Text-to-Speech (TTS)**: Convert text to audio with multiple voice options
- **Provider abstraction**: Switch between cloud and local providers without changing code
- **Configuration profiles**: Define multiple STT/TTS setups and switch them programmatically

### Available STT Providers

- **Groq** — Cloud-based Whisper transcription (fast, accurate, paid)
- **FasterWhisper** — Local Whisper implementation (fast, free, no cloud dependency)
- **LocalWhisper** — Local Whisper-compatible HTTP endpoint (flexible, free)

### Available TTS Providers

- **Piper** — Local text-to-speech synthesis (free, multi-voice, offline)

---

## Transcribing Audio (STT)

### Basic Usage

```python
from mellona import SyncMellonaClient

# Synchronous usage (recommended for scripts and CLIs)
with SyncMellonaClient() as client:
    response = client.transcribe("audio.wav")
    print(f"Transcribed text: {response.text}")
    print(f"Language: {response.language}")
    print(f"Duration: {response.duration_seconds}s")
    print(f"Provider used: {response.provider}")
```

### Choosing STT Providers Programmatically

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    # Use Groq (cloud)
    response = client.transcribe("audio.wav", provider="groq")
    print(f"Groq: {response.text}")

    # Fall back to FasterWhisper (local)
    try:
        response = client.transcribe("audio.wav", provider="groq")
    except Exception:
        print("Groq unavailable, using local provider")
        response = client.transcribe("audio.wav", provider="faster_whisper")

    print(f"Text: {response.text}")
```

### Handling STTResponse

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    response = client.transcribe("interview.wav", provider="groq", language="en")

    # Access transcription results
    transcribed_text = response.text
    detected_language = response.language
    duration = response.duration_seconds

    # Provider information
    provider_name = response.provider
    model_used = response.model

    # Provider-specific metadata
    metadata = response.metadata  # Dict[str, Any]
```

### Passing Options to the STT Provider

```python
from mellona import SyncMellonaClient

with SyncMellonaClient() as client:
    # Groq-specific options
    response = client.transcribe(
        "audio.wav",
        provider="groq",
        language="en",                    # BCP-47 language code
        prompt="technical: quantum computing",  # Context hint
        temperature=0.0,                  # Transcription randomness
        response_format="verbose_json"    # json, verbose_json, srt, vtt, text
    )
    print(response.text)
```

### Error Handling

```python
from mellona import SyncMellonaClient
from mellona.exceptions import (
    AuthenticationError,
    ProviderError,
    ProviderUnavailableError,
)

with SyncMellonaClient() as client:
    try:
        response = client.transcribe("audio.wav", provider="groq")
    except AuthenticationError as e:
        print(f"API key missing or invalid: {e}")
        # Fall back to local provider
        response = client.transcribe("audio.wav", provider="faster_whisper")
    except ProviderUnavailableError as e:
        print(f"Groq not available: {e}")
        response = client.transcribe("audio.wav", provider="faster_whisper")
    except ProviderError as e:
        print(f"Provider error: {e}")
        raise
```

---

## Synthesizing Speech (TTS)

### Basic Usage

```python
from mellona import SyncMellonaClient, TTSRequest
import asyncio

async def synthesize_and_save(text: str, output_file: str):
    from mellona import MellonaClient

    client = MellonaClient()
    manager = client._manager
    tts_provider = manager.get_tts_provider("piper")

    if not tts_provider:
        raise RuntimeError("Piper TTS provider not available")

    request = TTSRequest(text=text)
    response = await tts_provider.synthesize(request)

    # Write audio data to WAV file
    with open(output_file, "wb") as f:
        f.write(response.audio_data)

    print(f"Saved {response.duration_seconds}s of audio to {output_file}")

# Use it
asyncio.run(synthesize_and_save("Hello, this is a test.", "output.wav"))
```

### Getting Raw Bytes for Streaming

```python
from mellona import MellonaClient, TTSRequest
import asyncio

async def synthesize_for_streaming(text: str):
    client = MellonaClient()
    manager = client._manager
    tts_provider = manager.get_tts_provider("piper")

    request = TTSRequest(text=text, output_format="wav")
    response = await tts_provider.synthesize(request)

    # response.audio_data is raw bytes
    # Can stream directly to network, write to pipe, etc.
    return response.audio_data

# Example: write to stdout for piping
import sys
audio_bytes = asyncio.run(synthesize_for_streaming("Stream this!"))
sys.stdout.buffer.write(audio_bytes)
```

### Voice Selection

```python
from mellona import MellonaClient, TTSRequest
import asyncio

async def synthesize_with_voice(text: str, voice: str):
    client = MellonaClient()
    manager = client._manager
    tts_provider = manager.get_tts_provider("piper")

    # Specify voice in request
    request = TTSRequest(
        text=text,
        voice=voice,  # e.g., "en_US-lessac-medium"
    )
    response = await tts_provider.synthesize(request)
    return response.audio_data

# Available Piper voices
voices = [
    "en_US-lessac-medium",      # Default: natural male voice
    "en_US-libritts-high",      # High-quality female voice
    "en_US-ryan-medium",         # Medium-quality male voice
    "en_GB-alan-medium",         # British English male voice
]

# Synthesize with different voices
for voice in voices[:1]:
    audio = asyncio.run(synthesize_with_voice("Hello!", voice))
    print(f"Synthesized with {voice}: {len(audio)} bytes")
```

---

## Full Pipeline: STT → LLM → TTS

### Synchronous Pipeline Example

```python
from mellona import SyncMellonaClient
import asyncio

def full_audio_pipeline(audio_file: str, output_file: str):
    """
    1. Transcribe audio to text
    2. Send text to LLM for processing
    3. Synthesize LLM response to audio
    """
    # Step 1: Transcribe
    with SyncMellonaClient() as client:
        print("Transcribing audio...")
        stt_response = client.transcribe(audio_file, provider="groq")
        user_input = stt_response.text
        print(f"User said: {user_input}")

        # Step 2: LLM call
        print("Processing with LLM...")
        llm_response = client.chat(
            user_input,
            system="You are a helpful assistant.",
            profile="default"
        )
        assistant_reply = llm_response.text
        print(f"Assistant: {assistant_reply}")

        # Step 3: Synthesize response
        print("Synthesizing response to speech...")
        from mellona import MellonaClient, TTSRequest

        async def do_synthesis():
            async_client = MellonaClient()
            manager = async_client._manager
            tts_provider = manager.get_tts_provider("piper")
            request = TTSRequest(text=assistant_reply)
            response = await tts_provider.synthesize(request)
            return response.audio_data

        audio_bytes = asyncio.run(do_synthesis())

        # Save to file
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"Saved response to {output_file}")

# Run the pipeline
full_audio_pipeline("user_question.wav", "assistant_response.wav")
```

---

## See Also

- [Mellona Provider Reference](./mellona-provider-reference.md) — All providers and their configuration
- [Mellona Migration Notes](./mellona-migration-notes.md) — Chatterbox-specific integration details
