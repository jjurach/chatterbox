# Conversation Flows

**Task:** Epic 4, Task 4.14 — Documentation Package
**Status:** Complete (2026-02-20)

Annotated traces of how Chatterbox processes different types of conversation turns. Each scenario shows the message sequence, tool interactions, and final response.

---

## Architecture Context

Within the Home Assistant voice pipeline, Chatterbox's conversation layer sits between STT and TTS:

```
User speaks
    ↓
Wake Word (Wyoming)
    ↓
STT — Whisper (Wyoming)     → "What's the weather in Kansas?"
    ↓
Conversation Agent          ← this package
    ↓ (text response)
TTS — Piper (Wyoming)
    ↓
User hears spoken response
```

The conversation agent receives **text** from STT and returns **text** to TTS. All LLM and tool logic is internal.

For development and testing, `ChatterboxConversationEntity` is also accessible via the HTTP adapter in `server.py` (`POST /conversation`).

---

## Scenario 1: Direct Response (No Tools)

**User:** "Tell me a fun fact about penguins."

The LLM can answer from training knowledge — no tool call needed.

```
Messages sent to LLM (iteration 1):
  [system]  "You are Chatterbox, a helpful voice assistant..."
  [user]    "Tell me a fun fact about penguins."

LLM response:
  finish_reason = "stop"
  content = "Penguins are one of the few birds that can't fly,
             but they're remarkably fast swimmers — emperor penguins
             can reach speeds of up to 15 miles per hour underwater."

Loop terminates. Response returned to caller.
```

**Total LLM calls:** 1
**Tool calls:** 0

---

## Scenario 2: Single Tool Call (Weather)

**User:** "What's the weather in Kansas City right now?"

The LLM identifies a real-time information need and calls `get_weather`.

```
Messages sent to LLM (iteration 1):
  [system]  "You are Chatterbox, a helpful voice assistant..."
  [user]    "What's the weather in Kansas City right now?"

LLM response:
  finish_reason = "tool_calls"
  tool_calls = [
    { id: "call_abc", name: "get_weather", arguments: {"location": "Kansas City"} }
  ]

→ AgenticLoop dispatches get_weather({"location": "Kansas City"})

WeatherTool:
  1. Geocodes "Kansas City" → (39.0997, -94.5786, "Kansas City, Missouri, United States")
  2. Fetches Open-Meteo forecast API
  3. Returns: {
       "location_name": "Kansas City, Missouri, United States",
       "temperature_c": 8.2,
       "temperature_f": 46.8,
       "conditions": "Partly cloudy",
       "humidity_percent": 62,
       "wind_speed_kmh": 18.3,
       "wind_speed_mph": 11.4
     }

Messages sent to LLM (iteration 2):
  [system]  "You are Chatterbox..."
  [user]    "What's the weather in Kansas City right now?"
  [assistant, tool_calls] <the tool_calls message from above>
  [tool, call_abc] '{"location_name": "Kansas City, Missouri...", ...}'

LLM response:
  finish_reason = "stop"
  content = "In Kansas City, Missouri it's currently 47 degrees Fahrenheit
             with partly cloudy skies. Humidity is at 62% and winds are
             blowing at about 11 miles per hour."

Loop terminates.
```

**Total LLM calls:** 2
**Tool calls:** 1 (get_weather)

---

## Scenario 3: Multiple Tool Calls (Concurrent Dispatch)

**User:** "What time is it in London and what's the weather there?"

The LLM may request both tools in a single response, or make sequential calls.

```
Messages sent to LLM (iteration 1):
  [system]  "You are Chatterbox..."
  [user]    "What time is it in London and what's the weather there?"

LLM response (both tools in one response):
  finish_reason = "tool_calls"
  tool_calls = [
    { id: "call_dt1", name: "get_current_datetime", arguments: {"timezone": "Europe/London"} },
    { id: "call_wx1", name: "get_weather",           arguments: {"location": "London"} }
  ]

→ AgenticLoop dispatches both concurrently via asyncio.gather:
    get_current_datetime({"timezone": "Europe/London"})   ─┐
    get_weather({"location": "London"})                    ─┤ concurrent
                                                            ┘
  Results collected (in call order):
    call_dt1 → '{"datetime_iso": "2026-02-20T14:35:00+00:00", "time": "14:35:00",
                  "timezone": "Europe/London", "day_of_week": "Friday", ...}'
    call_wx1 → '{"location_name": "London, England, United Kingdom",
                  "temperature_c": 9.1, "temperature_f": 48.4,
                  "conditions": "Overcast", ...}'

Messages sent to LLM (iteration 2):
  [system] ...
  [user]   "What time is it in London and what's the weather there?"
  [assistant, tool_calls] <both tool calls>
  [tool, call_dt1] '{"datetime_iso": "2026-02-20T14:35:00+00:00", ...}'
  [tool, call_wx1] '{"location_name": "London...", ...}'

LLM response:
  finish_reason = "stop"
  content = "In London it's currently 2:35 PM on Friday, February 20th.
             The weather is overcast with a temperature of 48 degrees
             Fahrenheit."
```

**Total LLM calls:** 2
**Tool calls:** 2 (dispatched concurrently — latency = max(dt_time, weather_time))

---

## Scenario 4: Multi-Turn Conversation

When `conversation_id` is provided, `ChatterboxConversationEntity` maintains
chat history across turns.

```
Turn 1:
  ConversationInput(text="What's the weather in Seattle?", conversation_id="sess-1")

  → Loop runs (similar to Scenario 2)
  → Response: "In Seattle it's 52°F with light rain."

  History stored for "sess-1":
    [user]      "What's the weather in Seattle?"
    [assistant] "In Seattle it's 52°F with light rain."

Turn 2:
  ConversationInput(text="Should I bring an umbrella?", conversation_id="sess-1")

  Messages sent to LLM (iteration 1):
    [system]    "You are Chatterbox..."
    [user]      "What's the weather in Seattle?"        ← from history
    [assistant] "In Seattle it's 52°F with light rain." ← from history
    [user]      "Should I bring an umbrella?"

  LLM response (no tools needed — context sufficient):
    finish_reason = "stop"
    content = "Yes, definitely bring an umbrella — Seattle has light rain
               right now."
```

**History truncation:** `ChatterboxConversationEntity` keeps at most
`max_history_turns` turns (default: 20). Older turns are silently dropped.

---

## Scenario 5: Tool Error

**User:** "What's the weather in Narnia?"

The geocoder cannot find the location; the tool returns an error dict.

```
LLM requests get_weather({"location": "Narnia"})

WeatherTool._geocode raises ValueError("Location not found: 'Narnia'")
→ as_dispatcher_entry() catches ValueError
→ returns: '{"error": "Location not found: 'Narnia'"}'

Messages sent to LLM (iteration 2):
  ...
  [tool, call_abc] '{"error": "Location not found: 'Narnia'"}'

LLM response:
  finish_reason = "stop"
  content = "I'm sorry, I couldn't find a location called Narnia.
             Could you provide a real city or region?"
```

The LLM gracefully handles the error result and formulates an appropriate
spoken response.

---

## Scenario 6: LLM Error (Rate Limit)

If the LLM API returns a 429 rate-limit response, `OpenAICompatibleProvider`
raises `LLMRateLimitError`. `ChatterboxConversationEntity` catches it and
returns a user-friendly fallback.

```
AgenticLoop.run() → provider.complete() → raises LLMRateLimitError

ChatterboxConversationEntity catches LLMRateLimitError
→ returns ConversationResult(
    response_text="I'm sorry, I'm receiving too many requests right now. "
                  "Please try again in a moment.",
    conversation_id="sess-1",
  )

No history update (turn is not stored on LLM error).
```

Similar patterns apply for `LLMConnectionError` and `LLMAPIError`.

---

## Scenario 7: Max Iterations Exceeded

If the LLM enters a tool call loop and never returns `finish_reason="stop"`,
`AgenticLoop` raises `RuntimeError` after `max_iterations` calls.

```
Iteration 1: LLM calls get_weather("London") → result
Iteration 2: LLM calls get_weather("London") again → result (same)
...
Iteration 10: still calling tools

AgenticLoop raises RuntimeError("AgenticLoop exceeded max_iterations=10...")

ChatterboxConversationEntity catches RuntimeError
→ returns ConversationResult(
    response_text="I'm sorry, I got stuck trying to answer that. "
                  "Please try again.",
    ...
  )
```

`max_iterations` defaults to 10. Increase it only if your tools require many
sequential reasoning steps.

---

## Scenario 8: Cache Hit (Tool Result Reuse)

When `CachingDispatcher` is configured and the same tool/args combination is
called within the TTL window:

```
First call:
  dispatcher("get_weather", {"location": "Austin, Texas"})
  → cache miss → executes WeatherTool → stores result → returns result

Second call (within 5 minutes):
  dispatcher("get_weather", {"location": "Austin, Texas"})
  → cache HIT → returns stored result immediately (no HTTP request)
```

Cache key uses canonical JSON (sorted keys), so `{"location": "Austin, Texas"}`
and `{"location": "Austin, Texas"}` (different dicts, same content) resolve to
the same key.

---

## HTTP API Flow (Development / Testing)

When using the FastAPI server instead of direct entity calls:

```
POST /conversation
Content-Type: application/json

{
  "text": "What's the weather in Austin?",
  "conversation_id": "dev-session-1",
  "language": "en"
}

→ server calls entity.async_process(ConversationInput(...))
→ agentic loop runs (same as above)

HTTP 200 response:
{
  "response_text": "In Austin, Texas it's currently 68°F with clear skies.",
  "conversation_id": "dev-session-1"
}
```

Clear a session's history:

```
DELETE /conversation/dev-session-1
→ HTTP 200 {"cleared": "dev-session-1"}
```

Health check:

```
GET /health
→ HTTP 200 {"status": "ok", "entity": "Chatterbox"}
```

---

## Latency Reference

For typical use cases on a well-connected network:

| Scenario | Typical latency |
|----------|----------------|
| Direct LLM response (no tools) | 0.5–2s (LLM only) |
| Single tool call | 1–4s (LLM × 2 + tool) |
| Two concurrent tool calls | 1–4s (LLM × 2 + max(tool_a, tool_b)) |
| Cache hit on tool call | ~0.5–1s (LLM × 2, no tool I/O) |

---

## Related Documents

- `docs/agentic-loop.md` — Architecture and component design
- `docs/tool-development.md` — Guide for adding new tools
- `docs/agentic-loop-state-machine.md` — State machine design detail
- `docs/ha-conversation-flow.md` — HA Assist pipeline integration
- `tests/integration/test_end_to_end.py` — Automated E2E test scenarios
