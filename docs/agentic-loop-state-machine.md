# Agentic Loop State Machine Design

**Task:** Epic 4, Task 4.3 — Design Agentic Loop State Machine
**Status:** Complete (2026-02-20)
**Implemented in:** `src/chatterbox/conversation/loop.py`

---

## Overview

The Chatterbox agentic loop is a linear, single-agent state machine that processes one conversation turn at a time. It takes a user's transcribed text as input, invokes the LLM with optional tool definitions, dispatches any requested tool calls, feeds results back to the LLM, and returns a final text response.

Design decision (Task 4.2): A custom minimal async loop was selected over LangGraph because the required pattern is purely linear — no branching agents, no parallel sub-graphs. See `docs/agentic-framework-evaluation.md`.

---

## State Definitions

The loop progresses through the following logical states on each call to `AgenticLoop.run()`:

```
┌──────────────────┐
│ RECEIVE_INPUT    │  Entry point. Accepts user text + chat history.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ LLM_INFERENCE    │  Sends messages + tools to LLM provider.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TOOL_DECISION    │  Checks LLM finish_reason.
└────────┬─────────┘
         │
    ┌────┴──────────────────────┐
    │                           │
finish_reason="stop"    finish_reason="tool_calls"
    │                           │
    │                           ▼
    │               ┌──────────────────────┐
    │               │ TOOL_EXECUTION       │  Dispatches each tool call async.
    │               └──────────┬───────────┘
    │                          │
    │                          ▼
    │               ┌──────────────────────┐
    │               │ RESULT_AGGREGATION   │  Collects tool result strings.
    │               └──────────┬───────────┘
    │                          │
    │               Append tool results to messages,
    │               loop back to LLM_INFERENCE.
    │                          │
    │               ◄──────────┘
    │
    ▼
┌──────────────────┐
│ RESPONSE_        │  LLM content extracted as final text.
│ COMPOSITION      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ OUTPUT           │  Return response_text to caller (ConversationEntity).
└──────────────────┘
```

---

## State Details

### RECEIVE_INPUT

**Entry:** `AgenticLoop.run(user_text, chat_history, tools)`

Actions performed:
- Prepend system prompt message (if configured) to message list.
- Append chat history to message list.
- Append `{"role": "user", "content": user_text}` to message list.
- Initialize iteration counter.

**Exit:** Always → LLM_INFERENCE.

---

### LLM_INFERENCE

**Entry:** Message list ready; iteration counter checked against `max_iterations`.

Actions performed:
- Call `LLMProvider.complete(messages, tools)` → `CompletionResult`.
- Increment iteration counter.

**Exit:**
- `finish_reason == "stop"` → TOOL_DECISION (no-tool branch)
- `finish_reason == "tool_calls"` → TOOL_DECISION (tool branch)
- `finish_reason` is anything else → RESPONSE_COMPOSITION (warn + return content)
- `iteration >= max_iterations` → raise `RuntimeError`

---

### TOOL_DECISION

**Entry:** `CompletionResult` from LLM_INFERENCE.

Logic:
```
if result.finish_reason == "stop":
    → RESPONSE_COMPOSITION

elif result.finish_reason == "tool_calls" and result.tool_calls:
    → TOOL_EXECUTION

else:
    # unexpected finish_reason — treat content as final
    log warning
    → RESPONSE_COMPOSITION
```

**This state has no side effects** — it is purely a branch point.

---

### TOOL_EXECUTION

**Entry:** `result.tool_calls` list (one or more `ToolCall` objects).

Actions performed for each `ToolCall`:
1. Log the tool name and arguments (DEBUG level).
2. `await tool_dispatcher(name, arguments)` → `result_str`.
3. On exception: log error, set `result_str = json.dumps({"error": str(exc)})`.
4. Build `{"role": "tool", "tool_call_id": id, "content": result_str}` message.

Tool calls are dispatched **sequentially** in the current implementation. Parallel dispatch (using `asyncio.gather`) is a potential Task 4.13 optimization if tool latency becomes a bottleneck.

**Exit:** → RESULT_AGGREGATION.

---

### RESULT_AGGREGATION

**Entry:** List of tool result messages from TOOL_EXECUTION.

Actions performed:
1. Append `result.raw_message` (the assistant's tool-call request) to message list.
2. Extend message list with all tool result messages.

**Exit:** → LLM_INFERENCE (loop continues with enriched message list).

---

### RESPONSE_COMPOSITION

**Entry:** `result.content` string from LLM.

Actions performed:
- Extract text content: `response_text = result.content or ""`.
- Log iteration count at INFO level.

**Exit:** → OUTPUT.

---

### OUTPUT

**Entry:** `response_text` string.

Actions performed:
- Return `response_text` to the caller (`ChatterboxConversationEntity.async_process`).

The caller then:
1. Appends the user message and assistant message to `_histories[conversation_id]`.
2. Returns `ConversationResult(response_text=response_text, conversation_id=...)`.

---

## Iteration Guard

The loop enforces a maximum iteration limit (`max_iterations`, default 10) to prevent infinite tool-call cycles:

```
if iteration >= max_iterations:
    raise RuntimeError(
        f"AgenticLoop exceeded max_iterations={max_iterations} "
        "without reaching a final response."
    )
```

A `RuntimeError` here propagates to `ChatterboxConversationEntity.async_process`, which should catch it and return an appropriate error response to the user (error handling to be hardened in Task 4.7 / Task 4.12).

---

## Error Handling Strategy

| Failure Point | Handling | User Impact |
|---|---|---|
| LLM API error | Exception propagates from `LLMProvider.complete` | Turn fails; caller must handle |
| Tool raises exception | Caught in `_dispatch_tool_calls`; error serialized as JSON string result | LLM receives error message; may recover or report to user |
| `max_iterations` exceeded | `RuntimeError` raised | Turn fails; caller must handle |
| Unexpected `finish_reason` | Warning logged; content returned as-is | Degraded but functional |
| Empty LLM content on stop | `result.content or ""` → empty string returned | Silent empty response |

**Caller responsibility:** `ChatterboxConversationEntity.async_process` (and eventually the HA integration layer in Task 4.11) must wrap `async_process` in try/except and return a graceful error message (e.g. "Sorry, I encountered an error. Please try again.") rather than propagating the exception to the TTS pipeline.

---

## Interface Specifications

### AgenticLoop

```python
class AgenticLoop:
    def __init__(
        self,
        provider: LLMProvider,
        tool_dispatcher: ToolDispatcher,
        max_iterations: int = 10,
        system_prompt: str | None = None,
    ) -> None: ...

    async def run(
        self,
        user_text: str,
        chat_history: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
    ) -> str: ...
```

**`run()` contract:**
- Does not mutate `chat_history`.
- Returns a non-None string (may be empty if LLM returns empty content).
- Raises `RuntimeError` only on `max_iterations` exceeded.
- All other exceptions propagate from `provider.complete` or `tool_dispatcher`.

---

### LLMProvider (Protocol)

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
    ) -> CompletionResult: ...
```

**Implementation contract:**
- Must not raise for normal LLM responses.
- Must raise on network / authentication / rate-limit errors (no swallowing).
- `CompletionResult.finish_reason` must be `"stop"` or `"tool_calls"` for normal flow.

---

### ToolDispatcher (Callable)

```python
ToolDispatcher = Callable[[str, dict[str, Any]], Awaitable[str]]
```

**Contract:**
- Receives `(tool_name: str, arguments: dict)`.
- Returns a JSON-serializable string result.
- Raises `Exception` on tool failure (caught by loop; serialized as error JSON).
- Must be async-safe (called sequentially from the loop's event loop).

---

### ToolDefinition

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_openai_format(self) -> dict[str, Any]: ...
```

The `parameters` field must be a valid JSON Schema object (type `"object"` with `"properties"` and `"required"` keys). This format is used directly by `OpenAICompatibleProvider` and mirrors the HA LLM API helper format.

---

## Message Format

The loop uses the OpenAI chat completion message format throughout:

```python
# System message
{"role": "system", "content": "..."}

# User message
{"role": "user", "content": "What is the weather in Kansas?"}

# Assistant message (final text response)
{"role": "assistant", "content": "The weather in Kansas is..."}

# Assistant message (tool call request)
{
    "role": "assistant",
    "content": None,  # may be None
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location": "Kansas"}'},
        }
    ]
}

# Tool result message
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": '{"temperature": 72, "conditions": "partly cloudy"}',
}
```

---

## Sequence Diagram: Weather Query

```
User            ConversationEntity    AgenticLoop       LLM              WeatherTool
 │                     │                  │              │                    │
 │  "What's the        │                  │              │                    │
 │   weather in        │                  │              │                    │
 │   Kansas?"          │                  │              │                    │
 │─────────────────────►                  │              │                    │
 │              async_process(input)      │              │                    │
 │                     │──run(text, ...)──►              │                    │
 │                     │                  │──complete()──►                    │
 │                     │                  │◄─────────────│ finish="tool_calls"│
 │                     │                  │              │ tool: get_weather  │
 │                     │                  │──dispatch()──────────────────────►│
 │                     │                  │◄─────────────────────────────────│
 │                     │                  │         weather JSON              │
 │                     │                  │──complete()──►                    │
 │                     │                  │◄─────────────│ finish="stop"      │
 │                     │                  │              │ "The weather in…"  │
 │                     │◄─response_text───│              │                    │
 │◄─ConversationResult─│                  │              │                    │
```

---

## Context Management (Current State)

As of Task 4.3, `ChatterboxConversationEntity` maintains an **in-memory per-session chat history** dict:

```python
self._histories: dict[str, list[dict[str, Any]]] = {}
```

History is keyed by `conversation_id`. Sessions without a `conversation_id` get no history (stateless turn).

This is a **stub** pending Task 4.8 (Research Context Management) and Task 4.9/4.10. The stub is intentionally minimal:
- No persistence across process restarts.
- No TTL or eviction.
- No cross-session search.

The interface is designed so Task 4.9 can replace the `_histories` dict with a persistent backend without changing `AgenticLoop` or the public `async_process` API.

---

## Design Invariants

1. **`AgenticLoop` is stateless.** All conversation state is passed in via `chat_history`. The loop itself holds no mutable turn-level state between calls.
2. **Tool calls are serialized.** The loop calls `tool_dispatcher` sequentially, not concurrently. This avoids races on shared resources and simplifies error handling. Parallel dispatch can be added in Task 4.13 as an optimization.
3. **Message format is the OpenAI wire format.** This ensures compatibility with all OpenAI-compatible providers and with the HA LLM API helper (which also uses this format).
4. **Tools are optional.** If `tools=[]`, the loop calls the LLM without tool definitions and always reaches `RESPONSE_COMPOSITION` on the first iteration.
5. **The loop does not own context.** Chat history management is the caller's responsibility. This separation allows `ChatterboxConversationEntity` (or a future persistent context layer) to control retention, eviction, and storage.

---

## Implementation Status

| Component | File | Status |
|---|---|---|
| `AgenticLoop` | `src/chatterbox/conversation/loop.py` | Implemented (Task 4.2) |
| `OpenAICompatibleProvider` | `src/chatterbox/conversation/providers.py` | Implemented (Task 4.2) |
| `ChatterboxConversationEntity` | `src/chatterbox/conversation/entity.py` | Skeleton (Task 4.2) |
| Unit tests (24 tests) | `tests/unit/test_conversation/` | Passing (Task 4.2) |
| Weather tool | TBD | Task 4.5 |
| Tool framework | TBD | Task 4.6 |
| HA integration | TBD | Task 4.11 |
| Persistent context | TBD | Task 4.9 or 4.10 |

---

## Next Steps

- **Task 4.4:** Implement Core Agentic Loop — flesh out error handling in `async_process`, add structured logging, write additional edge-case unit tests.
- **Task 4.5:** Implement Weather Tool using `ToolDefinition` interface.
- **Task 4.6:** Implement Tool Framework (registry, discovery, second tool).
- **Task 4.7:** Integrate LLM with system prompts — finalize system prompt template, add rate-limiting and cost tracking.
