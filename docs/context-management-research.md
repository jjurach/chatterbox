# Context Management Research — Task 4.8

**Status:** Complete
**Date:** 2026-02-20
**Decision:** Defer persistent storage to Epic 5; ship production-ready in-memory stub in Epic 4.

---

## Research Questions

Task 4.8 asked us to answer:

1. Does the HA ConversationEntity provide built-in context facilities?
2. What storage options are realistic for persistent conversation history?
3. What is the complexity tradeoff: implement now vs. defer?
4. What minimum enhancements does the in-memory stub need before Epic 4 ships?

---

## Findings

### 1. HA ConversationEntity context model

Home Assistant's `ConversationEntity.async_process(user_input)` receives a
`ConversationInput` with an optional `conversation_id` string. HA itself
**does not store or manage** per-session history — that responsibility belongs
entirely to the integration. HA simply routes calls with the same
`conversation_id` back to the same entity instance. Our `ChatterboxConversationEntity`
is therefore free to implement any storage strategy it chooses.

### 2. Existing in-memory stub (pre-Task-4.8)

`ChatterboxConversationEntity` already maintains a working multi-turn context
system:

- `self._histories: dict[str, list[dict]]` keyed by `conversation_id`
- Each successful turn appends `{"role":"user",...}` + `{"role":"assistant",...}`
- History is passed to `AgenticLoop.run(chat_history=...)` on every subsequent turn
- Sessions are isolated; failed turns do not corrupt history

This is fully functional for in-process use, and is already exercised by 11
unit tests.

### 3. Persistence options evaluated

| Option | Complexity | Operational overhead | Epic 4 fit |
|--------|-----------|----------------------|------------|
| In-memory (current) | Low | None | ✓ sufficient |
| SQLite (local file) | Medium | File path config | Moderate |
| Redis | Medium | Separate service | High |
| PostgreSQL | High | DB provisioning | Too high |
| DynamoDB | High | AWS infra + IAM | Too high |

For a voice assistant on a home network, in-memory state is adequate for
session durations (<10 min typical). Cross-restart persistence adds
operational surface area with no near-term user-visible benefit.

### 4. Token window management (gap identified)

The existing stub had **no upper bound on history size**. A very long
session could accumulate thousands of messages, exceeding the LLM's context
window and inflating API costs. This gap was closed by Task 4.8 (see below).

---

## Decision: Defer Persistence to Epic 5

**Rationale:**

- The in-memory stub is production-quality for single-process deployment.
- Persistent storage requires design decisions (schema, retention policy,
  multi-user isolation, GDPR/privacy controls) that are out of scope for
  Epic 4's end-to-end validation goal.
- The `conversation_id` interface is already compatible with any future
  persistent backend — swapping in a DB-backed store requires only a change
  to `async_process` internals, not the public API.

**Task 4.10 (Context Stub + Epic 5 Proposal) is the path forward.**

---

## Task 4.8 Code Deliverables

Two enhancements were made to `ChatterboxConversationEntity` to make the
in-memory stub production-ready:

### 4.8.1 `max_history_turns` — bounded token consumption

```python
ChatterboxConversationEntity(
    ...,
    max_history_turns=20,   # keep last 20 user+assistant pairs (default)
)
```

- Default: **20 turns** (40 messages) — appropriate for voice sessions.
- Set to `0` to disable truncation (useful in tests or for very long sessions
  where the caller manages token budgets externally).
- Truncation happens at read time; the stored list is also replaced with the
  truncated version after each successful turn to bound memory usage.

### 4.8.2 `auto_create_conversation_id` — stateful single-caller mode

```python
ChatterboxConversationEntity(
    ...,
    auto_create_conversation_id=True,
)
```

- When `True` and the caller omits `conversation_id`, a UUID4 is generated
  and returned in `ConversationResult.conversation_id`.
- The caller can then echo this ID on subsequent turns to continue the session.
- Defaults to `False` to preserve the existing stateless (single-turn)
  behaviour for callers that do not need history.

---

## Epic 5 Proposal

See [`docs/epic5-context-persistence-proposal.md`](epic5-context-persistence-proposal.md)
for the scoped proposal for full persistent context management.
