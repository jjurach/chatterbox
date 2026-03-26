# Chatterbox Settings Schema Reference

**Last Updated:** 2026-03-25
**Version:** 0.1.0

---

## Overview

This document describes the complete schema for `~/.config/chatterbox/settings.json`, the unified configuration file for all Chatterbox and Mellona settings.

The settings file uses JSON format with comprehensive comments and defaults. All fields are optional unless marked otherwise.

---

## File Location

```
~/.config/chatterbox/settings.json
```

Or on Windows:
```
%APPDATA%\chatterbox\settings.json
```

---

## Configuration Priority

Settings are loaded with this priority (highest to lowest):

1. **Environment Variables:** `CHATTERBOX_*` and `MELLONA_*`
2. **Settings JSON:** Values from `~/.config/chatterbox/settings.json`
3. **Defaults:** Built-in defaults

Example: If `CHATTERBOX_LLM_MODEL=mistral` is set, it overrides the JSON file.

---

## Full Schema with Examples

### Root-Level Sections

```json
{
  "server": { ... },
  "conversation": { ... },
  "api": { ... },
  "providers": { ... },
  "profiles": { ... },
  "stt_profiles": { ... },
  "tts_profiles": { ... },
  "memory": { ... },
  "logging": { ... }
}
```

---

## Section: `server`

**Purpose:** Wyoming protocol server configuration (handles audio I/O for STT/TTS, not conversation)

**Location:** `settings.json` → `server`

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `host` | string | `"0.0.0.0"` | No | Listen address for Wyoming server (0.0.0.0 = all interfaces) |
| `port` | integer | `10700` | No | Port number (1024-65535). Must be open in firewall. |
| `max_connections` | integer | `10` | No | Maximum concurrent Wyoming clients |
| `timeout` | integer | `30` | No | Connection timeout in seconds |

**Example:**

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 10700,
    "max_connections": 10,
    "timeout": 30
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_SERVER_HOST=192.168.0.100
CHATTERBOX_SERVER_PORT=9999
```

---

## Section: `conversation`

**Purpose:** FastAPI HTTP conversation server configuration (what Home Assistant connects to)

**Location:** `settings.json` → `conversation`

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `host` | string | `"0.0.0.0"` | No | Listen address (0.0.0.0 = all interfaces) |
| `port` | integer | `8765` | No | Port number. HA will connect to this port. |
| `timeout` | integer | `30` | No | Request timeout in seconds |
| `workers` | integer | `1` | No | Number of Uvicorn workers (1 for simple setups) |

**Example:**

```json
{
  "conversation": {
    "host": "0.0.0.0",
    "port": 8765,
    "timeout": 30,
    "workers": 1
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_CONVERSATION_HOST=0.0.0.0
CHATTERBOX_CONVERSATION_PORT=8765
```

**Important Notes:**

- This is the URL you configure in Home Assistant
- Home Assistant will connect to `http://{your-ip}:{port}`
- Default 8765 is arbitrary but fixed by convention

---

## Section: `api`

**Purpose:** API authentication and key management

**Location:** `settings.json` → `api`

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `key` | string or null | `null` | No | API key for Bearer token auth. Auto-generated if null. |
| `require_key` | boolean | `true` | No | If false, /health endpoint doesn't require authentication |
| `rate_limit` | integer | `100` | No | Max requests per minute per client |
| `rate_limit_enabled` | boolean | `false` | No | Enable rate limiting |

**Example:**

```json
{
  "api": {
    "key": "a1b2c3d4-e5f6-4789-abcd-ef0123456789",
    "require_key": true,
    "rate_limit": 100,
    "rate_limit_enabled": false
  }
}
```

**Auto-Generation:**

If `key` is null or missing, Chatterbox generates a new UUID4 on startup:

```
2026-03-25 14:23:45 - chatterbox - INFO - API key (auto-generated): a1b2c3d4-e5f6-4789-abcd-ef0123456789
```

**Persisting the Generated Key:**

The generated key is automatically saved back to `settings.json` for future restarts.

**Environment Variable Overrides:**

```bash
CHATTERBOX_API_KEY=your-custom-key-here
CHATTERBOX_REQUIRE_API_KEY=false
```

**Security Notes:**

- Treat the API key like a password
- Use a strong, random value (UUID is good)
- Share only with authorized Home Assistant instances
- Rotate periodically if exposed
- Never commit to version control (use env vars instead)

---

## Section: `providers`

**Purpose:** Configure LLM, STT, and TTS provider endpoints and parameters

**Location:** `settings.json` → `providers`

### Subsection: `providers.ollama`

**Purpose:** Ollama LLM provider (local LLM service)

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `base_url` | string | `"http://localhost:11434/v1"` | No | Ollama API endpoint |
| `timeout` | integer | `60` | No | Request timeout in seconds |
| `keep_alive` | string | `"5m"` | No | How long to keep model in VRAM |

**Example:**

```json
{
  "providers": {
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "timeout": 60,
      "keep_alive": "5m"
    }
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_OLLAMA_BASE_URL=http://192.168.0.100:11434/v1
CHATTERBOX_OLLAMA_TIMEOUT=120
```

**Common Configurations:**

```json
{
  "providers": {
    "ollama": {
      "base_url": "http://192.168.0.100:11434/v1"
    }
  }
}
```

---

### Subsection: `providers.openai`

**Purpose:** OpenAI or OpenAI-compatible LLM provider

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `api_key` | string | `null` | Yes (if using) | OpenAI API key or Bearer token |
| `base_url` | string | `"https://api.openai.com/v1"` | No | API endpoint (change for Azure, etc.) |
| `organization_id` | string | `null` | No | OpenAI organization ID |
| `timeout` | integer | `60` | No | Request timeout in seconds |

**Example:**

```json
{
  "providers": {
    "openai": {
      "api_key": "sk-proj-...",
      "base_url": "https://api.openai.com/v1",
      "timeout": 60
    }
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_OPENAI_API_KEY=sk-proj-your-key-here
CHATTERBOX_OPENAI_BASE_URL=https://api.openai.com/v1
```

**Security Notes:**

- Do NOT hardcode API key in settings.json
- Use environment variable instead: `CHATTERBOX_OPENAI_API_KEY=...`
- .gitignore prevents accidental commits, but env vars are safer

---

### Subsection: `providers.faster_whisper`

**Purpose:** Faster-Whisper STT (Speech-to-Text) provider

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `model` | string | `"base"` | No | Model size: tiny, base, small, medium, large |
| `device` | string | `"cpu"` | No | Device: cpu, cuda, auto |
| `language` | string or null | `null` | No | Language code (null = auto-detect) |
| `compute_type` | string | `"default"` | No | Precision: default, float16, int8 |
| `num_workers` | integer | `1` | No | Number of threads |

**Example:**

```json
{
  "providers": {
    "faster_whisper": {
      "model": "base",
      "device": "cpu",
      "language": null,
      "compute_type": "default",
      "num_workers": 1
    }
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_WHISPER_MODEL=small
CHATTERBOX_WHISPER_DEVICE=cuda
```

**Model Size Reference:**

| Size | Speed | Accuracy | VRAM | Disk |
|------|-------|----------|------|------|
| tiny | Fast | Good | 1GB | 140MB |
| base | Fast | Better | 1GB | 140MB |
| small | Medium | Better | 2GB | 466MB |
| medium | Slow | Best | 5GB | 1.5GB |
| large | Slowest | Best | 10GB | 2.9GB |

Recommendation: Use `base` for balance, `tiny` for low-resource systems.

---

### Subsection: `providers.piper`

**Purpose:** Piper TTS (Text-to-Speech) provider

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `voice` | string | `"en_US-lessac-medium"` | No | Voice identifier (see table below) |
| `sample_rate` | integer | `22050` | No | Audio sample rate (Hz) |
| `length_scale` | float | `1.0` | No | Speech speed (0.5=fast, 1.0=normal, 2.0=slow) |
| `noise_scale` | float | `0.667` | No | Variability (0.0=monotone, 1.0=natural) |

**Example:**

```json
{
  "providers": {
    "piper": {
      "voice": "en_US-lessac-medium",
      "sample_rate": 22050,
      "length_scale": 1.0,
      "noise_scale": 0.667
    }
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_PIPER_VOICE=en_US-hfc_female-medium
CHATTERBOX_PIPER_SAMPLE_RATE=22050
```

**Popular English Voices:**

| Voice | Speaker | Speed | Quality |
|-------|---------|-------|---------|
| `en_US-lessac-medium` | Male | Medium | Good |
| `en_US-hfc_female-medium` | Female | Medium | Good |
| `en_US-joe-medium` | Male | Medium | Good |
| `en_GB-alan-medium` | British Male | Medium | Good |

Full list: https://huggingface.co/rhasspy/piper-voices

---

### Subsection: `providers.mellona_config`

**Purpose:** Mellona service configuration (for Mellona compatibility)

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `config_file` | string | `null` | No | Legacy mellona.yaml path (deprecated) |

**Example:**

```json
{
  "providers": {
    "mellona_config": {
      "config_file": "~/.config/chatterbox/mellona.yaml"
    }
  }
}
```

**Note:** This section supports legacy mellona.yaml configuration. Prefer using the providers section above.

---

## Section: `profiles`

**Purpose:** Define conversation profiles (which LLM and settings to use)

**Location:** `settings.json` → `profiles`

**What is a Profile?**

A profile selects an LLM model and configures its behavior. You can have multiple profiles and choose which one to use.

**Fields (per profile):**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `provider` | string | `"ollama"` | No | Provider name: ollama, openai, etc. |
| `model` | string | (required) | Yes | Model identifier (depends on provider) |
| `temperature` | float | `0.7` | No | Creativity (0.0=deterministic, 1.0=creative, 2.0=wild) |
| `max_tokens` | integer | `4096` | No | Max response length |
| `top_p` | float | `0.95` | No | Nucleus sampling (0.0-1.0) |

**Example - Multiple Profiles:**

```json
{
  "profiles": {
    "default": {
      "provider": "ollama",
      "model": "llama3.1:8b",
      "temperature": 0.7,
      "max_tokens": 4096,
      "top_p": 0.95
    },
    "fast": {
      "provider": "ollama",
      "model": "mistral",
      "temperature": 0.5,
      "max_tokens": 2048
    },
    "creative": {
      "provider": "ollama",
      "model": "llama3.1:8b",
      "temperature": 1.2,
      "max_tokens": 4096
    },
    "openai": {
      "provider": "openai",
      "model": "gpt-4-turbo-preview",
      "temperature": 0.8,
      "max_tokens": 8192
    }
  }
}
```

**Switching Profiles:**

Via environment variable:
```bash
CHATTERBOX_PROFILE=fast
```

Or programmatically by restarting with the profile name.

**Ollama Models:**

Common models and their characteristics:

| Model | Size | Speed | Quality | VRAM |
|-------|------|-------|---------|------|
| mistral | 7B | Very Fast | Good | 4GB |
| neural-chat | 7B | Fast | Good | 4GB |
| llama2 | 7B | Medium | Good | 4GB |
| llama3.1:8b | 8B | Medium | Better | 5GB |
| mistral-large | Large | Slow | Best | 20GB |

**OpenAI Models:**

| Model | Cost | Quality | Speed |
|-------|------|---------|-------|
| gpt-4o | High | Best | Medium |
| gpt-4-turbo | High | Best | Slow |
| gpt-3.5-turbo | Low | Good | Fast |

---

## Section: `stt_profiles`

**Purpose:** Define Speech-to-Text profiles

**Location:** `settings.json` → `stt_profiles`

**Fields (per profile):**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `provider` | string | `"faster_whisper"` | No | Provider name |
| `language` | string | `null` | No | Force language (null = auto-detect) |

**Example:**

```json
{
  "stt_profiles": {
    "default": {
      "provider": "faster_whisper",
      "language": null
    },
    "spanish": {
      "provider": "faster_whisper",
      "language": "es"
    },
    "french": {
      "provider": "faster_whisper",
      "language": "fr"
    }
  }
}
```

**Environment Variable Overrides:**

```bash
CHATTERBOX_STT_PROFILE=spanish
```

---

## Section: `tts_profiles`

**Purpose:** Define Text-to-Speech profiles

**Location:** `settings.json` → `tts_profiles`

**Fields (per profile):**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `provider` | string | `"piper"` | No | Provider name |
| `voice` | string | `"en_US-lessac-medium"` | No | Voice identifier |
| `sample_rate` | integer | `22050` | No | Audio sample rate |

**Example:**

```json
{
  "tts_profiles": {
    "default": {
      "provider": "piper",
      "voice": "en_US-lessac-medium",
      "sample_rate": 22050
    },
    "female": {
      "provider": "piper",
      "voice": "en_US-hfc_female-medium",
      "sample_rate": 22050
    },
    "british": {
      "provider": "piper",
      "voice": "en_GB-alan-medium",
      "sample_rate": 22050
    }
  }
}
```

---

## Section: `memory`

**Purpose:** Conversation context and memory management

**Location:** `settings.json` → `memory`

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `conversation_window_size` | integer | `3` | No | Number of past exchanges to remember |
| `max_conversation_length` | integer | `100` | No | Max total turns per conversation |
| `persistence_enabled` | boolean | `true` | No | Enable persistent storage (Epic 5) |
| `persistence_type` | string | `"sqlite"` | No | Backend: sqlite, redis, memory |
| `persistence_path` | string | `"~/.config/chatterbox/conversations.db"` | No | Database file path |
| `context_search_enabled` | boolean | `true` | No | Enable semantic search across history |

**Example:**

```json
{
  "memory": {
    "conversation_window_size": 3,
    "max_conversation_length": 100,
    "persistence_enabled": true,
    "persistence_type": "sqlite",
    "persistence_path": "~/.config/chatterbox/conversations.db",
    "context_search_enabled": true
  }
}
```

**Tuning Guidelines:**

- **conversation_window_size:** Higher = more context but more tokens (costs money)
  - Default 3 is good for balanced behavior
  - Use 1 for fast/cheap responses
  - Use 5-10 for multi-turn scenarios

- **persistence_type:**
  - `sqlite`: Recommended for single-machine deployments
  - `redis`: Recommended for multi-instance setups
  - `memory`: Development only (data lost on restart)

**Environment Variable Overrides:**

```bash
CHATTERBOX_CONVERSATION_WINDOW_SIZE=5
CHATTERBOX_PERSISTENCE_TYPE=redis
```

---

## Section: `logging`

**Purpose:** Control logging verbosity and output

**Location:** `settings.json` → `logging`

**Fields:**

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `level` | string | `"INFO"` | No | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `format` | string | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | No | Log message format |
| `file` | string | `null` | No | Log to file (path) in addition to console |
| `max_file_size` | integer | `10485760` | No | Max log file size (10MB default) |
| `backup_count` | integer | `5` | No | Keep N rotated log files |

**Example:**

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "~/.config/chatterbox/chatterbox.log",
    "max_file_size": 10485760,
    "backup_count": 5
  }
}
```

**Log Levels:**

| Level | Verbosity | Use Case |
|-------|-----------|----------|
| CRITICAL | Minimal | Catastrophic failures only |
| ERROR | Low | Errors only |
| WARNING | Low-Medium | Errors + warnings |
| INFO | Medium | Normal operation (default) |
| DEBUG | High | Development and troubleshooting |

**Environment Variable Overrides:**

```bash
CHATTERBOX_LOG_LEVEL=DEBUG
```

**Log Output Example:**

```
2026-03-25 14:23:45,123 - chatterbox.server - INFO - Conversation server listening on http://0.0.0.0:8765
2026-03-25 14:23:45,456 - chatterbox.config - INFO - API key (auto-generated): a1b2c3d4-e5f6-4789-abcd-ef0123456789
2026-03-25 14:23:46,789 - chatterbox.conversation - DEBUG - Received request: text="What time is it?" conversation_id="abc123"
```

---

## Complete Example Configuration

Here's a fully commented `~/.config/chatterbox/settings.json` with recommended defaults:

```json
{
  "_comment": "Chatterbox Configuration - ~/.config/chatterbox/settings.json",
  "_version": "0.1.0",
  "_last_updated": "2026-03-25",

  "server": {
    "_comment": "Wyoming protocol server (STT/TTS for voice I/O)",
    "host": "0.0.0.0",
    "port": 10700,
    "max_connections": 10,
    "timeout": 30
  },

  "conversation": {
    "_comment": "FastAPI HTTP server (Home Assistant connects here)",
    "host": "0.0.0.0",
    "port": 8765,
    "timeout": 30,
    "workers": 1
  },

  "api": {
    "_comment": "API authentication",
    "key": null,
    "_key_comment": "Auto-generated on first run if null. Use env var CHATTERBOX_API_KEY to override.",
    "require_key": true,
    "rate_limit": 100,
    "rate_limit_enabled": false
  },

  "providers": {
    "_comment": "External service endpoints (LLM, STT, TTS)",

    "ollama": {
      "_comment": "Ollama LLM endpoint",
      "base_url": "http://localhost:11434/v1",
      "timeout": 60,
      "keep_alive": "5m"
    },

    "openai": {
      "_comment": "OpenAI API (optional, use env var for key)",
      "api_key": null,
      "base_url": "https://api.openai.com/v1",
      "timeout": 60
    },

    "faster_whisper": {
      "_comment": "Faster-Whisper STT provider",
      "model": "base",
      "device": "cpu",
      "language": null,
      "compute_type": "default",
      "num_workers": 1
    },

    "piper": {
      "_comment": "Piper TTS provider",
      "voice": "en_US-lessac-medium",
      "sample_rate": 22050,
      "length_scale": 1.0,
      "noise_scale": 0.667
    }
  },

  "profiles": {
    "_comment": "LLM conversation profiles",

    "default": {
      "_comment": "Default: balanced speed and quality",
      "provider": "ollama",
      "model": "llama3.1:8b",
      "temperature": 0.7,
      "max_tokens": 4096,
      "top_p": 0.95
    },

    "fast": {
      "_comment": "Fast and lightweight",
      "provider": "ollama",
      "model": "mistral",
      "temperature": 0.5,
      "max_tokens": 2048
    },

    "creative": {
      "_comment": "More creative responses",
      "provider": "ollama",
      "model": "llama3.1:8b",
      "temperature": 1.2,
      "max_tokens": 4096
    }
  },

  "stt_profiles": {
    "_comment": "Speech-to-Text profiles",

    "default": {
      "provider": "faster_whisper",
      "language": null
    }
  },

  "tts_profiles": {
    "_comment": "Text-to-Speech profiles",

    "default": {
      "provider": "piper",
      "voice": "en_US-lessac-medium",
      "sample_rate": 22050
    }
  },

  "memory": {
    "_comment": "Conversation context and persistence",
    "conversation_window_size": 3,
    "max_conversation_length": 100,
    "persistence_enabled": true,
    "persistence_type": "sqlite",
    "persistence_path": "~/.config/chatterbox/conversations.db",
    "context_search_enabled": true
  },

  "logging": {
    "_comment": "Logging configuration",
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": null,
    "max_file_size": 10485760,
    "backup_count": 5
  }
}
```

---

## Environment Variable Reference

All settings can be overridden with environment variables. Format: `CHATTERBOX_<SECTION>_<FIELD>` (uppercase, underscores).

### Common Overrides

| Setting | Env Var | Example |
|---------|---------|---------|
| API Key | `CHATTERBOX_API_KEY` | `CHATTERBOX_API_KEY=uuid-here` |
| LLM Model | `CHATTERBOX_LLM_MODEL` | `CHATTERBOX_LLM_MODEL=mistral` |
| LLM Temp | `CHATTERBOX_LLM_TEMPERATURE` | `CHATTERBOX_LLM_TEMPERATURE=0.5` |
| Ollama URL | `CHATTERBOX_OLLAMA_BASE_URL` | `CHATTERBOX_OLLAMA_BASE_URL=http://192.168.0.100:11434/v1` |
| Log Level | `CHATTERBOX_LOG_LEVEL` | `CHATTERBOX_LOG_LEVEL=DEBUG` |
| Conv. Port | `CHATTERBOX_CONVERSATION_PORT` | `CHATTERBOX_CONVERSATION_PORT=8765` |
| Server Port | `CHATTERBOX_SERVER_PORT` | `CHATTERBOX_SERVER_PORT=10700` |

### Starting with Env Vars

```bash
export CHATTERBOX_LLM_MODEL=mistral
export CHATTERBOX_LOG_LEVEL=DEBUG
export CHATTERBOX_OLLAMA_BASE_URL=http://192.168.0.100:11434/v1

python -m src.chatterbox.conversation.server
```

---

## Troubleshooting Configuration Issues

### "Could not load settings.json"

**Cause:** File doesn't exist or is invalid JSON.

**Solution:**
```bash
# Check file exists
cat ~/.config/chatterbox/settings.json

# Validate JSON
python3 -m json.tool ~/.config/chatterbox/settings.json

# Create default if missing
mkdir -p ~/.config/chatterbox
# Copy the example from above
```

---

### Settings Not Taking Effect

**Cause:** Environment variable or priority issue.

**Solution:**

1. Check which config is actually loaded:
   ```bash
   # Add to logging section
   "level": "DEBUG"

   # Restart and look for messages like:
   # "Loading configuration from: ~/.config/chatterbox/settings.json"
   ```

2. Priority check (highest wins):
   - Environment variables (set these first)
   - `~/.config/chatterbox/settings.json`
   - Built-in defaults

---

### "Invalid profile: fast"

**Cause:** Referenced profile doesn't exist in `profiles` section.

**Solution:**
```bash
# Check profiles section exists
cat ~/.config/chatterbox/settings.json | grep -A 50 '"profiles"'

# Verify profile name matches exactly
CHATTERBOX_PROFILE=default  # Use an existing one
```

---

## Migration from mellona.yaml

If you have an existing `~/.config/chatterbox/mellona.yaml`, you can migrate to the unified settings:

1. Keep the old file for now (preserved for compatibility)
2. Create the new `settings.json` with desired settings
3. Chatterbox will prefer `settings.json` over `mellona.yaml`
4. Once tested, you can delete `mellona.yaml`

---

## Best Practices

1. **Never hardcode API keys** — Use `CHATTERBOX_API_KEY` env var
2. **Use profiles for different scenarios** — fast, creative, production, etc.
3. **Set log level to DEBUG during setup** — Easier troubleshooting
4. **Start simple** — Use defaults, add customizations as needed
5. **Backup settings.json** — Before major changes
6. **Test after editing** — Restart and check logs
7. **Document custom profiles** — Add comments explaining each profile

---

## See Also

- [Home Assistant Integration Guide](ha-integration-guide.md)
- [HACS Setup Guide](hacs-setup.md)
- [LLM Providers Reference](llm-providers.md)
- [Environment Variables](env-vars.md)

---

**Last Updated:** 2026-03-25
**Version:** 0.1.0
