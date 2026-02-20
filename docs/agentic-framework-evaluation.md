# Agentic Framework Evaluation — Task 4.2

**Date:** 2026-02-20
**Status:** Decision Made — Custom Minimal Async Loop Selected
**Related:** Task 4.1 findings in `docs/ha-conversation-flow.md`

---

## Background

Task 4.1 established that Chatterbox's LLM integrates into Home Assistant as a custom
**ConversationEntity**, not as a Wyoming endpoint. The HA Assist pipeline is:

```
Wake Word (Wyoming) → STT (Wyoming) → Conversation Agent (HA integration) → TTS (Wyoming)
```

The ConversationEntity's `async_process()` method receives transcribed text, runs the
LLM (with tools), and returns a text response. The "agentic framework" question is
therefore: **what do we use inside `async_process()` for the tool-calling loop?**

---

## Evaluation Criteria

| Criterion | Weight | Rationale |
|---|---|---|
| Async-native | High | HA is asyncio; blocking calls cause event loop stalls |
| Simplicity | High | The loop pattern is linear and well-understood |
| Testability | High | Must be unit-testable without HA running |
| OpenAI-compatible | High | Must work with Ollama (local), OpenAI, and Claude proxy |
| Dependency footprint | Medium | Prefer already-installed packages |
| State management | Low | HA manages session state; we don't need framework-level state |
| Multi-agent support | Low | Single-agent pattern sufficient for Epic 4 |

---

## Option 1: LangChain Classic (Existing `agent.py`)

**Package:** `langchain-classic>=0.0.1` (already in pyproject.toml)

**What it is:** A compatibility shim for old LangChain v0.x API. The existing `agent.py`
uses `initialize_agent()` with a ReAct-style `chat-zero-shot-react-description` agent
and `ConversationBufferWindowMemory`.

**Assessment:**

| Criterion | Score | Notes |
|---|---|---|
| Async-native | ❌ | Uses `run_in_executor` — blocks a thread |
| Simplicity | ⚠️ | ReAct string parsing is fragile |
| Testability | ⚠️ | Requires mocking LangChain internals |
| OpenAI-compatible | ✅ | Uses `ChatOpenAI` (Ollama-compatible) |
| Dependency footprint | ✅ | Already installed |
| State management | ⚠️ | `ConversationBufferWindowMemory` is in-memory only |

**Verdict:** ❌ Not recommended for HA ConversationEntity integration.
- Synchronous design conflicts with HA's async architecture
- LangChain Classic is a legacy compat shim, not forward-compatible
- ReAct string parsing is brittle; modern LLMs use structured tool_call responses
- Will remain in codebase for existing usage but should not be extended

---

## Option 2: LangGraph (1.0.7 — Already Installed)

**Package:** `langgraph>=1.0.0` (already installed in tools venv)

**What it is:** The modern successor to LangChain agents. Represents agentic workflows
as directed graphs with typed state, persistence checkpoints, and streaming support.

**Assessment:**

| Criterion | Score | Notes |
|---|---|---|
| Async-native | ✅ | Full async support |
| Simplicity | ⚠️ | Graph/node model adds structural overhead for a linear loop |
| Testability | ⚠️ | State graphs require graph-specific test patterns |
| OpenAI-compatible | ✅ | Works with any OpenAI-compatible model |
| Dependency footprint | ✅ | Already installed |
| State management | ✅ | Built-in `TypedDict` state, checkpointing |
| Multi-agent support | ✅ | Core design goal |

**Verdict:** ⚠️ Available but overkill for Epic 4.
- LangGraph excels at multi-agent, branching, and checkpoint scenarios
- Our ConversationEntity has a linear tool-calling loop: no branching, no checkpoints
- The graph/node model adds complexity without benefit for our use case
- **Future option:** If Epic 5 requires parallel tool execution or multi-agent, LangGraph should be re-evaluated

---

## Option 3: Custom Minimal Async Loop (OpenAI SDK) — Selected ✅

**Package:** `openai>=2.0.0` (openai 2.16.0 already installed)

**What it is:** A hand-written `while True` loop that calls the LLM via `openai.AsyncOpenAI`,
dispatches tool calls, feeds results back, and repeats until the model returns a final
text response. Works with any OpenAI-compatible backend (Ollama, OpenAI, LiteLLM proxy).

**The loop (pseudocode):**
```python
async def run(user_text, chat_history, tools):
    messages = chat_history + [{"role": "user", "content": user_text}]
    while True:
        response = await client.chat.completions.create(
            model=model, messages=messages, tools=tools
        )
        choice = response.choices[0]
        if choice.finish_reason == "stop":
            return choice.message.content
        # Execute tool calls
        messages.append(choice.message)  # assistant message with tool_calls
        for tc in choice.message.tool_calls:
            result = await dispatch_tool(tc.function.name, tc.function.arguments)
            messages.append(tool_result_message(tc.id, result))
```

**Assessment:**

| Criterion | Score | Notes |
|---|---|---|
| Async-native | ✅ | `openai.AsyncOpenAI` is fully async |
| Simplicity | ✅ | ~50 lines of loop logic |
| Testability | ✅ | Mock the `AsyncOpenAI` client easily |
| OpenAI-compatible | ✅ | Works with Ollama, OpenAI, Claude proxy |
| Dependency footprint | ✅ | OpenAI SDK already installed |
| State management | ✅ | HA manages session state; messages list handles within-turn state |
| Multi-agent support | ⚠️ | Not built-in; LangGraph available if needed later |

**Verdict:** ✅ **Selected.** The correct tool for the job. Simple, async, testable, and
exactly as powerful as the use case requires.

---

## Option 4: Raw Anthropic SDK

**Package:** `anthropic` (not installed)

**Assessment:** ❌ Not selected.
- Not installed; would add a new dependency
- Vendor-locked to Anthropic's API format
- Ollama uses OpenAI-compatible format, not Anthropic format
- The OpenAI SDK already handles Anthropic models via LiteLLM/proxy

---

## Decision Summary

**Selected:** Option 3 — Custom Minimal Async Loop using `openai.AsyncOpenAI`

**Rationale:**
1. Async-native: Required for HA ConversationEntity
2. OpenAI-compatible: Works with Ollama (dev), OpenAI (production), and Claude proxies
3. Simplest correct implementation: The tool-calling pattern is well-understood and linear
4. LangGraph is available as a future upgrade path if Epic 5 needs complex agentic patterns

**What's not changing:**
- `agent.py` (LangChain Classic) — retained for existing CLI usage; not extended
- LangGraph — available in venv, not used for Epic 4 core; may be used in future epics

---

## Initial Architecture: `src/chatterbox/conversation/`

### `providers.py` — LLM Provider Abstraction
- `LLMProvider` Protocol: `async def complete(messages, tools) -> CompletionResult`
- `OpenAICompatibleProvider`: wraps `openai.AsyncOpenAI`, configurable base_url + model

### `loop.py` — AgenticLoop
- `AgenticLoop(provider, tool_dispatcher, max_iterations)`
- `async def run(user_text, chat_history, tools) -> str`
- Handles tool call dispatching, message accumulation, iteration limit

### `entity.py` — ChatterboxConversationEntity
- Mirrors HA's `ConversationEntity` interface (no HA dependency for testability)
- `ConversationInput` dataclass, `ConversationResult` dataclass
- `async def async_process(user_input: ConversationInput) -> ConversationResult`
- Owns the `AgenticLoop` instance; bridges HA's interface to the loop

---

## References

- Task 4.1 change log: `dev_notes/changes/2026-02-20_00-15-36_task-4.1-ha-conversation-flow-research.md`
- HA Conversation Flow: `docs/ha-conversation-flow.md`
- HA ConversationEntity API: https://developers.home-assistant.io/docs/core/conversation/custom_agent/
- HA LLM API: https://developers.home-assistant.io/docs/core/llm/
- LangGraph docs: https://langchain-ai.github.io/langgraph/
