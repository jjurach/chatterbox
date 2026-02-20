# Tool Development Guide

**Task:** Epic 4, Task 4.14 — Documentation Package
**Status:** Complete (2026-02-20)

This guide explains how to add a new tool to the Chatterbox agentic loop so that the LLM can call it during conversation turns.

---

## Concepts

A **tool** in Chatterbox has three parts:

1. **`ToolDefinition`** — describes the tool to the LLM (name, description, parameter schema). The LLM reads this to decide when to call the tool.
2. **Async handler** — `async (args: dict) -> str` callable that executes the tool and returns a JSON string result.
3. **Registration** — the tool is registered with a `ToolRegistry`, which builds the dispatcher passed to `AgenticLoop`.

The two reference implementations are:

- `src/chatterbox/conversation/tools/weather.py` — external API, HTTP, error handling
- `src/chatterbox/conversation/tools/datetime_tool.py` — stdlib only, no I/O

---

## Step-by-Step: Adding a New Tool

### 1. Create the tool module

Create a new file in `src/chatterbox/conversation/tools/`. Follow the naming convention `<noun>_tool.py` for single-purpose tools or `<noun>.py` for multi-capability modules.

```python
# src/chatterbox/conversation/tools/my_tool.py
"""
My tool for the Chatterbox agentic loop.

Brief description of what the tool does and any external dependencies.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from chatterbox.conversation.providers import ToolDefinition

logger = logging.getLogger(__name__)


class MyTool:
    """One-line description.

    Attributes:
        TOOL_DEFINITION: Ready-to-use ToolDefinition for AgenticLoop.
    """

    TOOL_DEFINITION: ToolDefinition = ToolDefinition(
        name="my_tool",
        description=(
            "Concise, verb-led description that tells the LLM WHEN to call "
            "this tool and what it returns. This text appears verbatim in the "
            "LLM's context, so be specific and avoid ambiguity."
        ),
        parameters={
            "type": "object",
            "properties": {
                "required_param": {
                    "type": "string",
                    "description": "What this parameter means and expected format.",
                },
                "optional_param": {
                    "type": "integer",
                    "description": "Optional integer parameter, e.g. a count.",
                },
            },
            "required": ["required_param"],  # list only truly required params
        },
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def do_thing(self, required_param: str, optional_param: int = 10) -> dict[str, Any]:
        """Execute the tool's core logic.

        Args:
            required_param: Description.
            optional_param: Description.

        Returns:
            A dict describing the result. Keep keys short and descriptive.
            The LLM will receive this as a JSON string.

        Raises:
            ValueError: If inputs are invalid.
        """
        # ... implementation ...
        return {"result": "...", "detail": "..."}

    def as_dispatcher_entry(self):
        """Return an async callable for ToolRegistry.register().

        The returned callable accepts the raw args dict from the LLM and
        returns a JSON string. It must never raise — catch all exceptions
        and return {"error": "..."} instead.
        """

        async def _call(args: dict[str, Any]) -> str:
            required_param = args.get("required_param", "")
            if not required_param:
                return json.dumps({"error": "Missing required argument: required_param"})

            optional_param = int(args.get("optional_param", 10))

            try:
                result = await self.do_thing(required_param, optional_param)
                return json.dumps(result)
            except ValueError as exc:
                return json.dumps({"error": str(exc)})
            except Exception as exc:
                logger.error("MyTool failed: %s", exc, exc_info=True)
                return json.dumps({"error": f"Tool error: {exc}"})

        return _call
```

### 2. Register the tool

In the code that sets up the conversation entity (e.g. `server.py`, a CLI entry point, or a test), register the tool with a `ToolRegistry`:

```python
from chatterbox.conversation.tools.registry import ToolRegistry
from chatterbox.conversation.tools.my_tool import MyTool

registry = ToolRegistry()

my = MyTool()
registry.register(MyTool.TOOL_DEFINITION, my.as_dispatcher_entry())

# Build the dispatcher after all tools are registered
dispatcher = registry.build_dispatcher(
    timeout=30.0,    # seconds per tool call
    max_retries=0,   # additional attempts on asyncio.TimeoutError
)

entity = ChatterboxConversationEntity(
    provider=provider,
    tool_dispatcher=dispatcher,
    tools=registry.get_definitions(),
)
```

> **Important:** `build_dispatcher()` snapshots the registry at call time.
> Tools registered after this call are not visible to the returned dispatcher.
> Register all tools before calling `build_dispatcher()`.

### 3. Write unit tests

Place tests in `tests/unit/test_conversation/`. Use a mock to isolate HTTP
calls or other I/O:

```python
# tests/unit/test_conversation/test_my_tool.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from chatterbox.conversation.tools.my_tool import MyTool


@pytest.fixture
def tool():
    return MyTool()


@pytest.mark.asyncio
async def test_happy_path(tool):
    result = await tool.do_thing(required_param="hello")
    assert result["result"] == "..."


@pytest.mark.asyncio
async def test_dispatcher_missing_param(tool):
    entry = tool.as_dispatcher_entry()
    response = await entry({})
    data = json.loads(response)
    assert "error" in data


@pytest.mark.asyncio
async def test_dispatcher_error_is_json(tool):
    entry = tool.as_dispatcher_entry()
    # simulate a ValueError from do_thing
    with patch.object(tool, "do_thing", side_effect=ValueError("bad input")):
        response = await entry({"required_param": "x"})
    data = json.loads(response)
    assert "error" in data
```

---

## Tool Design Guidelines

### Dispatcher handlers must never raise

The dispatcher callable (`as_dispatcher_entry()`) must catch **all** exceptions
and return a `{"error": "..."}` JSON string. Unhandled exceptions propagate
to `AgenticLoop._dispatch_tool_calls()`, which catches them and converts them
to error strings anyway — but it logs the error, which may be alarming. Better
to handle it in the tool itself with a meaningful message.

### Return JSON-serialisable dicts

The handler must return a `str` (the JSON encoding of the result). The LLM
receives this string as the tool's response. Keep the structure flat and
descriptive — the LLM reads it and extracts the answer.

Good:
```json
{"temperature_c": 22.5, "temperature_f": 72.5, "conditions": "Partly cloudy"}
```

Avoid deeply nested structures — they cost extra tokens and may confuse the
LLM.

### Write the `TOOL_DEFINITION` description carefully

The `description` field in `ToolDefinition` is what the LLM reads to decide
whether and when to call the tool. Be:

- **Specific** about what the tool returns.
- **Clear** about when to use it (vs. answering from training data).
- **Brief** — every word costs tokens in every conversation turn.

Parameter `description` fields are equally important. If the LLM doesn't
understand the expected format for `location`, it may pass "the weather in
Kansas" instead of "Kansas".

### Use `TOOL_DEFINITION` as a class attribute

This allows code that introspects tool definitions without instantiating the
tool:

```python
definitions = [WeatherTool.TOOL_DEFINITION, DateTimeTool.TOOL_DEFINITION]
```

### Avoid global state

Tools should be stateless or hold only configuration (e.g. HTTP timeout,
API credentials). The `AgenticLoop` may dispatch the same tool concurrently
for multiple requests.

---

## Optional: Tool Result Caching

For tools with expensive or rate-limited backends, wrap the dispatcher with
`CachingDispatcher`:

```python
from chatterbox.conversation.tools.cache import ToolResultCache, CachingDispatcher

cache = ToolResultCache(
    default_ttl=300.0,                  # seconds
    tool_ttls={"get_weather": 600.0},   # per-tool overrides
    max_size=256,                        # max cache entries
)

cached = CachingDispatcher(
    inner=dispatcher,
    cache=cache,
    cached_tools={"get_weather", "my_tool"},  # opt-in per tool
)

entity = ChatterboxConversationEntity(
    provider=provider,
    tool_dispatcher=cached,             # use cached dispatcher
    tools=registry.get_definitions(),
)
```

Cache keys are `(tool_name, canonicalised_args_json)`. Invalidate specific
entries with `cache.invalidate("my_tool", {"required_param": "hello"})` or
clear all with `cache.clear()`.

---

## Reference Implementations

| Tool | File | Notes |
|------|------|-------|
| `get_weather` | `tools/weather.py` | External HTTP API (Open-Meteo), geocoding, error handling |
| `get_current_datetime` | `tools/datetime_tool.py` | stdlib only, IANA timezone support |

---

## Checklist for a New Tool

- [ ] Module created in `src/chatterbox/conversation/tools/`
- [ ] `TOOL_DEFINITION` defined as a class attribute with a clear `description`
- [ ] `as_dispatcher_entry()` method returns an async callable that never raises
- [ ] All exceptions caught; errors returned as `{"error": "..."}` JSON
- [ ] Unit tests written covering happy path, missing args, and error cases
- [ ] Tool registered in the appropriate entry point (server, CLI, entity factory)
- [ ] Tool listed in `docs/tool-development.md` reference table (this file)
