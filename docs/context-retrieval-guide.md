# Context Retrieval & Search Guide

Epic 5 Phase 2 implementation guide for context management, retention policies, search, and multi-user isolation.

## Overview

This guide covers the complete context retrieval, persistence, and search functionality for the Chatterbox conversation system. The implementation provides:

- **Task 5.4**: Retention Policy Implementation - TTL-based cleanup of old data
- **Task 5.5**: Context Retrieval - Efficient message retrieval with token counting
- **Task 5.6**: Context Search - Full-text search with filtering and ranking
- **Task 5.7**: Multi-User Isolation - Access control and user context enforcement

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  (Conversation handlers, API endpoints, LLM integration)   │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┼──────────────┬──────────────┐
       │             │              │              │
       ▼             ▼              ▼              ▼
┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐
│ Cleanup    │ │ Context  │ │  Search  │ │ Access Control   │
│ Service    │ │ Manager  │ │ Engine   │ │ Middleware       │
└────────────┘ └──────────┘ └──────────┘ └──────────────────┘
       │             │              │              │
       └─────────────┼──────────────┴──────────────┘
                     │
       ┌─────────────┴──────────────┐
       │                            │
       ▼                            ▼
┌─────────────────┐       ┌──────────────────┐
│   Repositories  │       │ UserContext      │
│ (Data Access)   │       │ (Permissions)    │
└─────────────────┘       └──────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│   SQLite Storage Backend (async)        │
│   (ORM: Conversation, Message, etc.)    │
└─────────────────────────────────────────┘
```

## Task 5.4: Retention Policy Implementation

### Overview

Implements configurable TTL-based cleanup of conversation data. Supports:
- Configurable retention periods per data type
- Safety checks (minimum messages per conversation)
- Dry-run mode for testing
- Background scheduled cleanup job
- Error handling and alerts

### Key Classes

#### RetentionPolicy

```python
from chatterbox.persistence.cleanup import RetentionPolicy

# Default policy: 30 days messages, 7 days snapshots
policy = RetentionPolicy()

# Custom policy: 60 days messages, keep at least 2 per conversation
policy = RetentionPolicy(
    message_ttl_days=60,
    tool_call_ttl_days=45,
    snapshot_ttl_days=14,
    conversation_ttl_days=180,
    min_messages_per_conversation=2
)
```

#### CleanupService

```python
from chatterbox.persistence.cleanup import CleanupService, RetentionPolicy

async with storage.get_session() as session:
    policy = RetentionPolicy(message_ttl_days=30)
    service = CleanupService(session, policy)

    # Execute cleanup
    stats = await service.execute_cleanup()
    print(f"Deleted {stats.messages_deleted} messages")

    # Or dry-run first
    stats = await service.dry_run()
    print(f"Would delete {stats.messages_deleted} messages")
```

#### ScheduledCleanupJob

```python
from chatterbox.persistence.cleanup import ScheduledCleanupJob

# Run cleanup every 24 hours
job = ScheduledCleanupJob(
    storage,
    policy=RetentionPolicy(),
    interval_hours=24
)

await job.start()   # Starts background task
await job.stop()    # Graceful shutdown
```

### Configuration

```python
# In environment or config file:
CHATTERBOX_RETENTION_MESSAGE_DAYS=30     # Default message retention
CHATTERBOX_RETENTION_SNAPSHOT_DAYS=7     # Context snapshot retention
CHATTERBOX_CLEANUP_INTERVAL_HOURS=24     # Run cleanup job every 24 hours
```

### Example: Full Cleanup Workflow

```python
async def run_daily_cleanup():
    storage = SQLiteStorage("sqlite+aiosqlite:///chatterbox.db")
    await storage.initialize()

    # Start scheduled job
    job = ScheduledCleanupJob(storage, interval_hours=24)
    await job.start()

    # Run manual cleanup
    async with storage.get_session() as session:
        service = CleanupService(session)
        stats = await service.execute_cleanup()

        if stats.has_errors:
            alert_admin(f"Cleanup errors: {stats.errors}")
        else:
            log_cleanup_metrics(stats)
```

## Task 5.5: Context Retrieval

### Overview

Efficiently retrieves conversation messages for LLM context windows with:
- Token counting and budgeting
- Pagination support
- Context integrity verification
- OpenAI API compatibility

### Key Classes

#### TokenCounter

```python
from chatterbox.persistence.context import TokenCounter

# Count tokens in text (character-based heuristic)
tokens = TokenCounter.count_tokens("Hello world")  # ~2-4 tokens
tokens = TokenCounter.count_message_tokens("user", "Hello")  # ~5 tokens
```

#### ContextMessage

```python
from chatterbox.persistence.context import ContextMessage

msg = ContextMessage(
    id="msg-123",
    role="user",
    content="What is the weather?",
    sequence=5,
    token_count=10
)

# Convert to dict
msg_dict = msg.to_dict()
```

#### ContextManager

```python
from chatterbox.persistence.context import ContextManager

async with storage.get_session() as session:
    manager = ContextManager(session, default_context_size=20)

    # Get last 10 messages
    context = await manager.get_context(conversation_id, limit=10)
    for msg in context:
        print(f"{msg.role}: {msg.content[:50]}...")

    # Build context window respecting token budget
    window = await manager.build_context_window(
        conversation_id,
        token_budget=4000  # GPT-4 context window
    )

    # Convert to OpenAI format
    messages = window.to_openai_format()
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )

    # Verify context integrity
    is_valid = await manager.verify_context_integrity(conversation_id)
    assert is_valid
```

### Context Window Composition

The context manager builds context windows intelligently:

1. **System Messages**: Always included (preserve_system_messages=True)
2. **Recent Messages**: Added newest-to-oldest until token budget reached
3. **Truncation**: Tracked in window.truncated flag
4. **Ordering**: Messages kept in chronological order for LLM

Example:
```python
# Conversation with 20 messages
# - 1 system message: "You are helpful"
# - 19 user/assistant messages

# With token_budget=100
window = await manager.build_context_window(
    conversation_id,
    token_budget=100
)

# Result:
# - System message always included
# - ~8-10 recent messages
# - truncated=True (more messages would exceed budget)
```

### Pagination

```python
# Get page 1 (10 messages per page, newest first)
messages, total_count = await manager.get_recent_messages(
    conversation_id,
    limit=10,
    offset=0
)
print(f"Page 1: {len(messages)}/{total_count} messages")

# Get page 2
messages, total_count = await manager.get_recent_messages(
    conversation_id,
    limit=10,
    offset=10
)
```

## Task 5.6: Context Search

### Overview

Full-text search with filtering, ranking, and relevance scoring:
- Search message content with case-insensitive matching
- Filter by date range, role, conversation, user
- Relevance ranking based on position and frequency
- Search suggestions

### Key Classes

#### SearchQuery

```python
from chatterbox.persistence.search import SearchQuery

query = SearchQuery(
    query="weather today",
    conversation_id="conv-123",
    role="assistant",  # Only assistant messages
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    limit=10,
    offset=0
)
```

#### SearchResult

```python
from chatterbox.persistence.search import SearchResult

result = SearchResult(
    message_id="msg-456",
    conversation_id="conv-123",
    content="The weather is sunny today",
    role="assistant",
    created_at=datetime.now(),
    sequence=42,
    relevance_score=0.85  # 0.0-1.0, higher is better
)

result_dict = result.to_dict()
```

#### ContextSearchEngine

```python
from chatterbox.persistence.search import ContextSearchEngine, SearchQuery

async with storage.get_session() as session:
    engine = ContextSearchEngine(session)

    # Basic search
    query = SearchQuery(query="weather")
    results, total = await engine.search(query)

    for result in results:
        print(f"[{result.relevance_score:.2f}] {result.content}")

    # Advanced search with exclusions
    results, total = await engine.advanced_search(
        query,
        exclude_queries=["rain", "snow"]  # Exclude these terms
    )

    # User-scoped search
    results, total = await engine.search_by_user(
        user_id="user-123",
        query=SearchQuery(query="weather")
    )

    # Search suggestions
    suggestions = await engine.get_search_suggestions("wea", limit=5)
    # Returns: ["weather", "wear", "weary", ...]
```

### Search Examples

```python
# Find all weather discussions
q = SearchQuery(query="weather")
results, total = await engine.search(q)

# Find recent assistant responses about weather
q = SearchQuery(
    query="weather",
    role="assistant",
    start_date=datetime.now() - timedelta(days=7)
)
results, total = await engine.search(q)

# Find user questions excluding weather
q = SearchQuery(query="question", role="user")
results, total = await engine.advanced_search(
    q,
    exclude_queries=["weather", "forecast"]
)

# Get user's messages mentioning a specific conversation
results, total = await engine.search_by_user(
    "user-123",
    SearchQuery(query="hello")
)
```

### Relevance Scoring

Results are ranked by relevance based on:
- **Position Score**: Earlier matches in message are more relevant
- **Frequency Score**: Messages with more term occurrences rank higher
- **Combined Score**: (position_score + frequency_score) / 2.0

## Task 5.7: Multi-User Isolation & Access Control

### Overview

Ensures users only access their own conversations with:
- User context with role-based permissions
- Automatic query filtering by user_id
- RBAC framework (ADMIN, USER, GUEST roles)
- Permission enforcement (READ, WRITE, DELETE, etc.)

### Key Classes

#### UserRole & Permission

```python
from chatterbox.persistence.access_control import UserRole, Permission

# Available roles
UserRole.ADMIN   # Full access
UserRole.USER    # Access own conversations only
UserRole.GUEST   # Read-only access

# Available permissions
Permission.READ          # Read messages
Permission.WRITE         # Create messages
Permission.DELETE        # Delete messages
Permission.MANAGE_USERS  # Admin only
Permission.VIEW_ALL      # Admin only
```

#### UserContext

```python
from chatterbox.persistence.access_control import UserContext, UserRole

context = UserContext(
    user_id="user-123",
    username="alice",
    role=UserRole.USER
)

# Check permissions
if context.has_permission(Permission.WRITE):
    # Can create messages
    pass

if context.is_admin():
    # Can view all conversations
    pass
```

#### AccessControlMiddleware

```python
from chatterbox.persistence.access_control import AccessControlMiddleware

async with storage.get_session() as session:
    middleware = AccessControlMiddleware(session)

    # Create user context with validation
    context = await middleware.require_user_context("user-123")

    # Get user's conversations only
    conversations = await middleware.get_user_conversations(context)

    # Access specific conversation (checks ownership)
    conv = await middleware.get_user_conversation(context, "conv-456")
    if conv is None:
        # User doesn't own this conversation
        raise PermissionError()

    # Get messages (checks READ permission)
    messages = await middleware.get_user_messages(context, "conv-456")

    # Add message (checks WRITE permission)
    msg = await middleware.add_message(
        context,
        "conv-456",
        "user",
        "Hello"
    )

    # Delete message (checks DELETE permission)
    deleted = await middleware.delete_message(context, "conv-456", "msg-789")

    # Admin-only: view statistics
    if context.is_admin():
        stats = await middleware.list_conversations_by_role(context)
```

### Example: Complete Access Control

```python
async def handle_search_request(user_id, search_query):
    async with storage.get_session() as session:
        # Create user context
        middleware = AccessControlMiddleware(session)
        context = await middleware.require_user_context(user_id)

        # Search only user's conversations
        engine = ContextSearchEngine(session)
        results, total = await engine.search_by_user(user_id, search_query)

        # Return results
        return {
            "results": [r.to_dict() for r in results],
            "total": total,
            "user_id": user_id,
            "role": context.role.value
        }
```

### Permission Model

| Role  | READ | WRITE | DELETE | MANAGE_USERS | VIEW_ALL |
|-------|------|-------|--------|--------------|----------|
| ADMIN | ✓    | ✓     | ✓      | ✓            | ✓        |
| USER  | ✓    | ✓     | ✓      | ✗            | ✗        |
| GUEST | ✓    | ✗     | ✗      | ✗            | ✗        |

## Integration Examples

### Complete Conversation Flow

```python
async def conversation_flow(user_id, user_message):
    storage = SQLiteStorage("sqlite+aiosqlite:///chatterbox.db")
    await storage.initialize()

    async with storage.get_session() as session:
        # 1. Access Control
        middleware = AccessControlMiddleware(session)
        context = await middleware.require_user_context(user_id)

        # 2. Retrieve Context
        manager = ContextManager(session)
        window = await manager.build_context_window(
            conversation_id,
            token_budget=4000
        )

        # 3. Add User Message
        msg_repo = MessageRepository(session)
        user_msg = await middleware.add_message(
            context,
            conversation_id,
            "user",
            user_message
        )

        # 4. Call LLM with context
        openai_context = window.to_openai_format()
        openai_context.append({
            "role": "user",
            "content": user_message
        })

        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=openai_context
        )

        # 5. Store Assistant Response
        assistant_msg = await middleware.add_message(
            context,
            conversation_id,
            "assistant",
            response.choices[0].message.content
        )

        # 6. Search Historical Context (if needed)
        engine = ContextSearchEngine(session)
        similar = await engine.search_by_user(
            user_id,
            SearchQuery(query=user_message)
        )

        await session.commit()

        return assistant_msg
```

### Scheduled Cleanup with Monitoring

```python
async def start_background_tasks(storage):
    # Start cleanup job
    cleanup_job = ScheduledCleanupJob(
        storage,
        policy=RetentionPolicy(message_ttl_days=30),
        interval_hours=24
    )
    await cleanup_job.start()

    # Monitor job (example)
    async def monitor_cleanup():
        while True:
            await asyncio.sleep(3600)  # Check hourly
            async with storage.get_session() as session:
                service = CleanupService(session)
                stats = await service.execute_cleanup()

                if stats.total_deleted > 0:
                    logger.info(f"Cleanup: {stats.total_deleted} items deleted")
                if stats.has_errors:
                    logger.warning(f"Cleanup errors: {stats.errors}")

    return cleanup_job
```

## Performance Characteristics

### Cleanup Service (Task 5.4)
- **Delete 1000 messages**: ~500ms
- **Empty 100 conversations**: ~200ms
- **Dry-run cost**: Same as execute, but with rollback

### Context Retrieval (Task 5.5)
- **Get last 20 messages**: <50ms
- **Build context window (4000 tokens)**: <100ms
- **Token counting (1000 characters)**: <1ms
- **Pagination (10 items/page)**: <20ms

### Search (Task 5.6)
- **Basic search (1000 messages)**: <100ms
- **Search with filters**: <150ms
- **Search suggestions**: <50ms
- **Advanced search (with exclusions)**: <200ms

### Access Control (Task 5.7)
- **Check permission**: <1ms
- **Get user conversations**: <50ms
- **Enforce access**: <5ms

## Testing

Run the comprehensive test suite:

```bash
# All context retrieval tests
pytest tests/unit/test_persistence/test_cleanup.py \
        tests/unit/test_persistence/test_context.py \
        tests/unit/test_persistence/test_search.py \
        tests/unit/test_persistence/test_access_control.py -v

# Expected: 68 tests, all passing
```

## Future Enhancements

1. **Redis Caching** (optional in Task 5.5)
   - Cache context windows in Redis
   - TTL-based invalidation

2. **Full-Text Search Index** (Task 5.6)
   - Use SQLite FTS5 for faster searches
   - Index message content at insert time

3. **Advanced RBAC** (Task 5.7)
   - Custom role creation
   - Fine-grained permissions (e.g., "read own messages only")
   - Time-based access revocation

4. **Analytics** (Epic 5 Phase 3)
   - Track search patterns
   - Measure cleanup efficiency
   - Monitor retention policy impact

## References

- [Epic 5 Context Persistence Proposal](docs/epic5-context-persistence-proposal.md)
- [Context Management Research](docs/context-management-research.md)
- [AGENTS.md](AGENTS.md) - Development workflow
- [Definition of Done](docs/definition-of-done.md)

---

Last Updated: 2026-03-25
Status: Ready for Phase 3 (LLM Framework Integration)
