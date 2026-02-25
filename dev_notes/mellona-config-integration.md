# Mellona Config Integration for Chatterbox

## Overview

Chatterbox integrates with Mellona to provide a unified configuration system for:
- **STT (Speech-to-Text)**: Faster Whisper provider
- **TTS (Text-to-Speech)**: Piper provider
- **LLM (Large Language Model)**: Ollama provider

## Configuration File

The default configuration is located at `src/chatterbox/mellona.yaml` and defines:

### Providers
- `faster_whisper`: STT configuration with model and device settings
- `piper`: TTS configuration with voice and sample rate settings
- `ollama`: LLM configuration with base URL

### Profiles
- `stt_profiles.default`: STT profile using faster_whisper
- `tts_profiles.default`: TTS profile using piper
- `profiles.default`: LLM profile using ollama

## Environment Variables

The config file supports environment variable substitution using `${VAR_NAME}` syntax. All variables are substituted at startup:

### STT Configuration
- `CHATTERBOX_STT_MODEL`: Whisper model size (default: base)
- `CHATTERBOX_STT_DEVICE`: Computation device (default: cpu)
- `CHATTERBOX_STT_LANGUAGE`: Language code (default: auto-detect)

### TTS Configuration
- `CHATTERBOX_TTS_VOICE`: Piper voice model (default: en_US-lessac-medium)
- `CHATTERBOX_TTS_SAMPLE_RATE`: Audio sample rate (default: 22050)

### LLM Configuration
- `CHATTERBOX_OLLAMA_BASE_URL`: Ollama API endpoint (default: http://localhost:11434/v1)
- `CHATTERBOX_OLLAMA_MODEL`: Model name (default: llama3.1:8b)
- `CHATTERBOX_OLLAMA_TEMPERATURE`: Response temperature (default: 0.7)

## Settings Integration

The `Settings` class in `src/chatterbox/config/__init__.py` includes:

### New Setting
- `mellona_config_path`: Optional override for the config file location

### Method: `get_mellona_config_path()`
Returns the effective mellona config path:
1. Uses `mellona_config_path` if explicitly set via `CHATTERBOX_MELLONA_CONFIG_PATH`
2. Falls back to the default location: `src/chatterbox/mellona.yaml`

## Loading Strategy

### Single Config File (Current Implementation)
Chatterbox loads a single mellona config file directly:

```python
from mellona import MellonaConfig
from chatterbox.config import get_settings

settings = get_settings()
config_path = settings.get_mellona_config_path()
mellona_config = MellonaConfig(config_chain=[config_path])
```

### Future: Config Chain Strategy
If additional config sources are needed (user ~/.config/mellona, environment-specific configs), the `config_chain` parameter supports multiple files with first-found-wins semantics:

```python
config_chain = [
    settings.get_mellona_config_path(),  # Chatterbox defaults
    Path.home() / ".config" / "mellona" / "config.yaml",  # User overrides
]
mellona_config = MellonaConfig(config_chain=config_chain)
```

## Integration Points

### 1. STT Service (Placeholder)
```python
from mellona import get_config
stt_profile = get_config().get_stt_profile("default")
# Use stt_profile.provider and stt_profile.model
```

### 2. TTS Service (Placeholder)
```python
from mellona import get_config
tts_profile = get_config().get_tts_profile("default")
# Use tts_profile.provider and tts_profile.voice
```

### 3. LLM Agent (Placeholder)
```python
from mellona import get_config
llm_profile = get_config().get_profile("default")
# Use llm_profile.provider and llm_profile.model
```

## Backward Compatibility

The Settings class retains all original environment variables (`CHATTERBOX_STT_MODEL`, `CHATTERBOX_TTS_VOICE`, etc.) for backward compatibility. Existing code can continue using these settings directly.

Once services are migrated to use mellona profiles, individual settings can be deprecated in favor of profile-based configuration.

## Next Steps

1. **STT Integration** (issue: chatterbox-f1p)
   - Replace WhisperSTTService with mellona STT profile

2. **TTS Integration** (issue: chatterbox-tey)
   - Replace PiperTTSService with mellona TTS profile

3. **LLM Integration** (issue: chatterbox-44u)
   - Update VoiceAssistantAgent to use mellona Ollama profile

4. **Profile Customization**
   - Support per-app mellona.yaml in user home directory
   - Allow profile selection via CLI arguments or environment variables
