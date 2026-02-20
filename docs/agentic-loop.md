# Chatterbox Agentic Loop — Architecture and Design

**Task:** Epic 4, Task 4.14 — Documentation Package
**Status:** Complete (2026-02-20)
**Implements:** Tasks 4.2–4.8, 4.10–4.13

---

## Overview

The Chatterbox conversation package implements a **minimal async agentic loop** that processes one conversation turn at a time. It takes transcribed text as input, invokes an LLM with registered tool definitions, dispatches any tool calls the LLM requests (concurrently), feeds results back, and returns the LLM's final text response.

The design was selected in Task 4.2 after evaluating LangGraph and LangChain. A custom loop was chosen because the required pattern is **linear** — single agent, no branching sub-graphs, no parallel conversation streams. See `docs/agentic-framework-evaluation.md` for the full evaluation.

---

## Package Structure

```
src/chatterbox/conversation/
├── __init__.py
├── providers.py        # LLMProvider protocol, OpenAICompatibleProvider,
│                       # ToolDefinition, LLMError hierarchy, UsageStats,
│                       # CostEstimator, RateLimiter
├── loop.py             # AgenticLoop — the core tool-calling engine
├── entity.py           # ChatterboxConversationEntity (HA ConversationEntity)
├── server.py           # FastAPI HTTP adapter for development/testing
└── tools/
    ├── __init__.py
    ├── registry.py     # ToolRegistry — registration, build_dispatcher()
    ├── cache.py        # ToolResultCache, CachingDispatcher (Task 4.13)
    ├── weather.py      # WeatherTool (Open-Meteo, no API key)
    └── datetime_tool.py # DateTimeTool (stdlib, IANA timezone support)
```

---

## Component Roles

### `LLMProvider` (providers.py)

A `Protocol` (structural interface) that any LLM backend must satisfy:

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> CompletionResult: ...
```

**`OpenAICompatibleProvider`** is the concrete implementation. It uses
`openai.AsyncOpenAI` and accepts any OpenAI-compatible base URL — enabling
Ollama, LiteLLM, or any local model with an OpenAI-compatible API.

Configuration:

```python
from chatterbox.conversation.providers import OpenAICompatibleProvider

provider = OpenAICompatibleProvider(
    model="gpt-4o-mini",          # model name
    api_key="sk-...",              # defaults to OPENAI_API_KEY env var
    base_url=None,                 # None = OpenAI; set for local models
    rate_limiter=None,             # optional RateLimiter instance
)
```

### `AgenticLoop` (loop.py)

The core engine. Runs until the LLM produces a `finish_reason="stop"` response
or `max_iterations` is exhausted.

**State flow** (detailed design in `docs/agentic-loop-state-machine.md`):

```
RECEIVE_INPUT
    ↓
LLM_INFERENCE  ←──────────────────────────┐
    ↓                                      │
TOOL_DECISION                              │
    ├── finish_reason="stop" → OUTPUT      │
    └── finish_reason="tool_calls"         │
             ↓                             │
        TOOL_EXECUTION  (concurrent)       │
             ↓                             │
        RESULT_AGGREGATION ────────────────┘
```

Usage:

```python
from chatterbox.conversation.loop import AgenticLoop

loop = AgenticLoop(
    provider=provider,
    tool_dispatcher=dispatcher,   # from ToolRegistry.build_dispatcher()
    max_iterations=10,
    system_prompt="You are a helpful assistant.",
)

response = await loop.run(
    user_text="What's the weather in Kansas?",
    chat_history=[],               # prior turns in OpenAI message format
    tools=[weather_def, dt_def],   # ToolDefinition objects
)
```

**Concurrency:** When the LLM requests multiple tool calls in a single response,
all are dispatched concurrently via `asyncio.gather`. Results are collected in
order and appended to the message history before the next LLM call.

**Error handling:** Tool call exceptions are caught at dispatch time and
converted to JSON error strings (`{"error": "..."}`). The LLM receives the
error result and can decide how to respond. Unexpected `finish_reason` values
are logged and the content returned as-is.

### `ChatterboxConversationEntity` (entity.py)

Connects the HA `ConversationEntity` interface to the `AgenticLoop`. Owns the
loop instance and manages per-session chat history in memory.

```python
from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
)

entity = ChatterboxConversationEntity(
    provider=provider,
    tool_dispatcher=dispatcher,
    tools=registry.get_definitions(),
    max_history_turns=20,           # keep last 20 turns (40 messages)
    auto_create_conversation_id=True,
)

result = await entity.async_process(
    ConversationInput(
        text="What time is it in Tokyo?",
        conversation_id="session-abc",  # None for stateless single-turn
    )
)
print(result.response_text)
```

**History management:** In-memory histories are keyed by `conversation_id`.
Older turns beyond `max_history_turns` are silently dropped to bound token
usage. Persistent storage is scoped to Epic 5 (see
`docs/epic5-context-persistence-proposal.md`).

**Error handling:** All LLM errors are caught and translated to user-friendly
voice-suitable messages. The entity never raises to its caller — it always
returns a `ConversationResult`.

### `ConversationServer` (server.py)

A **FastAPI** HTTP adapter for development and testing. Wraps
`ChatterboxConversationEntity` as a REST service so the agentic loop can be
exercised without a running Home Assistant instance.

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/conversation` | Process one turn (text → text) |
| `DELETE` | `/conversation/{id}` | Clear history for a session |
| `DELETE` | `/conversation` | Clear all session histories |
| `GET` | `/health` | Health / readiness check |

See `src/chatterbox/conversation/server.py` for the full usage example.

---

## Error Handling Architecture

### LLM Errors

`providers.py` defines a hierarchy:

```
LLMError
├── LLMRateLimitError   — 429 from API
├── LLMConnectionError  — network unreachable
└── LLMAPIError         — other HTTP errors (5xx, auth failures)
    .status_code: int | None
```

`ChatterboxConversationEntity.async_process()` catches all three and returns
graceful spoken-language error messages rather than propagating.

### Tool Errors

- `AgenticLoop._dispatch_tool_calls()` catches all exceptions and converts them
  to `{"error": "..."}` JSON strings. The LLM sees the error as a tool result.
- `ToolRegistry.build_dispatcher()` adds **timeout** and **retry** wrappers.
  Unknown tool names return `{"error": "Unknown tool: ..."}` without raising.

---

## Rate Limiting and Cost Tracking

**`RateLimiter`** (providers.py): A sliding-window token bucket with
configurable `calls_per_minute`. `OpenAICompatibleProvider` integrates it
transparently; callers do not need to add delays themselves.

**`UsageStats` / `CostEstimator`** (providers.py): Each `CompletionResult`
carries a `UsageStats` instance. `CostEstimator` maps known model names to
per-token prices and computes `estimated_cost_usd`. Currently informational
(logged at DEBUG level); billing enforcement is out of scope for Epic 4.

---

## Performance Optimisations (Task 4.13)

### Concurrent Tool Dispatch

Multiple tool calls requested in a single LLM response are dispatched
concurrently via `asyncio.gather`. For a turn that calls both `get_weather`
and `get_current_datetime`, the two network calls overlap rather than
serialise.

### Tool Result Cache (`tools/cache.py`)

`ToolResultCache` is a TTL dict cache keyed by `(tool_name, canonical_args)`.
`CachingDispatcher` is a transparent wrapper around any dispatcher:

```python
from chatterbox.conversation.tools.cache import ToolResultCache, CachingDispatcher

cache = ToolResultCache(default_ttl=300.0)  # 5-minute TTL
cached_dispatcher = CachingDispatcher(
    inner=registry.build_dispatcher(),
    cache=cache,
    cached_tools={"get_weather"},  # only cache these tools
)
```

Cache hits skip the LLM tool dispatch entirely. Cache entries are
invalidated explicitly via `cache.invalidate(name, args)` or cleared in bulk
with `cache.clear()`.

---

## Testing

| Suite | Location | Count |
|-------|----------|-------|
| Unit — providers | `tests/unit/test_conversation/test_providers.py` | ~50 |
| Unit — loop | `tests/unit/test_conversation/test_loop.py` | ~30 |
| Unit — entity | `tests/unit/test_conversation/test_entity.py` | ~40 |
| Unit — registry | `tests/unit/test_conversation/test_registry.py` | ~30 |
| Unit — tools | `tests/unit/test_conversation/test_tools.py` | ~30 |
| Unit — cache | `tests/unit/test_conversation/test_cache.py` | 20 |
| Unit — server | `tests/unit/test_conversation/test_server.py` | ~20 |
| E2E | `tests/integration/test_end_to_end.py` | 17 |

Run all unit tests:

```bash
/home/phaedrus/hentown/tools/venv/bin/pytest tests/unit/ -v
```

---

## Related Documents

- `docs/agentic-framework-evaluation.md` — Framework selection rationale (Task 4.2)
- `docs/agentic-loop-state-machine.md` — Detailed state machine design (Task 4.3)
- `docs/ha-conversation-flow.md` — How this fits into the HA Assist pipeline
- `docs/context-management-research.md` — Context/history design decisions (Task 4.8)
- `docs/epic5-context-persistence-proposal.md` — Persistent storage proposal
- `docs/tool-development.md` — Guide for adding new tools
- `docs/conversation-flows.md` — End-to-end conversation examples
