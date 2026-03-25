# Epic 6 Addendum: Home Assistant Custom Integration
# Tasks 6.14–6.21

**Document ID:** EPIC-6-HA-INTEGRATION-2026
**Parent Epic:** Epic 6 — Backend Deployment & Home Assistant Connection
**Addendum Date:** 2026-03-25
**Status:** Planned
**Estimated Additional Hours:** ~40 hours
**HA Target Version:** 2025.x+ (2026.1.1 confirmed on target host)

---

## Summary of Decisions

This addendum captures planning for the custom Home Assistant conversation agent integration, based on the following architectural decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Integration pattern | Pattern B — HTTP proxy | Calls existing Chatterbox FastAPI; thin wrapper, no HA-side deps |
| HA host | Separate LAN host (e.g. `192.168.0.167`) | Chatterbox server is on a different machine |
| Integration location | `custom_components/chatterbox/` in chatterbox repo root | Single repo, HACS custom repository support |
| HACS distribution | Custom repository (option A) | `hacs.json` at repo root, points at chatterbox repo |
| Authentication | Required API key, Bearer token | Single key, HA → Chatterbox direction; auto-generated if not set |
| Offline/error behavior | Return spoken error text → Piper on HA host | Free, no credit card, Piper runs on HA host independently |
| Media player / offline WAV | Deferred to Epic 8 | Revisit when box3b gains `media_player` entity |
| mDNS discovery | Zeroconf auto-discovery + manual URL fallback | Standard HA pattern (ESPHome, etc.) |
| Config flow | Display name (user-configurable, default "Chatterbox"), URL, API key | OptionsFlow for reconfiguration after setup |
| Config file | Unified `~/.config/chatterbox/settings.json` | Eliminates `mellona.yaml`; Mellona supports JSON config_chain |
| Device control (HA LLM API) | Not now — designed for future addition | No architectural blockers; add as tool in later epic |
| HA version | 2025.x+ only | No legacy API shims needed |

---

## Architecture Overview

```
box3b (ESP32-S3)
    ↓ wake word / audio
HA Voice Pipeline (192.168.0.167)
    ↓ STT (Whisper Wyoming)   ← runs on Chatterbox server or HA
    ↓ transcript text
custom_components/chatterbox  ← THIS ADDENDUM
    ↓ POST /conversation (Bearer token)
Chatterbox FastAPI server     ← existing Epic 4/5 service
    ↓ AgenticLoop + tools + persistence
    ↑ response text
custom_components/chatterbox
    ↓ response text
HA Voice Pipeline
    ↓ TTS (Piper add-on on HA host)
box3b speaker
```

**Error path (Chatterbox server unreachable):**
```
custom_components/chatterbox
    → aiohttp timeout / ConnectionError
    → return ConversationResult("Chatterbox is temporarily offline, please try again")
    → fire HA persistent_notification
    → Piper on HA host speaks the error text normally
```

---

## Task 6.14: Unified Configuration System

**Objective:** Make `~/.config/chatterbox/settings.json` the single source of truth for all Chatterbox and Mellona configuration. Eliminate `mellona.yaml`. Add API key support with auto-generation.

**Estimated Hours:** 6

**Acceptance Criteria:**
- [ ] `Settings` class loads `~/.config/chatterbox/settings.json` as a config source (env vars still override)
- [ ] `api_key` field added to `Settings`; auto-generated UUID4 if not present at startup
- [ ] Auto-generated key logged clearly at INFO level: `"API key: <key>"` (one-time, on generation)
- [ ] Mellona initialized via `get_config(config_chain=["~/.config/chatterbox/settings.json"])` — no separate mellona.yaml required
- [ ] `~/.config/chatterbox/mellona.yaml` documented as deprecated (backward-compatible during transition)
- [ ] `settings.json` schema updated to include `api`, `providers`, `profiles`, `stt_profiles`, `tts_profiles` sections
- [ ] Unit tests: config loading priority (env var > settings.json > defaults), API key generation, Mellona config_chain

**Implementation Details:**

Extend `Settings` with a custom pydantic-settings source that reads `~/.config/chatterbox/settings.json`. Priority order (highest to lowest):
1. `CHATTERBOX_*` environment variables
2. `~/.config/chatterbox/settings.json`
3. Built-in defaults

New `api_key` field:
```python
api_key: str | None = None  # CHATTERBOX_API_KEY env var or settings.json["api"]["key"]
```

Startup logic (in server entry point):
```python
if not settings.api_key:
    settings.api_key = str(uuid.uuid4())
    logger.info("API key (auto-generated): %s", settings.api_key)
    # Persist to settings.json so it survives restarts
```

Final `~/.config/chatterbox/settings.json` schema:
```json
{
  "server": { "host": "0.0.0.0", "port": 10700 },
  "api": {
    "key": null,
    "comment": "Set to a UUID string, or leave null to auto-generate on startup"
  },
  "conversation": {
    "port": 8765,
    "host": "0.0.0.0"
  },
  "providers": {
    "faster_whisper": { "model": "base", "device": "cpu", "language": null },
    "piper": { "voice": "en_US-lessac-medium", "sample_rate": 22050 },
    "ollama": { "base_url": "http://localhost:11434/v1" }
  },
  "profiles": {
    "default": { "provider": "ollama", "model": "llama3.1:8b", "temperature": 0.7 }
  },
  "stt_profiles": { "default": { "provider": "faster_whisper" } },
  "tts_profiles": { "default": { "provider": "piper" } },
  "memory": { "conversation_window_size": 3 },
  "logging": { "level": "INFO" }
}
```

**Files Changed:**
- `src/chatterbox/config/__init__.py` — add JSON source, `api_key` field, startup key generation
- `~/.config/chatterbox/settings.json` — restructured with api, providers, profiles sections
- `~/.config/chatterbox/mellona.yaml` — add deprecation comment; preserved for backward compat
- `tests/unit/test_config/test_settings.py` — new unit tests

---

## Task 6.15: Chatterbox FastAPI Authentication Middleware

**Objective:** Add Bearer token validation to the Chatterbox FastAPI conversation server. The `/health` endpoint remains unauthenticated (HA needs it for connection testing).

**Estimated Hours:** 4

**Depends On:** Task 6.14 (api_key in Settings)

**Acceptance Criteria:**
- [ ] All endpoints except `GET /health` require `Authorization: Bearer <key>` header
- [ ] Returns HTTP 401 with JSON error on missing/invalid token
- [ ] `GET /health` remains unauthenticated and returns `{"status": "ok", ...}`
- [ ] API key read from `Settings.api_key` (resolved per Task 6.14)
- [ ] Unit tests: valid key accepted, invalid key rejected, missing header rejected, health bypasses auth

**Implementation Details:**

FastAPI middleware approach:
```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.api_key:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

**Files Changed:**
- `src/chatterbox/conversation/server.py` — add auth middleware
- `tests/unit/test_conversation/test_server.py` — add auth tests

---

## Task 6.16: Zeroconf/mDNS Advertisement

**Objective:** Advertise the Chatterbox conversation server on the LAN via Zeroconf so HA can auto-discover it without manual IP/port entry.

**Estimated Hours:** 3

**Acceptance Criteria:**
- [ ] Server advertises `_chatterbox._tcp.local.` on startup
- [ ] TXT record includes `version`, `api_path=/conversation`
- [ ] Advertisement withdrawn cleanly on server shutdown
- [ ] `zeroconf` added to `pyproject.toml` dependencies
- [ ] HA's Zeroconf integration can see the service (tested manually)

**Implementation Details:**

Service type: `_chatterbox._tcp.local.`
Name: `Chatterbox.<hostname>._chatterbox._tcp.local.`

```python
from zeroconf import ServiceInfo, Zeroconf
import socket

info = ServiceInfo(
    "_chatterbox._tcp.local.",
    f"Chatterbox.{socket.gethostname()}._chatterbox._tcp.local.",
    addresses=[socket.inet_aton(get_local_ip())],
    port=settings.conversation_port,
    properties={"version": "1.0", "api_path": "/conversation"},
)
zeroconf = Zeroconf()
zeroconf.register_service(info)
# On shutdown: zeroconf.unregister_service(info); zeroconf.close()
```

The HA `manifest.json` (Task 6.17) will declare `"zeroconf": [{"type": "_chatterbox._tcp.local."}]` so HA triggers the config flow automatically on discovery.

**Files Changed:**
- `src/chatterbox/conversation/server.py` — add Zeroconf advertisement lifecycle
- `pyproject.toml` — add `zeroconf` dependency

---

## Task 6.17: Scaffold `custom_components/chatterbox/`

**Objective:** Create the HA custom integration package structure with all required metadata files and a working (minimal) `__init__.py`.

**Estimated Hours:** 3

**Acceptance Criteria:**
- [ ] `custom_components/chatterbox/` created at chatterbox repo root
- [ ] `manifest.json` valid and accepted by HA 2025.x
- [ ] `hacs.json` at repo root passes HACS validation
- [ ] `__init__.py` implements `async_setup_entry` and `async_unload_entry` (minimal, no-op stubs initially)
- [ ] `const.py` defines all shared constants
- [ ] `strings.json` covers config flow and options flow labels
- [ ] Loading the integration in HA produces no errors (verified manually)

**Implementation Details:**

Directory structure:
```
custom_components/chatterbox/
  __init__.py          # async_setup_entry, async_unload_entry
  manifest.json        # integration metadata
  config_flow.py       # Task 6.18
  conversation.py      # Task 6.19
  const.py             # shared constants
  strings.json         # UI labels
  translations/
    en.json            # English translations (mirrors strings.json)

hacs.json              # repo root
```

`manifest.json`:
```json
{
  "domain": "chatterbox",
  "name": "Chatterbox",
  "version": "0.1.0",
  "documentation": "https://github.com/phaedrus/hentown",
  "requirements": [],
  "dependencies": [],
  "codeowners": [],
  "iot_class": "local_polling",
  "config_flow": true,
  "integration_type": "service",
  "zeroconf": [{"type": "_chatterbox._tcp.local."}]
}
```

`hacs.json` (repo root):
```json
{
  "name": "Chatterbox",
  "content_in_root": false,
  "filename": "custom_components/chatterbox"
}
```

`const.py`:
```python
DOMAIN = "chatterbox"
CONF_URL = "url"           # e.g. "http://192.168.0.100:8765"
CONF_API_KEY = "api_key"
CONF_AGENT_NAME = "agent_name"
DEFAULT_AGENT_NAME = "Chatterbox"
DEFAULT_TIMEOUT = 30        # seconds
OFFLINE_MESSAGE = "Chatterbox is temporarily offline, please try again."
```

**Files Created:**
- `custom_components/chatterbox/__init__.py`
- `custom_components/chatterbox/manifest.json`
- `custom_components/chatterbox/const.py`
- `custom_components/chatterbox/strings.json`
- `custom_components/chatterbox/translations/en.json`
- `hacs.json`

---

## Task 6.18: Config Flow & Options Flow

**Objective:** Implement HA GUI-based setup wizard (Config Flow) and reconfiguration (Options Flow). Supports Zeroconf auto-discovery and manual URL entry.

**Estimated Hours:** 6

**Depends On:** Task 6.17

**Acceptance Criteria:**
- [ ] Zeroconf discovery triggers config flow automatically when Chatterbox is running on LAN
- [ ] Manual flow: URL field (e.g. `http://192.168.0.100:8765`), API key field, display name field
- [ ] "Test Connection" validates `GET /health` before allowing submission
- [ ] Config entry created with `url`, `api_key`, `agent_name` stored in HA config entry
- [ ] OptionsFlow allows reconfiguring all three fields after setup
- [ ] Error states handled: unreachable host, wrong API key, malformed URL
- [ ] All UI strings in `strings.json` / `translations/en.json`
- [ ] Tests: config flow steps, zeroconf discovery flow, options flow, error states

**Implementation Details:**

Two entry points to ConfigFlow:
1. **Zeroconf trigger** (`async_step_zeroconf`): receives `ZeroconfServiceInfo`, pre-fills URL, prompts only for API key + display name
2. **Manual trigger** (`async_step_user`): full form — URL + API key + display name

Connection test (shared):
```python
async def _test_connection(url: str, api_key: str) -> bool:
    """Call GET /health (no auth required) to verify reachability."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return resp.status == 200
```

OptionsFlow mirrors ConfigFlow form (all three fields reconfigurable).

**Files Created/Changed:**
- `custom_components/chatterbox/config_flow.py`
- `custom_components/chatterbox/strings.json` (updated)
- `custom_components/chatterbox/translations/en.json` (updated)
- `tests/unit/test_ha_integration/test_config_flow.py`

---

## Task 6.19: ConversationAgent Implementation

**Objective:** Implement the HA `ConversationEntity` subclass that proxies conversation turns to the Chatterbox FastAPI server.

**Estimated Hours:** 8

**Depends On:** Tasks 6.15, 6.17, 6.18

**Acceptance Criteria:**
- [ ] `ChatterboxAgent` subclasses `homeassistant.components.conversation.ConversationEntity`
- [ ] `async_process(user_input: ConversationInput) -> ConversationResult` calls `POST /conversation` with Bearer auth
- [ ] Conversation ID passed through for multi-turn context
- [ ] On success: returns `ConversationResult` with LLM response text
- [ ] On connection error / timeout: returns spoken error text (`OFFLINE_MESSAGE`) AND fires `persistent_notification`
- [ ] On HTTP 401: logs warning, returns spoken error about authentication
- [ ] Entity registered with HA's conversation platform on `async_setup_entry`
- [ ] Entity unregistered cleanly on `async_unload_entry`
- [ ] `supported_languages` returns `MATCH_ALL` (Chatterbox handles all languages)
- [ ] Integration appears in HA Settings → Voice Assistants → Conversation Agent dropdown
- [ ] Tests: successful turn, connection error path, auth error path, multi-turn ID threading

**Implementation Details:**

```python
# conversation.py
from homeassistant.components.conversation import ConversationEntity, ConversationInput, ConversationResult
from homeassistant.components.conversation import MATCH_ALL
import aiohttp

class ChatterboxAgent(ConversationEntity):

    _attr_supported_languages = MATCH_ALL

    def __init__(self, hass, entry) -> None:
        self._url = entry.data[CONF_URL]
        self._api_key = entry.data[CONF_API_KEY]
        self._attr_name = entry.data[CONF_AGENT_NAME]
        self._attr_unique_id = entry.entry_id

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"{self._url}/conversation",
                    json={
                        "text": user_input.text,
                        "conversation_id": user_input.conversation_id,
                        "language": user_input.language,
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                )
                resp.raise_for_status()
                data = await resp.json()
                return ConversationResult(
                    response=intent.IntentResponse(language=user_input.language),
                    conversation_id=data.get("conversation_id"),
                )
                # (response speech set from data["response_text"])
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Chatterbox unreachable: %s", err)
            self.hass.components.persistent_notification.async_create(
                f"Chatterbox is offline: {err}",
                title="Chatterbox Unavailable",
                notification_id="chatterbox_offline",
            )
            # Return spoken error — Piper on HA host will synthesize this
            result = ConversationResult(response=intent.IntentResponse(...))
            result.response.async_set_speech(OFFLINE_MESSAGE)
            return result
```

**Note on Epic 8 dependency:** Pre-generating an offline WAV file and playing it via `media_player.play_media` is deferred to Epic 8, when the box3b gains a `media_player` entity. The current approach (spoken error text via Piper on HA host) is the permanent solution for the HA-side pipeline and will not be replaced in Epic 8 — Epic 8 adds *additional* audio feedback at the device level.

**Files Created:**
- `custom_components/chatterbox/conversation.py`
- `tests/unit/test_ha_integration/test_conversation_agent.py`
- `tests/unit/test_ha_integration/__init__.py`

---

## Task 6.20: Integration Tests & Manual Verification

**Objective:** Verify end-to-end flow with a real HA instance.

**Estimated Hours:** 4

**Depends On:** Tasks 6.17, 6.18, 6.19

**Acceptance Criteria:**
- [ ] Integration added via HA UI without errors (Zeroconf discovery path)
- [ ] Integration added via HA UI without errors (manual URL path)
- [ ] Agent appears in Settings → Voice Assistants → select "Chatterbox" in pipeline
- [ ] Voice command reaches Chatterbox FastAPI and returns spoken response
- [ ] Stopping Chatterbox server produces spoken offline message within one voice command
- [ ] HA persistent notification appears when server is unreachable
- [ ] Restarting Chatterbox server restores normal operation without HA restart
- [ ] Options flow successfully updates URL / API key / display name
- [ ] HACS custom repository import works (add repo URL in HACS, install integration)

**Verification Checklist (manual):**
```
[ ] chatterbox service running, key confirmed in logs
[ ] HACS → Integrations → Custom repositories → add repo URL
[ ] HACS → Integrations → Chatterbox → Install
[ ] HA restart
[ ] Settings → Devices & Services → Add Integration → Chatterbox
[ ] Select discovered device OR enter URL manually
[ ] Enter API key from logs
[ ] Enter display name (e.g. "Chatterbox")
[ ] Test Connection passes
[ ] Settings → Voice Assistants → Edit pipeline → set Conversation Agent to "Chatterbox"
[ ] Speak a test command → hear LLM response
[ ] Stop chatterbox service → speak → hear "temporarily offline"
[ ] Check HA notifications panel for offline alert
[ ] Restart chatterbox service → speak → hear LLM response again
```

---

## Task 6.21: Deployment Documentation

**Objective:** Document the complete HA integration installation and configuration process.

**Estimated Hours:** 3

**Acceptance Criteria:**
- [ ] `docs/ha-integration-guide.md` covers: prerequisites, HACS install, manual install, config flow walkthrough, API key setup, voice pipeline setup, troubleshooting
- [ ] `~/.config/chatterbox/settings.json` schema documented with all fields and comments
- [ ] HACS structure (`hacs.json`) documented
- [ ] Minimum HA version noted (2025.x)

**Files Created:**
- `docs/ha-integration-guide.md`

---

## Summary

| Task | Description | Hours | Depends On |
|------|-------------|-------|------------|
| 6.14 | Unified config system + API key | 6 | — |
| 6.15 | FastAPI Bearer auth middleware | 4 | 6.14 |
| 6.16 | Zeroconf advertisement | 3 | 6.14 |
| 6.17 | Scaffold custom_components/ | 3 | — |
| 6.18 | Config flow + options flow | 6 | 6.17 |
| 6.19 | ConversationAgent (HTTP proxy) | 8 | 6.15, 6.17, 6.18 |
| 6.20 | Integration tests + manual verification | 4 | 6.17–6.19 |
| 6.21 | Deployment documentation | 3 | 6.17–6.20 |
| **Total** | | **37 hours** | |

## Dependency Graph

```
6.14 (config/api key)
  ├─→ 6.15 (auth middleware)
  └─→ 6.16 (zeroconf advert.)
6.17 (scaffold)
  ├─→ 6.18 (config flow)
  │     └─→ 6.19 (ConversationAgent) ←─ 6.15
  │               └─→ 6.20 (tests)
  └─→ 6.20                └─→ 6.21
```

6.14 and 6.17 can run in parallel.
6.16 (Zeroconf) can run in parallel with 6.17–6.18.

---

## Deferred Items (Epic 8)

- **Pre-generated offline WAV + `media_player.play_media`**: Once box3b gains a `media_player` entity in Epic 8, add a task to pre-generate `offline.wav` at Chatterbox startup (via Piper while it's running), serve it from HA static path, and call `media_player.play_media` on the box3b entity as a supplementary notification. This is additive — the spoken error text path (Task 6.19) remains in place.

---

*Parent plan: [2026-03-24_epic-6-backend-deployment-ha-connection.md](2026-03-24_epic-6-backend-deployment-ha-connection.md)*
*Created: 2026-03-25*
