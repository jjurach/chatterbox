# Persistent Storage Architecture

**Document Status:** Epic 5 Phase 1 Complete (Tasks 5.1-5.3)
**Last Updated:** 2026-03-25

## Overview

Chatterbox now includes a persistent storage layer for conversations, messages, tool calls, and context snapshots. This document describes the architecture, design decisions, and migration path to PostgreSQL.

## Key Design Principles

1. **Pluggable Backends** — Storage abstraction via Protocol (base.py) allows SQLite in development and PostgreSQL in production without code changes.

2. **Async Throughout** — All repository and backend operations are async/await, matching Epic 4's pattern.

3. **Repository Pattern** — Clean data access layer decoupling ORM specifics from business logic.

4. **Schema Design** — Normalized relational schema with proper foreign keys, indexes, and JSON columns for flexible metadata.

5. **No ORM Lazy Loading** — All relationships are explicit (no lazy-loaded attributes during request handling).

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│  Application (ChatterboxConversationEntity) │
└──────────────┬──────────────────────────────┘
               │
        ┌──────▼───────────────────┐
        │  Repository Layer        │
        │  (UserRepository, etc.)   │
        └──────┬───────────────────┘
               │
        ┌──────▼───────────────────┐
        │  SQLAlchemy ORM Models   │
        │  (User, Conversation...) │
        └──────┬───────────────────┘
               │
        ┌──────▼───────────────────┐
        │  StorageBackend Protocol │
        │  (base.py interface)     │
        └──────┬───────────────────┘
               │
        ┌──────▼───────────────────┐
        │  SQLite Implementation   │
        │  (sqlite.py)             │
        └──────────────────────────┘
```

## Data Model

### Users Table
- **Primary Key:** `id` (UUID)
- **Unique:** `username`
- **Fields:** email, created_at, metadata (JSON)
- **Relationships:** 1→N Conversations

### Conversations Table
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** user_id (nullable for anonymous)
- **Unique:** `conversation_id` (client-facing ID)
- **Fields:** language, device, created_at, updated_at, metadata
- **Indexes:** user_id, conversation_id, created_at
- **Relationships:** 1→N Messages, 1→N ToolCalls, 1→N ContextSnapshots

### Messages Table
- **Primary Key:** `id` (UUID)
- **Foreign Key:** conversation_id
- **Fields:** sequence (order in conversation), role (user/assistant/system), content, created_at, metadata
- **Indexes:** (conversation_id, sequence) for efficient history retrieval
- **Relationships:** 1→N ToolCalls

### ToolCalls Table
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** conversation_id, message_id (optional)
- **Fields:** call_id, tool_name, arguments (JSON), result, error, duration_ms, created_at
- **Index:** conversation_id (for audit logs)

### ContextSnapshots Table
- **Primary Key:** `id` (UUID)
- **Foreign Key:** conversation_id
- **Fields:** message_sequence, context_window (JSON array), metadata, created_at
- **Used by:** Epic 5 Phase 2 for context retention and recovery

## Storage Abstraction

### StorageBackend Protocol (backends/base.py)

The protocol defines the interface any backend must implement:

```python
class StorageBackend(Protocol):
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]: ...
    async def create_tables(self) -> None: ...
    async def drop_tables(self) -> None: ...
    async def healthcheck(self) -> bool: ...
    @property
    def connection_string(self) -> str: ...
```

**Benefits:**
- Easy testing with in-memory SQLite
- No coupling to specific database
- Clear contract for new backends
- Supports dependency injection

### SQLiteStorage Implementation (backends/sqlite.py)

Concrete implementation using `aiosqlite` for async support:

```python
storage = SQLiteStorage(
    database_url="sqlite+aiosqlite:///./chatterbox.db",
    echo=False,  # Set True to log SQL
)

await storage.initialize()
async with storage.get_session() as session:
    repo = ConversationRepository(session)
    conv = await repo.create(user_id=user_id)
await storage.shutdown()
```

**Design Choices:**
- **NullPool** — SQLite doesn't support connection pooling; each connection is created/destroyed per request
- **Async Safe** — Uses `aiosqlite` (pure Python SQLite driver) for async compatibility
- **In-Memory Support** — Can use `:memory:` for testing
- **File Permissions** — Automatically creates parent directories

## Repository Layer

Repositories provide a clean data access interface:

### ConversationRepository
- `create()` — Create new conversation
- `get_by_id()` — Fetch by UUID
- `get_by_conversation_id()` — Fetch by client-facing ID
- `get_by_user_id()` — List user's conversations (paginated)
- `update()` — Update fields
- `delete()` — Delete conversation and all related data

### MessageRepository
- `add()` — Append message (auto-assigns sequence)
- `get_by_id()` — Fetch single message
- `get_by_conversation()` — Fetch all messages (with optional limit)
- `delete_old()` — Retention policy (keep N most recent)
- `delete()` — Delete single message

### ToolCallRepository
- `add()` — Log a tool call
- `get_by_id()` — Fetch single call
- `get_by_conversation()` — Audit log for conversation
- `get_by_tool_name()` — Analytics queries

### ContextSnapshotRepository
- `create()` — Store a context snapshot
- `get_by_id()` — Fetch single snapshot
- `get_by_conversation()` — Retrieve snapshots for conversation

### UserRepository
- `create()`, `get_by_id()`, `get_by_username()`, `update()`, `delete()`

## Configuration

### Environment Variables

```bash
# Full connection string (overrides others)
export CHATTERBOX_DATABASE_URL="sqlite+aiosqlite:///./prod.db"

# Or configure backend:
export CHATTERBOX_DATABASE_BACKEND="sqlite"
export CHATTERBOX_DATABASE_PATH="./chatterbox.db"
export CHATTERBOX_DATABASE_ECHO="false"  # Log SQL
export CHATTERBOX_DATABASE_POOL_SIZE="10"  # PostgreSQL only
```

### Python API

```python
from chatterbox.persistence.config import get_config, PersistenceConfig

config = get_config()
url = config.get_connection_url()

# Or create custom config:
config = PersistenceConfig(
    database_backend="sqlite",
    database_path="./my_chatterbox.db",
    database_echo=True,
)
```

## Migration Path: SQLite → PostgreSQL

The storage abstraction is designed to support PostgreSQL migration without application code changes.

### Phase 1 → Phase 2 Roadmap

1. **Phase 1 (Done):** SQLite backend with all models and repositories
2. **Phase 2 (TODO):** Implement PostgresqlStorage backend
   - Connection pooling with `asyncpg`
   - Connection string from environment
   - Migration testing
3. **Phase 3 (TODO):** Alembic migration tooling
   - Schema version tracking
   - Forward/backward migrations
   - Zero-downtime deployments
4. **Phase 4 (TODO):** Production deployment
   - Read replicas for analytics
   - Backup/restore strategies
   - Performance tuning

### Implementation Checklist for PostgreSQL

```python
# New file: src/chatterbox/persistence/backends/postgresql.py
class PostgresqlStorage:
    def __init__(self, connection_string: str, pool_size: int = 10, ...):
        self._engine = create_async_engine(
            connection_string,
            echo=echo,
            poolclass=AsyncPool,
            pool_size=pool_size,
            pool_recycle=pool_recycle,
        )
        # Rest of implementation
```

The application layer needs no changes — just switch the backend in config:

```bash
export CHATTERBOX_DATABASE_BACKEND="postgresql"
export DATABASE_URL="postgresql+asyncpg://user:pass@host/dbname"
```

## Integration with Epic 4

### Current State

Epic 4 conversation entity maintains **in-memory** history per conversation_id:

```python
self._histories: dict[str, list[dict[str, Any]]] = {}
```

Epic 5 Phase 1 provides the **storage abstraction** to back this with a database.

### Epic 5 Phase 2 Plan

Phase 2 (Context Retrieval & Retention Policies) will:

1. Integrate repositories into ConversationEntity
2. Persist messages to database instead of in-memory dict
3. Implement context window retrieval from storage
4. Add retention policies (keep N turns, delete after TTL, etc.)
5. Add context search capabilities (for future LLM-based retrieval)

**No breaking changes** — repositories provide the same data access semantics.

## Thread Safety & Connection Pooling

### SQLite

- **NullPool** — One connection per request, no shared state
- **async/await** — All operations are async-safe within asyncio event loop
- **Session Management** — Use `async with storage.get_session()` context manager

### PostgreSQL (Future)

- **AsyncPool** — Configurable pool size (default 10)
- **Connection Recycling** — Recycle stale connections after 1 hour
- **Row-Level Locking** — Optional for concurrent updates

## Data Consistency Guarantees

1. **Foreign Key Integrity** — CASCADE DELETE enforces referential integrity
2. **Unique Constraints** — username, conversation_id are unique
3. **Transactional Safety** — All repository methods within single transaction
4. **ACID Compliance** — Both SQLite and PostgreSQL provide ACID guarantees

## Performance Considerations

### Indexes

- **Users:** `(username)` for login queries
- **Conversations:** `(user_id)`, `(conversation_id)`, `(created_at)` for list/search
- **Messages:** `(conversation_id, sequence)` for history retrieval
- **ToolCalls:** `(conversation_id)` for audit logs

### Query Optimization

- Use repository methods with explicit limits (avoid full table scans)
- Lazy-load relationships only when needed (e.g., before persisting)
- Batch operations for bulk inserts/deletes

### Scalability

- **SQLite:** Single-device, up to 100K conversations
- **PostgreSQL:** Multi-device, millions of conversations with proper indexing

## Testing

All persistence operations are tested in `tests/unit/test_persistence/`:

- **test_schema.py** — ORM model validation
- **test_sqlite_storage.py** — CRUD operations
- **test_repositories.py** — Repository pattern tests

Tests use in-memory SQLite (`sqlite+aiosqlite:///:memory:`) for speed and isolation.

## See Also

- [Agentic Loop State Machine](agentic-loop-state-machine.md) — How persistence integrates with conversation loop
- [Epic 5 Context Persistence Proposal](epic5-context-persistence-proposal.md) — Phase 2 detailed design
- [AGENTS.md](../AGENTS.md) — Development workflow and quality standards
