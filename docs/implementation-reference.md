# Implementation Reference

This document provides practical implementation patterns and reference implementations for Cackle.

## Key Patterns

### STT Service Implementation (Whisper)

```python
from cackle.services.stt import WhisperSTTService

stt = WhisperSTTService(model_size="base")
transcript = stt.transcribe("audio.wav")
```

### TTS Service Implementation (Piper)

```python
from cackle.services.tts import PiperTTSService

tts = PiperTTSService()
audio_path = tts.synthesize("Hello world", "output.wav")
```

### Agent with Tools

```python
from cackle.agent import VoiceAssistantAgent

agent = VoiceAssistantAgent()
response = agent.process("What time is it?")
```

### Tool Definition

Built-in tools are defined in `cackle/tools/builtin/` and registered in `cackle/tools/registry.py`.

```python
from langchain.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Description of the tool."""
    return "result"
```

## Testing Patterns

### Unit Test (pytest)

```python
def test_stt_transcription(mocker):
    mock_stt = mocker.patch("cackle.services.stt.WhisperSTTService.transcribe")
    mock_stt.return_value = "hello"
    
    # ... test logic
```

## See Also

- [Architecture](architecture.md) - System design
- [Workflows](workflows.md) - Development workflows
- [Definition of Done](definition-of-done.md) - Quality standards

---
Last Updated: 2026-02-01
