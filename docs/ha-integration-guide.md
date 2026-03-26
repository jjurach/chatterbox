# Chatterbox Home Assistant Integration Guide

**Last Updated:** 2026-03-25
**Minimum Home Assistant Version:** 2025.x
**Integration Version:** 0.1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
   - [HACS Installation (Recommended)](#hacs-installation-recommended)
   - [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
   - [Chatterbox Server Setup](#chatterbox-server-setup)
   - [Home Assistant Configuration Flow](#home-assistant-configuration-flow)
   - [Voice Pipeline Setup](#voice-pipeline-setup)
6. [Usage](#usage)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)
9. [FAQ](#faq)
10. [Support](#support)

---

## Overview

Chatterbox is a custom Home Assistant integration that brings intelligent voice conversations to your smart home. It acts as a bridge between Home Assistant's voice assistant pipeline and a local or remote Chatterbox server running advanced LLM capabilities with tool calling.

### What You Get

- **Intelligent Conversations:** Powered by Ollama, OpenAI, or other compatible LLMs
- **Voice Commands:** "What's the weather?" "What time is it?" and more
- **Context Awareness:** Maintains conversation history for multi-turn interactions
- **Local Processing:** Run the LLM on your own hardware, no cloud dependency
- **Tool Calling:** Extensible system for adding custom skills and integrations

### When to Use Chatterbox

- You want a more intelligent conversation agent than Home Assistant's built-in intent matching
- You prefer local LLM processing over cloud services
- You need advanced conversation features like context management
- You want to extend voice commands with custom tools

---

## Architecture

Chatterbox integrates into Home Assistant's voice assistant pipeline like this:

```
ESP32-S3-BOX-3B (or any device with mic/speaker)
    ↓ audio
Home Assistant Voice Pipeline (192.168.0.167)
    ├─ Wake Word Detection (Wyoming)
    ├─ Speech-to-Text (STT) - Wyoming
    └─ Conversation Agent (THIS INTEGRATION) ← Chatterbox
         ↓ POST /conversation (Bearer token auth)
    Chatterbox FastAPI Server (192.168.0.100:8765)
         ├─ LLM (Ollama, OpenAI, local model)
         ├─ Tool Registry (weather, time, device control)
         └─ Context Persistence
         ↑ response text
    Home Assistant Voice Pipeline (continued)
         └─ Text-to-Speech (TTS) - Piper
    ↓ audio
ESP32-S3-BOX-3B speaker
```

**Key Points:**

- Wyoming handles only **audio I/O** (wake word, STT, TTS)
- Chatterbox handles **conversation logic** (LLM, tools, context)
- HA integration proxies requests over HTTP with Bearer token authentication
- All communication is local network (no cloud required)

---

## Prerequisites

Before installing Chatterbox, ensure you have:

### Hardware
- **Home Assistant Server:** Any machine running HA 2025.x or later
  - Raspberry Pi 4+ recommended for HA itself
  - Can be same machine as Chatterbox server or different

- **Chatterbox Server:** Machine to run the backend service
  - Ubuntu/Debian Linux (tested on Ubuntu 20.04+)
  - Or any system with Python 3.10+
  - Can be same machine as HA or separate (local network)

- **Voice Device:** ESP32-S3-BOX-3B or HA compatible satellite
  - Microphone and speaker
  - On same WiFi network as HA and Chatterbox

### Software
- **Home Assistant:** Version 2025.x or later installed and accessible
- **Python:** 3.10 or higher (if running Chatterbox server yourself)
- **Ollama or Alternative LLM:** Running on your network or cloud (optional)
  - Default uses Ollama at `http://localhost:11434`

### Network
- **Local Network Access:** All machines on same LAN or routable network
- **DNS/Zeroconf:** mDNS enabled for automatic discovery (`.local` domains)
  - Or static IP for manual configuration

### API Key
- Chatterbox server auto-generates an API key on first run
- This key is shared with HA for authentication
- Should be a strong random value (UUID format)

---

## Installation

### HACS Installation (Recommended)

HACS (Home Assistant Community Store) is the easiest way to install and manage the Chatterbox integration.

#### Step 1: Enable HACS (if not already enabled)

1. Go to **Settings** → **Devices & Services** → **Automation, Scripts & Scenes**
2. Look for HACS in the integrations list
3. If not present, [install HACS](https://hacs.xyz/docs/setup/download) following the official guide

#### Step 2: Add Chatterbox as Custom Repository

1. In Home Assistant, go to **HACS** → **Integrations**
2. Click the three-dot menu (⋮) in the top right
3. Select **Custom repositories**
4. Add this repository:
   ```
   Repository URL: https://github.com/phaedrus/hentown
   Category: Integration
   ```
5. Click **Create**

#### Step 3: Install Chatterbox

1. Go to **HACS** → **Integrations**
2. Search for **Chatterbox**
3. Click the result
4. Click **Install**
5. Click **Install** in the dialog box
6. **Restart Home Assistant** (Settings → System → Restart)

#### Step 4: Add to Home Assistant

After restart:

1. Go to **Settings** → **Devices & Services**
2. Click **Create Integration** (bottom right)
3. Search for **Chatterbox**
4. Follow the configuration flow (see [Home Assistant Configuration Flow](#home-assistant-configuration-flow))

---

### Manual Installation

If you prefer not to use HACS:

#### Step 1: Clone or Download the Repository

```bash
# Option A: Clone the full repository (includes other components)
git clone https://github.com/phaedrus/hentown
cd hentown/modules/chatterbox

# Option B: Download just the integration
# Download custom_components/chatterbox/ directory
```

#### Step 2: Copy to Home Assistant Config Directory

```bash
# Find your HA config directory (usually /root/.homeassistant or ~/config)
# Copy the chatterbox integration to HA's custom_components directory

cp -r custom_components/chatterbox ~/.homeassistant/custom_components/
# or
cp -r custom_components/chatterbox ~/config/custom_components/
```

#### Step 3: Restart Home Assistant

In Home Assistant:
1. Go to **Settings** → **System** → **Restart**
2. Wait for restart to complete

#### Step 4: Add to Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **Create Integration** (bottom right)
3. Search for **Chatterbox**
4. Follow the configuration flow

---

## Configuration

### Chatterbox Server Setup

Before configuring Home Assistant, ensure the Chatterbox server is running.

#### Step 1: Install and Start Chatterbox Server

On your Chatterbox server machine (Linux/Ubuntu):

```bash
# Clone the repository
git clone https://github.com/phaedrus/hentown
cd hentown/modules/chatterbox

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .
```

#### Step 2: Ensure Ollama is Running (or Configure Alternative LLM)

The Chatterbox server needs an LLM provider. Default is Ollama:

```bash
# Install Ollama from https://ollama.ai or your package manager
ollama serve
```

In another terminal:
```bash
# Download the model (first time only)
ollama pull llama3.1:8b

# Or use another model:
ollama pull mistral  # Faster, smaller
ollama pull neural-chat  # Optimized for conversations
```

**Alternative LLMs:**
- **OpenAI:** Set `CHATTERBOX_OPENAI_API_KEY` and `CHATTERBOX_LLM_PROVIDER=openai`
- **Local Models:** Configure Ollama with different models
- **Remote Services:** Point to any OpenAI-compatible endpoint

#### Step 3: Start the Chatterbox Conversation Server

```bash
# Start the main chatterbox server (handles Wyoming protocol)
# Usually not needed for HA integration, but can be useful for testing
chatterbox-server

# In another terminal, start the Chatterbox FastAPI conversation server
# This is what HA will connect to
python -m src.chatterbox.conversation.server
# or
chatterbox-conversation-server  # if entry point is defined
```

The server should start on `http://0.0.0.0:8765` (default port).

#### Step 4: Locate Your API Key and Server URL

Check the Chatterbox server logs for the auto-generated API key:

```
2026-03-25 14:23:45 - chatterbox - INFO - API key (auto-generated): a1b2c3d4-e5f6-4789-abcd-ef0123456789
2026-03-25 14:23:45 - chatterbox - INFO - Conversation server listening on http://0.0.0.0:8765
```

**Note the following:**
- **API Key:** `a1b2c3d4-e5f6-4789-abcd-ef0123456789` (your value will differ)
- **Server URL:** Determine your actual IP address:
  ```bash
  hostname -I
  # Output: 192.168.0.100 (use this)
  ```
  So your URL is `http://192.168.0.100:8765`

#### Step 5: Configure Environment Variables (Optional)

Create a `.env` file in the Chatterbox directory for custom settings:

```bash
# .env file in /home/user/hentown/modules/chatterbox/

# Server Configuration
CHATTERBOX_SERVER_HOST=0.0.0.0
CHATTERBOX_SERVER_PORT=10700

# Conversation API Server (this is what HA connects to)
CHATTERBOX_CONVERSATION_HOST=0.0.0.0
CHATTERBOX_CONVERSATION_PORT=8765

# API Key (leave unset to auto-generate)
# CHATTERBOX_API_KEY=your-key-here

# LLM Provider
CHATTERBOX_LLM_PROVIDER=ollama
CHATTERBOX_OLLAMA_BASE_URL=http://localhost:11434/v1
CHATTERBOX_LLM_MODEL=llama3.1:8b
CHATTERBOX_LLM_TEMPERATURE=0.7

# Logging
CHATTERBOX_LOG_LEVEL=INFO
```

Then start the server:
```bash
source .env
chatterbox-conversation-server
```

---

### Home Assistant Configuration Flow

Once the Chatterbox server is running, configure Home Assistant.

#### Step 1: Create the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Create Integration** (bottom right button)
3. Search for and select **Chatterbox**

#### Step 2: Choose Configuration Method

You'll be presented with two options:

**Option A: Zeroconf Discovery (Automatic)**

If your network supports mDNS (most do), the integration will auto-discover Chatterbox:

1. A list of discovered Chatterbox servers appears
2. Select your server from the list
3. Click **Submit**
4. Proceed to Step 3 below

**Option B: Manual URL Entry**

If auto-discovery doesn't work:

1. Select **Manual Entry**
2. Enter the server URL: `http://192.168.0.100:8765` (use your IP)
3. Click **Submit**
4. Proceed to Step 3 below

#### Step 3: Enter API Key

The next screen asks for:

- **API Key** (optional): Paste the auto-generated key from Chatterbox logs
  - Leave blank if you want HA to test connection first
  - You can update this later if needed

- **Agent Name** (optional): Display name for this agent
  - Default: "Chatterbox"
  - Can be anything (e.g., "Living Room AI", "Bedroom Assistant")

Example:
```
API Key: a1b2c3d4-e5f6-4789-abcd-ef0123456789
Agent Name: Kitchen Assistant
```

#### Step 4: Connection Test

The integration tests the connection:
- Sends a request to `/health` endpoint
- If successful, saves the configuration
- If failed, shows error message with suggestions

**Common errors:**
- "Cannot connect" → Check Chatterbox is running and URL is correct
- "Invalid API key" → Check the key is correct if provided
- "Timeout" → Check network connectivity and firewall

#### Step 5: Confirmation

After successful connection:

```
Configuration saved!
Chatterbox integration is ready.
Agent: Kitchen Assistant
Server: http://192.168.0.100:8765
```

---

### Voice Pipeline Setup

After the integration is added, configure it in the voice pipeline.

#### Step 1: Go to Voice Assistants Settings

1. Go to **Settings** → **Voice Assistants** (or **Settings** → **Voice & Assist**)
2. Click on the Assist pipeline you want to use (usually "Default")

#### Step 2: Configure Conversation Agent

In the pipeline settings, find **Conversation Agent** and:

1. **Agent:** Select your Chatterbox agent from the dropdown
   - Should show "Kitchen Assistant" (or whatever name you chose)
2. **Fallback:** Leave at default unless you have a specific preference

Example configuration:
```
Conversation Agent: Kitchen Assistant ✓
Fallback conversation: (Built-in - matching intents)
```

#### Step 3: Configure STT (Speech-to-Text)

Configure how speech is converted to text:

1. **STT Engine:** Choose one of:
   - **Whisper (Remote)** - Runs on Chatterbox server (recommended if Chatterbox has it)
   - **Whisper (Local)** - Runs on HA server (if you have HA hardware with good CPU)
   - **Other services** - Google Cloud Speech, OpenAI, etc.

Example:
```
Speech-to-text: Whisper (Remote)
Provider: Local (runs on Chatterbox server)
```

#### Step 4: Configure Wake Word (Optional)

If using a wake word:

1. **Wake Word:** Select a wake word detector
   - Options: "Alexa", "Mycroft", "Okay Nabu", etc.
   - Usually provided by Wyoming service

Example:
```
Wake word: Okay Nabu
Sensitivity: Normal
```

#### Step 5: Configure TTS (Text-to-Speech)

Configure voice output:

1. **TTS Engine:** Choose one of:
   - **Piper (Local)** - Recommended, runs on HA server
   - **Google Cloud Text-to-Speech** - Cloud service
   - **Amazon Polly** - Cloud service
   - **Other services**

Example:
```
Text-to-speech: Piper
Voice: en_US-lessac-medium (or your preference)
```

#### Step 6: Test the Pipeline

Once configured:

1. Click **Test** on the voice pipeline settings
2. Speak into your device (or type a text command)
3. You should hear Chatterbox respond

If you see errors, check the [Troubleshooting](#troubleshooting) section.

---

## Usage

### Basic Voice Commands

Once configured, you can use voice commands like:

- **Time and Date**
  - "What time is it?"
  - "What's today's date?"

- **Weather** (if weather tools are configured)
  - "What's the weather?"
  - "What's the temperature outside?"

- **General Conversation**
  - "How does photosynthesis work?"
  - "Tell me a joke"
  - "What's the capital of France?"

- **Custom Tools** (if configured by your setup)
  - Any custom tools added to your Chatterbox configuration

### Multi-turn Conversations

Chatterbox maintains conversation history, so you can have multi-turn dialogues:

```
User: "What's the weather?"
Chatterbox: "It's currently 72°F and sunny."

User: "How's the humidity?"
Chatterbox: "The humidity is 55%, making it quite comfortable."
```

The context is automatically managed by the Chatterbox server.

### Checking Conversation History

Conversation history is stored on the Chatterbox server. Refer to the Chatterbox documentation for:
- Viewing conversation logs
- Exporting conversation history
- Searching past interactions

---

## Troubleshooting

### "Server Not Discovered" (Zeroconf)

**Symptom:** Auto-discovery doesn't find the Chatterbox server.

**Possible Causes:**
1. mDNS/Zeroconf not enabled on the network
2. Firewall blocking mDNS (port 5353)
3. Chatterbox not advertising correctly

**Solutions:**

1. **Check Zeroconf is Enabled:**
   - On Linux, ensure Avahi is running: `sudo systemctl status avahi-daemon`
   - On macOS, should work out of the box
   - On Windows, might need additional setup

2. **Use Manual Entry Instead:**
   - During setup, select "Manual Entry"
   - Enter the full URL: `http://192.168.0.100:8765`

3. **Check Chatterbox is Running:**
   ```bash
   curl http://192.168.0.100:8765/health
   # Should return: {"status": "ok"}
   ```

---

### "Connection Refused"

**Symptom:** Configuration flow says "Cannot connect" immediately.

**Possible Causes:**
1. Chatterbox server isn't running
2. Wrong IP address or port
3. Firewall blocking the port

**Solutions:**

1. **Verify Chatterbox is Running:**
   ```bash
   ps aux | grep chatterbox
   # Should show running process
   ```

2. **Check the URL:**
   - Get your IP: `hostname -I`
   - Test from HA machine: `curl http://192.168.0.100:8765/health`
   - URL should match exactly

3. **Check Firewall:**
   ```bash
   # On Chatterbox server machine
   sudo ufw allow 8765  # if using UFW
   # or adjust your firewall rules
   ```

4. **Check Port is Actually Running:**
   ```bash
   sudo netstat -tlnp | grep 8765
   # Should show: LISTEN ... 8765
   ```

---

### "Offline" Error During Voice Command

**Symptom:** HA voice response says "Chatterbox is temporarily offline, please try again."

**Possible Causes:**
1. Chatterbox server crashed or restarted
2. Network connectivity issue
3. API key mismatch

**Solutions:**

1. **Check Chatterbox Logs:**
   ```bash
   # In the terminal running Chatterbox
   # Look for error messages
   # Should see: "API key: ..." on startup
   ```

2. **Restart Chatterbox:**
   ```bash
   # Stop current process
   Ctrl+C

   # Ensure Ollama is running
   ollama serve  # in another terminal

   # Restart Chatterbox
   python -m src.chatterbox.conversation.server
   ```

3. **Verify API Key:**
   - Check the key in HA settings matches the one in Chatterbox logs
   - If it doesn't, update via Settings → Devices & Services → Chatterbox → Configure

4. **Check Network Connectivity:**
   ```bash
   # From HA machine to Chatterbox
   ping 192.168.0.100
   # Should respond
   ```

---

### "Invalid API Key" Error

**Symptom:** Configuration says "Authentication failed" after entering API key.

**Possible Causes:**
1. API key is incorrect or mistyped
2. API key changed (Chatterbox restarted and generated new key)
3. API key feature not enabled in Chatterbox

**Solutions:**

1. **Get Correct Key from Chatterbox Logs:**
   ```bash
   # In Chatterbox terminal, look for:
   # "API key (auto-generated): a1b2c3d4-e5f6-4789-abcd-ef0123456789"
   ```

2. **Update Key in HA:**
   - Settings → Devices & Services
   - Find Chatterbox integration
   - Click the three dots → Options
   - Update the API Key field

3. **Disable API Key Requirement (Testing Only):**
   - In Chatterbox `.env`, set: `CHATTERBOX_REQUIRE_API_KEY=false`
   - Leave the API Key field blank in HA
   - **Note:** Not recommended for production

---

### No Response from Voice Command

**Symptom:** Ask a question, but Chatterbox doesn't respond (no audio, no error).

**Possible Causes:**
1. LLM provider (Ollama) not running
2. LLM model not loaded
3. Network latency / request timeout
4. Chatterbox conversation server not in voice pipeline

**Solutions:**

1. **Check LLM is Running:**
   ```bash
   curl http://localhost:11434/api/tags
   # Should return list of models
   ```

2. **Load the Model Explicitly:**
   ```bash
   ollama run llama3.1:8b
   # Keep this running while using Chatterbox
   ```

3. **Verify Conversation Agent is Selected:**
   - Settings → Voice Assistants → Default
   - Under "Conversation Agent", should show your Chatterbox agent
   - If it says "Built-in", click the dropdown and select Chatterbox

4. **Check HA Logs:**
   - Settings → System → Logs
   - Look for Chatterbox-related messages
   - Share the full error in [GitHub Issues](https://github.com/phaedrus/hentown/issues)

---

### Slow Responses

**Symptom:** Chatterbox takes 10+ seconds to respond.

**Possible Causes:**
1. LLM model is large or not optimized
2. Network latency between HA and Chatterbox
3. Server CPU/memory under stress

**Solutions:**

1. **Use Smaller, Faster Model:**
   ```bash
   # Download a faster model
   ollama pull mistral  # Faster than llama3.1:8b

   # Update .env or settings.json
   CHATTERBOX_LLM_MODEL=mistral

   # Restart Chatterbox
   ```

2. **Profile the Response:**
   - Check Chatterbox logs for timing
   - Is delay in LLM (seconds) or network (milliseconds)?
   - LLM delay → use smaller model
   - Network delay → move Chatterbox closer or optimize network

3. **Check System Resources:**
   ```bash
   top  # Check CPU and memory usage
   # If high, try smaller model or dedicated hardware
   ```

4. **Optimize Model:**
   - Use quantized versions (Q4 instead of full precision)
   - Ollama uses quantized models by default

---

### Connection Test Works, But Voice Commands Fail

**Symptom:** Settings → Devices & Services shows "Connected", but voice commands don't work.

**Possible Causes:**
1. Voice pipeline not configured to use Chatterbox agent
2. Conversation server endpoint different from health endpoint
3. Bearer token not being sent correctly

**Solutions:**

1. **Verify Voice Pipeline Configuration:**
   - Go to Settings → Voice Assistants
   - Select your pipeline
   - Under "Conversation Agent", is Chatterbox selected?
   - Should NOT be "Built-in" or another agent

2. **Check HA System Logs:**
   - Settings → System → Logs
   - Search for "Chatterbox" or "conversation"
   - Look for connection errors or auth failures

3. **Manual Test:**
   ```bash
   # From HA machine, test the API directly
   API_KEY="your-key-here"

   curl -X POST http://192.168.0.100:8765/conversation \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello", "conversation_id": "test", "language": "en"}'

   # Should return: {"response_text": "...", "conversation_id": "test"}
   ```

---

## Advanced Configuration

### Settings.json Schema

The Chatterbox server configuration is stored in `~/.config/chatterbox/settings.json`. You can customize behavior here.

**Full schema:**

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 10700,
    "description": "Wyoming protocol server (STT/TTS, not conversation)"
  },
  "conversation": {
    "host": "0.0.0.0",
    "port": 8765,
    "description": "FastAPI conversation server (what HA connects to)"
  },
  "api": {
    "key": null,
    "comment": "API key for Bearer token auth. Leave null to auto-generate on startup"
  },
  "providers": {
    "faster_whisper": {
      "model": "base",
      "device": "cpu",
      "language": null,
      "comment": "STT (Speech-to-Text) provider"
    },
    "piper": {
      "voice": "en_US-lessac-medium",
      "sample_rate": 22050,
      "comment": "TTS (Text-to-Speech) provider"
    },
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "comment": "LLM provider endpoint"
    },
    "openai": {
      "api_key": null,
      "base_url": "https://api.openai.com/v1",
      "comment": "Alternative: use OpenAI instead of Ollama"
    }
  },
  "profiles": {
    "default": {
      "provider": "ollama",
      "model": "llama3.1:8b",
      "temperature": 0.7,
      "comment": "LLM profile: what model to use and how creative"
    },
    "fast": {
      "provider": "ollama",
      "model": "mistral",
      "temperature": 0.5,
      "comment": "Faster but less capable"
    }
  },
  "stt_profiles": {
    "default": {
      "provider": "faster_whisper",
      "comment": "Speech-to-Text profile"
    }
  },
  "tts_profiles": {
    "default": {
      "provider": "piper",
      "comment": "Text-to-Speech profile"
    }
  },
  "memory": {
    "conversation_window_size": 3,
    "comment": "Number of past exchanges to remember (higher = more context, more tokens)"
  },
  "logging": {
    "level": "INFO",
    "comment": "Logging level: DEBUG, INFO, WARNING, ERROR"
  }
}
```

**Common Customizations:**

1. **Use a Faster Model:**
   ```json
   "profiles": {
     "default": {
       "provider": "ollama",
       "model": "mistral",
       "temperature": 0.5
     }
   }
   ```

2. **Use OpenAI Instead of Ollama:**
   ```json
   "profiles": {
     "default": {
       "provider": "openai",
       "model": "gpt-4-turbo-preview"
     }
   }
   ```
   Then set env var: `CHATTERBOX_OPENAI_API_KEY=sk-...`

3. **Increase Conversation Memory:**
   ```json
   "memory": {
     "conversation_window_size": 10
   }
   ```

4. **Change Logging Level:**
   ```json
   "logging": {
     "level": "DEBUG"
   }
   ```

After editing, restart Chatterbox for changes to take effect.

---

### HACS Repository Configuration

If hosting the integration yourself, configure HACS discovery with `hacs.json` at the repo root:

```json
{
  "name": "Chatterbox",
  "content_in_root": false,
  "filename": "custom_components/chatterbox"
}
```

This tells HACS:
- **name:** Display name in HACS UI
- **content_in_root:** Set to `false` because the integration is in a subdirectory
- **filename:** Path to the integration folder relative to repo root

For the official Chatterbox repo:
```
Repository: https://github.com/phaedrus/hentown
HACS Custom Repository: Yes
Category: Integration
```

---

### Custom Tools and Extensions

The Chatterbox agentic loop supports custom tools. To add your own:

1. **Define the Tool:**
   ```python
   from src.chatterbox.conversation.tools import ToolDefinition

   my_tool = ToolDefinition(
       name="get_device_status",
       description="Get the status of a Home Assistant device",
       input_schema={
           "type": "object",
           "properties": {
               "entity_id": {"type": "string", "description": "Entity ID (e.g., light.living_room)"}
           }
       }
   )
   ```

2. **Register in Tool Registry:**
   ```python
   from src.chatterbox.conversation.tools import ToolRegistry

   registry = ToolRegistry()
   registry.register("get_device_status", my_tool, my_handler_function)
   ```

3. **Restart Chatterbox**

See the [Tool Calling documentation](tools-and-extensions.md) for more details.

---

## FAQ

### Can I run Chatterbox on the same machine as Home Assistant?

**Yes.** While this guide shows them on separate machines, you can run both on the same hardware:

```
Home Assistant (http://localhost:8123)
   └─ connects to
Chatterbox Conversation Server (http://localhost:8765)
   └─ uses
Ollama (http://localhost:11434)
```

Just use `http://localhost:8765` as the server URL in the HA configuration flow.

**Caveat:** Resource contention — both HA and Chatterbox are resource-intensive. Recommend:
- CPU: 4+ cores
- RAM: 8GB minimum (16GB recommended)
- Consider: Move one to a different machine for production

---

### Can I use a different LLM (not Ollama)?

**Yes.** Chatterbox supports multiple providers:

1. **OpenAI:**
   ```bash
   export CHATTERBOX_LLM_PROVIDER=openai
   export CHATTERBOX_OPENAI_API_KEY=sk-your-key
   ```
   Then in `settings.json`: `"provider": "openai"`

2. **Any OpenAI-Compatible Endpoint:**
   ```json
   {
     "profiles": {
       "default": {
         "provider": "openai",
         "model": "your-model"
       }
     },
     "openai": {
       "base_url": "https://your-endpoint.com/v1",
       "api_key": "your-key"
     }
   }
   ```

3. **Local Models (besides Ollama):**
   - llama.cpp: Configure via API endpoint
   - vLLM: Uses OpenAI-compatible API
   - Hugging Face TGI: Uses OpenAI-compatible API

See the [LLM Providers documentation](llm-providers.md) for details.

---

### How do I update Chatterbox?

**Via HACS:**
1. Go to **HACS** → **Integrations**
2. Find **Chatterbox**
3. If an update is available, click **Upgrade**
4. Restart Home Assistant

**Manual:**
1. Pull latest from repository: `git pull origin main`
2. Copy updated files to `~/.homeassistant/custom_components/chatterbox/`
3. Restart Home Assistant

**Note:** Settings are preserved across updates.

---

### How do I backup/restore conversations?

Conversation history is stored on the **Chatterbox server**, not in HA.

**Backup:**
```bash
# Chatterbox stores conversations in a database (SQLite by default)
# Location: ~/.config/chatterbox/conversations.db

# Backup the entire config directory:
tar czf chatterbox-backup.tar.gz ~/.config/chatterbox/
scp chatterbox-backup.tar.gz user@backup-machine:~/backups/
```

**Restore:**
```bash
# On the backup machine
tar xzf chatterbox-backup.tar.gz -C ~/
# Or copy conversations.db back to Chatterbox server
```

See [Conversation Persistence documentation](persistence.md) for advanced options.

---

### Can I use multiple Chatterbox instances?

**Yes.** Create multiple configurations in HA:

1. **Instance 1 (Living Room):**
   - Server: `http://192.168.0.100:8765`
   - Agent Name: "Living Room AI"

2. **Instance 2 (Bedroom):**
   - Server: `http://192.168.0.101:8765`
   - Agent Name: "Bedroom AI"

Then in Voice Assistants, select which agent to use for each pipeline.

**Benefit:** Load balancing, specialized models per room, etc.

---

### What if my network doesn't have .local (mDNS)?

If your network is offline or doesn't support Zeroconf:

1. **During HA Config Flow:**
   - Select "Manual Entry" instead of auto-discovery
   - Enter the static IP: `http://192.168.0.100:8765`

2. **Update in Home Assistant Later:**
   - Settings → Devices & Services
   - Find Chatterbox integration
   - Click three dots → Options
   - Update the URL field

---

## Support

### Getting Help

If you encounter issues:

1. **Check the Troubleshooting Section** (above) for your specific error
2. **Review Logs:**
   - HA: Settings → System → Logs (search "Chatterbox")
   - Chatterbox: Terminal where server is running
3. **Check GitHub Issues:** https://github.com/phaedrus/hentown/issues

### Reporting Bugs

When opening an issue, include:

1. **Home Assistant Version:** Settings → System → About
2. **Chatterbox Integration Version:** Settings → Devices & Services → Chatterbox
3. **Full Error Message:** Copy from HA Logs (Settings → System → Logs)
4. **Chatterbox Server Logs:** Terminal output where server is running
5. **Configuration (sanitized):** Your settings.json (remove sensitive keys)
6. **Steps to Reproduce:** Exact commands or voice inputs to trigger the issue

Example issue template:
```
**Home Assistant Version:** 2026.1.1
**Chatterbox Version:** 0.1.0
**LLM Provider:** Ollama (llama3.1:8b)

**Error:**
```
Chatterbox connection error for http://192.168.0.100:8765:
[Errno 111] Connection refused
```

**Steps to Reproduce:**
1. Start Chatterbox server: `python -m src.chatterbox.conversation.server`
2. Configure HA integration with URL: `http://192.168.0.100:8765`
3. Restart HA
4. Go to Voice Assistants and select Chatterbox agent
5. Speak a command: "What time is it?"

**Expected Behavior:** Chatterbox should respond with current time
**Actual Behavior:** No response, error in HA logs
```

---

### Development and Contribution

Interested in contributing? See [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Summary Checklist

Before you start using Chatterbox in production:

- [ ] Chatterbox server installed and running
- [ ] Ollama (or alternative LLM) running and model loaded
- [ ] Integration installed in Home Assistant (HACS or manual)
- [ ] Configuration flow completed with correct API key and URL
- [ ] Voice pipeline configured with Chatterbox as conversation agent
- [ ] STT (speech-to-text) configured
- [ ] TTS (text-to-speech) configured
- [ ] Test command successful ("What time is it?" etc.)
- [ ] Check Chatterbox server logs for any warnings
- [ ] (Optional) Backup `~/.config/chatterbox/` for safety

---

**Last Updated:** 2026-03-25
**Minimum Home Assistant Version:** 2025.x
**Integration Version:** 0.1.0
**Official Repository:** https://github.com/phaedrus/hentown

For more information, see:
- [Architecture Documentation](docs/architecture.md)
- [Configuration System](docs/ha-settings-schema.md)
- [HACS Setup Guide](docs/hacs-setup.md)
- [LLM Providers Reference](docs/llm-providers.md)
- [Troubleshooting Deep Dive](docs/troubleshooting.md)
