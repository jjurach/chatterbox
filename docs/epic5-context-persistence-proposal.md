# Epic 5 Proposal: Persistent Conversation Context

**Status:** Proposed (output of Task 4.8)
**Date:** 2026-02-20
**Depends on:** Epic 4 complete

---

## Problem Statement

The in-memory context system shipped in Epic 4 loses all conversation history
when the Chatterbox process restarts. For a home voice assistant this means:

- The LLM cannot reference what was said in a previous session ("like I
  mentioned yesterday, …").
- User preferences discovered during conversation are not retained.
- Smart-home context (e.g., "the bedroom lights are usually dim at 9pm") must
  be re-established each restart.

## Proposed Scope

### Goal 1: Persistent Session Store

Store conversation history in a durable backend so it survives process
restarts.

**Acceptance criteria:**
- History for any `conversation_id` is retrievable after process restart.
- Store supports concurrent access (multiple simultaneous HA conversations).
- Write latency does not add perceptibly to response time (<10 ms per turn).

**Candidate backends (to be evaluated in Epic 5 Task 5.1):**
- **SQLite** — zero-ops, local file, good for single-host deployment.
- **Redis** — fast, already common in HA setups.
- **PostgreSQL/SQLite via SQLAlchemy** — portable async ORM path.

### Goal 2: History Retention Policy

Define how long history is retained and how it is pruned.

**Acceptance criteria:**
- Configurable TTL per session (e.g., 30 days default).
- Automatic purge of expired sessions.
- Manual `clear_history(conversation_id)` still honoured.

### Goal 3: Context Search Tool

Allow the LLM to search prior conversation content as a tool call.

```
search_history(query: str, max_results: int = 5) -> list[str]
```

Enables responses like "You asked about the weather in Topeka last Tuesday."

**Acceptance criteria:**
- Tool registered in `ToolRegistry`.
- Full-text or semantic (embedding) search over stored history.
- Returns formatted snippets the LLM can cite.

### Goal 4: Multi-User Isolation

Ensure history from different HA users/devices is strictly isolated.

**Acceptance criteria:**
- `conversation_id` namespaced by HA user ID or device ID.
- No cross-user history leakage.
- Privacy controls: per-user data deletion API.

### Goal 5: Storage Interface Abstraction

Decouple storage backend from `ChatterboxConversationEntity` so backends
are swappable without touching entity logic.

**Proposed interface:**

```python
class ConversationStore(Protocol):
    async def load(self, conversation_id: str) -> list[dict]: ...
    async def save(self, conversation_id: str, history: list[dict]) -> None: ...
    async def delete(self, conversation_id: str) -> None: ...
    async def purge_expired(self) -> int: ...  # returns count purged
```

`ChatterboxConversationEntity` will accept an optional `store: ConversationStore`
argument. If `None`, falls back to the current in-memory dict.

---

## Estimated Effort

| Task | Effort |
|------|--------|
| 5.1 Backend evaluation + SQLite implementation | 8 h |
| 5.2 Retention policy + purge job | 4 h |
| 5.3 `ConversationStore` protocol + in-memory adapter | 4 h |
| 5.4 Wire store into `ChatterboxConversationEntity` | 4 h |
| 5.5 Context search tool | 8 h |
| 5.6 Multi-user isolation | 4 h |
| 5.7 Tests + documentation | 6 h |
| **Total** | **~38 h** |

---

## Interface Compatibility Note

The `async_process` / `ConversationInput` / `ConversationResult` public API is
**unchanged**. Epic 5 is an internal implementation change only, making it safe
to defer without creating a future breaking-change obligation.
