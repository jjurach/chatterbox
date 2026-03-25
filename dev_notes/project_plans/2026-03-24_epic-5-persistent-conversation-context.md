# Epic 5: Persistent Conversation Context - Project Plan

**Document ID:** EPIC-5-PERSISTENCE-2026
**Epic Title:** Persistent Conversation Context with SQLite Backend
**Status:** Planned
**Target Completion:** 2026-05-12
**Estimated Duration:** 1 week (~41 hours including weather tool integration)
**Last Updated:** 2026-03-24
**Prerequisite:** Mellona integration (HIGH PRIORITY - must complete BEFORE Epic 5)
**Backend Strategy:** SQLite for Phase 1; PostgreSQL migration path for future scalability

---

## Executive Summary

Epic 5 implements persistent conversation storage and retrieval, enabling context survival across process restarts and enabling meaningful multi-turn conversations. This epic builds on the agentic framework from Epic 4 and leverages Mellona's integrated STT/TTS for rich audio context logging. The system uses SQLite as the primary backend for single-device deployments, with PostgreSQL migration capability for future scalable deployments. The system maintains isolation between users while enabling access to historical context for improved LLM responses.

**Critical Prerequisite:** Mellona integration must be completed before this epic begins. Mellona provides high-quality STT/TTS already integrated, enabling context-aware conversation persistence with audio metadata.

---

## Goals & Success Criteria

### Primary Goals
1. Store conversation history persistently across process restarts
2. Enable context retrieval for multi-turn conversations
3. Implement retention policies for automatic cleanup
4. Support user isolation and multi-user scenarios
5. Provide efficient context search for LLM queries
6. Maintain system performance with historical data

### Success Criteria
- [ ] Conversation storage backend fully operational
- [ ] Context survival verified across 3+ restarts
- [ ] Multi-turn conversation coherence maintained
- [ ] Retention policy execution verified (30-day default)
- [ ] Context search latency <200ms for typical queries
- [ ] Storage abstraction interface allows backend swapping
- [ ] Multi-user isolation enforced with no cross-contamination
- [ ] Database schema normalized and indexed
- [ ] Automatic garbage collection tested and working
- [ ] API documented with examples

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 4 (LLM Integration):** Conversation framework and LLM integration operational
- **Wyoming Protocol:** Fully functional STT/TTS pipeline

### Prerequisites
- Database system selected (SQLite for single-device, PostgreSQL for scalable)
- Python ORM library (SQLAlchemy recommended for abstraction)
- Redis optional (for caching layer)
- Storage abstraction pattern established

### Blockers to Identify
- Database performance at scale (1000+ conversations)
- Network I/O in distributed scenarios
- Storage capacity constraints

---

## Detailed Task Breakdown

### Task 5.1: Backend Evaluation & Selection
**Objective:** Confirm SQLite as Phase 1 backend with PostgreSQL migration planning
**Estimated Hours:** 4
**Strategic Decision:** SQLite for Phase 1 (single-device); PostgreSQL as Phase 2 migration path
**Acceptance Criteria:**
- [ ] SQLite selected as primary Phase 1 backend
- [ ] PostgreSQL migration path documented and designed
- [ ] Abstraction layer planned to enable backend swapping
- [ ] Performance characteristics documented
- [ ] Migration strategy including data compatibility verified

**Implementation Details:**
**Phase 1 (SQLite - This Epic):**
- Single file-based database, ideal for single device
- No external dependencies, easy deployment
- Sufficient performance for typical conversation volumes
- Migration path available via storage abstraction layer

**Phase 2 (PostgreSQL - Future Scaling):**
- Network database for distributed deployments
- Horizontal scaling capability
- Advanced features (full-text search, JSONB, etc.)
- Direct replacement via storage abstraction layer

**Storage Abstraction Pattern:**
```python
# Abstract interface allows backend swapping
class StorageBackend(ABC):
    async def create_conversation(...) -> Conversation
    async def get_conversation(...) -> Conversation
    async def search(...) -> List[Message]

class SQLiteStorage(StorageBackend):
    # SQLite implementation
class PostgreSQLStorage(StorageBackend):
    # PostgreSQL implementation
```

**Testing Plan:**
- SQLite performance baseline with realistic conversation volumes
- PostgreSQL design validation for future migration
- Storage abstraction interface testing with both backends
- Data compatibility verification

---

### Task 5.2: Storage Schema Design
**Objective:** Design normalized database schema for conversations
**Estimated Hours:** 6
**Depends On:** Task 5.1
**Acceptance Criteria:**
- [ ] Schema documented with ER diagram
- [ ] Table relationships defined
- [ ] Indexes planned for query performance
- [ ] Partitioning strategy for scalability
- [ ] Migration scripts created

**Implementation Details:**

**Core Tables:**

```sql
-- Users table
CREATE TABLE users (
  user_id UUID PRIMARY KEY,
  name VARCHAR(255),
  created_at TIMESTAMP,
  metadata JSONB -- for user preferences
);

-- Conversations table (sessions)
CREATE TABLE conversations (
  conversation_id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(user_id),
  title VARCHAR(255),
  created_at TIMESTAMP,
  last_activity TIMESTAMP,
  metadata JSONB -- model, temperature, etc.
);

-- Messages table (turns)
CREATE TABLE messages (
  message_id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(conversation_id),
  role VARCHAR(20), -- 'user', 'assistant', 'system'
  content TEXT,
  timestamp TIMESTAMP,
  tokens_used INT, -- for cost tracking
  metadata JSONB -- tools called, reasoning, etc.
);

-- Context snapshots (for efficient retrieval)
CREATE TABLE context_snapshots (
  snapshot_id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(conversation_id),
  messages_context JSONB, -- serialized context window
  created_at TIMESTAMP,
  token_count INT
);

-- Tool calls log (for auditing)
CREATE TABLE tool_calls (
  tool_call_id UUID PRIMARY KEY,
  message_id UUID REFERENCES messages(message_id),
  tool_name VARCHAR(255),
  arguments JSONB,
  result JSONB,
  timestamp TIMESTAMP
);

-- Session tokens (for API access)
CREATE TABLE session_tokens (
  token_id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(user_id),
  token_hash VARCHAR(255),
  created_at TIMESTAMP,
  expires_at TIMESTAMP,
  is_active BOOLEAN
);
```

**Indexing Strategy:**
- Index on (user_id, conversation_id) for fast retrieval
- Index on (created_at, last_activity) for retention policy
- Index on conversation_id for message lookups
- Full-text index on content for search

**Testing Plan:**
- Verify schema with migrations
- Test indexes on realistic data volume
- Validate relationships with test queries

---

### Task 5.3: SQLAlchemy ORM Models & Repository Pattern
**Objective:** Implement ORM models with clean repository interface
**Estimated Hours:** 8
**Depends On:** Task 5.2
**Acceptance Criteria:**
- [ ] All tables represented as SQLAlchemy models
- [ ] Repository pattern implemented for data access
- [ ] Connection pooling configured
- [ ] Session management thread-safe
- [ ] Models support serialization to JSON
- [ ] Lazy loading configured appropriately

**Implementation Details:**

**Model Example:**
```python
class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

    messages = relationship("Message", back_populates="conversation")
    user = relationship("User", back_populates="conversations")

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID, primary_key=True, default=uuid4)
    conversation_id = Column(UUID, ForeignKey("conversations.conversation_id"))
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tokens_used = Column(Integer)
    metadata = Column(JSON)

    conversation = relationship("Conversation", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message")
```

**Repository Interface:**
```python
class ConversationRepository:
    async def create_conversation(self, user_id: UUID, title: str) -> Conversation
    async def get_conversation(self, conversation_id: UUID) -> Conversation
    async def list_conversations(self, user_id: UUID) -> List[Conversation]
    async def update_conversation(self, conversation_id: UUID, **kwargs) -> Conversation
    async def delete_conversation(self, conversation_id: UUID) -> None

class MessageRepository:
    async def add_message(self, conversation_id: UUID, role: str, content: str) -> Message
    async def get_messages(self, conversation_id: UUID, limit: int = 50) -> List[Message]
    async def delete_old_messages(self, before: datetime) -> int
```

**Testing Plan:**
- Unit test ORM models
- Test repository CRUD operations
- Validate transactions
- Test connection pooling

---

### Task 5.4: Retention Policy Implementation
**Objective:** Implement automatic cleanup of old conversations
**Estimated Hours:** 6
**Depends On:** Task 5.3
**Acceptance Criteria:**
- [ ] Configurable retention periods (default 30 days)
- [ ] Separate policies for different data types (messages, snapshots)
- [ ] Background job runs automatically
- [ ] Cleanup execution logged
- [ ] Dry-run mode for testing
- [ ] Alert when policies need adjustment

**Implementation Details:**

**Retention Policy Configuration:**
```python
RETENTION_POLICY = {
    "conversation_history": {
        "active": 90,  # days
        "archived": 365,  # days
        "cleanup_interval": "daily"
    },
    "context_snapshots": {
        "retention": 30,  # days
        "cleanup_interval": "daily"
    },
    "tool_call_logs": {
        "retention": 30,  # days
        "cleanup_interval": "daily"
    }
}
```

**Cleanup Service:**
```python
async def cleanup_old_data():
    """Run nightly to clean up expired data"""
    before_date = datetime.utcnow() - timedelta(days=30)

    # Soft delete (archive) or hard delete based on policy
    archived = await archive_old_conversations(before_date)
    deleted = await delete_archived_conversations(before_30yr_date)

    logger.info(f"Archived {archived} conversations, deleted {deleted}")
```

**Testing Plan:**
- Test cleanup logic with various retention periods
- Verify data preservation for active items
- Test dry-run mode
- Validate cleanup scheduling

---

### Task 5.5: Context Window & Message Retrieval
**Objective:** Implement efficient context retrieval for LLM
**Estimated Hours:** 6
**Depends On:** Task 5.3
**Acceptance Criteria:**
- [ ] Retrieve last N messages with latency <200ms
- [ ] Context window composing working correctly
- [ ] Token counting for context size
- [ ] Efficient pagination for large conversations
- [ ] Caching layer optional (Redis)
- [ ] Context integrity verified

**Implementation Details:**

**Context Retrieval Service:**
```python
async def get_conversation_context(
    conversation_id: UUID,
    max_tokens: int = 2000,
    include_system: bool = True
) -> List[Message]:
    """
    Retrieve conversation context up to token limit.
    Most recent messages first (tail of conversation).
    """
    messages = []
    total_tokens = 0

    # Get messages in reverse chronological order
    all_messages = await message_repo.get_messages(
        conversation_id,
        limit=None  # Get all
    )

    # Build context from most recent backwards
    for msg in reversed(all_messages):
        msg_tokens = estimate_tokens(msg.content)
        if total_tokens + msg_tokens > max_tokens:
            break
        messages.insert(0, msg)
        total_tokens += msg_tokens

    return messages

def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    return len(text) // 4  # Typical: 1 token ≈ 4 chars
```

**Context Snapshot (for optimization):**
```python
async def save_context_snapshot(conversation_id: UUID):
    """Periodically save serialized context for faster retrieval"""
    messages = await get_conversation_context(conversation_id)
    snapshot = {
        "messages": [msg.to_dict() for msg in messages],
        "timestamp": datetime.utcnow(),
        "token_count": sum(estimate_tokens(m.content) for m in messages)
    }
    await context_snapshot_repo.create(conversation_id, snapshot)
```

**Testing Plan:**
- Test context retrieval latency
- Verify token counting accuracy
- Test with conversations of various sizes
- Validate caching effectiveness (if used)

---

### Task 5.6: Context Search & Query Interface
**Objective:** Implement search for historical context
**Estimated Hours:** 6
**Depends On:** Task 5.3
**Acceptance Criteria:**
- [ ] Full-text search on message content
- [ ] Filter by date range, role, conversation
- [ ] Search results ranked by relevance
- [ ] Search latency <500ms typical case
- [ ] Search API documented
- [ ] Example queries documented

**Implementation Details:**

**Search Interface:**
```python
async def search_context(
    user_id: UUID,
    query: str,
    filters: Optional[SearchFilters] = None,
    limit: int = 50
) -> List[SearchResult]:
    """
    Full-text search across user's conversations.

    Filters:
    - conversation_id: specific conversation
    - date_from, date_to: time range
    - role: filter by user/assistant
    """

    # Use database full-text search or external engine
    results = await db.search(
        "SELECT * FROM messages WHERE "
        "user_id = ? AND content @@ ? "
        "ORDER BY ts_rank(...) DESC LIMIT ?",
        (user_id, query, limit)
    )

    return [SearchResult.from_db(r) for r in results]
```

**Search Filters:**
```python
@dataclass
class SearchFilters:
    conversation_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    role: Optional[str] = None  # 'user', 'assistant'
    tool_name: Optional[str] = None
```

**Testing Plan:**
- Test search accuracy with known queries
- Verify ranking quality
- Test filter combinations
- Load test search with large datasets

---

### Task 5.7: Multi-User Isolation & Access Control
**Objective:** Ensure data isolation between users
**Estimated Hours:** 5
**Depends On:** Task 5.3
**Acceptance Criteria:**
- [ ] Users can only access their conversations
- [ ] No cross-user data leakage
- [ ] Queries filtered by user_id automatically
- [ ] Access control tested in integration
- [ ] RBAC framework for future (admin, user roles)

**Implementation Details:**

**User Context Middleware:**
```python
class UserContextMiddleware:
    """Automatically filter queries by current user"""

    async def __call__(self, request, call_next):
        # Extract user from auth token
        user_id = await get_user_from_token(request)
        request.state.user_id = user_id
        return await call_next(request)
```

**Repository Pattern with User Filtering:**
```python
async def get_conversation(
    conversation_id: UUID,
    user_id: UUID  # Always required
) -> Conversation:
    """Fetch conversation, verifying ownership"""
    conv = await db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user_id  # Crucial filter
    ).first()

    if not conv:
        raise NotFoundError("Conversation not found")

    return conv
```

**Testing Plan:**
- Test accessing conversations with different user IDs
- Verify 403 errors for unauthorized access
- Test with multiple users simultaneously
- Validate query filtering

---

### Task 5.8: Storage Abstraction Layer
**Objective:** Create interface allowing backend swapping
**Estimated Hours:** 4
**Depends On:** Tasks 5.1, 5.3
**Acceptance Criteria:**
- [ ] Storage interface defined (abstract base class)
- [ ] SQLite implementation complete
- [ ] PostgreSQL implementation complete
- [ ] Mock implementation for testing
- [ ] Easy switching between backends
- [ ] Implementations tested equivalently

**Implementation Details:**

**Abstract Interface:**
```python
class StorageBackend(ABC):
    """Abstract storage backend interface"""

    @abstractmethod
    async def create_conversation(self, user_id: UUID, title: str) -> Conversation:
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        pass

    @abstractmethod
    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        pass

    @abstractmethod
    async def search(self, query: str, filters: SearchFilters) -> List[Message]:
        pass

class SQLiteStorage(StorageBackend):
    """SQLite implementation (single-device)"""

    async def create_conversation(self, user_id: UUID, title: str) -> Conversation:
        # SQLite implementation

class PostgreSQLStorage(StorageBackend):
    """PostgreSQL implementation (scalable)"""

    async def create_conversation(self, user_id: UUID, title: str) -> Conversation:
        # PostgreSQL implementation
```

**Configuration:**
```python
# Choose backend at startup
if settings.DATABASE_URL.startswith("sqlite"):
    storage = SQLiteStorage()
elif settings.DATABASE_URL.startswith("postgresql"):
    storage = PostgreSQLStorage()
```

**Testing Plan:**
- Test each implementation with identical test suite
- Test backend switching
- Validate data format consistency

---

### Task 5.9: Integration with LLM Framework
**Objective:** Integrate context persistence with Epic 4 LLM system
**Estimated Hours:** 6
**Depends On:** Tasks 5.5, 5.7
**Acceptance Criteria:**
- [ ] Context automatically loaded for conversations
- [ ] LLM receives persisted context correctly
- [ ] New messages stored after LLM response
- [ ] Tool calls logged and associated
- [ ] Tokens tracked for cost analysis
- [ ] Integration tested end-to-end

**Implementation Details:**

**Conversation Handler:**
```python
class ConversationManager:
    def __init__(self, storage: StorageBackend, llm_engine: LLMEngine):
        self.storage = storage
        self.llm = llm_engine

    async def process_conversation(
        self,
        conversation_id: UUID,
        user_message: str,
        user_id: UUID
    ) -> str:
        # Load context
        messages = await self.storage.get_messages(conversation_id)
        context = self._build_context(messages)

        # Store user message
        await self.storage.add_message(
            conversation_id,
            role="user",
            content=user_message
        )

        # Get LLM response
        response, tool_calls = await self.llm.process(
            context=context,
            user_message=user_message
        )

        # Store assistant response
        await self.storage.add_message(
            conversation_id,
            role="assistant",
            content=response,
            metadata={"tool_calls": tool_calls}
        )

        # Store tool calls
        for call in tool_calls:
            await self.storage.log_tool_call(call)

        return response

    def _build_context(self, messages: List[Message]) -> List[dict]:
        """Convert stored messages to LLM format"""
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
```

**Testing Plan:**
- Test context loading and building
- Test message storage after responses
- Test tool call logging
- End-to-end conversation flow

---

### Task 5.10: Testing & Validation
**Objective:** Comprehensive testing of persistence system
**Estimated Hours:** 8
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Unit tests for all components with mocked providers (>90% coverage)
- [ ] Unit tests for weather tool with mocked Open-Meteo API
- [ ] Unit tests for LLM interactions with mocked mellona provider
- [ ] Integration tests for full workflows with real tools
- [ ] Integration tests for live weather tool responses (multiple locations)
- [ ] Integration tests for multi-turn weather conversations
- [ ] Data integrity tests (no loss, no corruption)
- [ ] Performance tests (latency requirements met)
- [ ] Multi-user isolation verified
- [ ] Retention policy verified
- [ ] Tool call logging verified
- [ ] Weather results persisted in conversation history

**Implementation Details:**

**Test Categories:**

1. **Unit Tests:**
   - ORM model functionality
   - Repository CRUD operations
   - Search query building
   - Token estimation
   - **Tool interaction with mocked providers:**
     - Weather tool with mocked Open-Meteo API responses
     - LLM model calls with mocked mellona provider
     - Tool call parameter validation
     - Error handling for tool failures

2. **Integration Tests:**
   - Full conversation flow (store/retrieve/search)
   - Multi-turn conversation coherence
   - User isolation
   - Cleanup policy execution
   - **Live weather tool integration:**
     - Real weather query: "What's the weather in Kansas City?"
     - Verify tool response stored in message history with:
       - Original user message
       - Tool call (get_weather, location)
       - Tool result (temperature, conditions, humidity, wind)
       - Assistant response referencing weather data
     - Multiple location queries (city, city+state, city+country)
     - Invalid location error handling
     - Tool result persistence across restarts

3. **Tool-Agent Integration Tests:**
   - Agent processes weather query with real LLM response
   - LLM includes weather context in follow-up messages
   - Tool calls appear in conversation history with timestamps
   - Multi-turn conversation with weather references:
     - User: "What's the weather in London?"
     - Agent calls weather tool, gets result
     - User: "What about Paris?"
     - Agent references both results in conversation

4. **Performance Tests:**
   - Retrieval latency <200ms
   - Search latency <500ms
   - Write throughput (100+ msgs/sec)
   - Memory footprint under load
   - Weather API latency (typical <5s round-trip)

5. **Data Integrity Tests:**
   - No data loss on restart
   - Transactions working correctly
   - Concurrent access handled properly
   - Orphaned records cleanup
   - Tool result data consistency across database backends

**Test Fixtures:**
- Sample conversations (5-50 messages each)
- Multiple user scenarios
- Large dataset for performance testing (10K+ messages)
- **Weather tool test data:**
  - Mock Open-Meteo responses for various locations
  - Mock mellona LLM provider responses
  - Real weather queries for integration tests

**Mocking Strategy:**
```python
# Unit tests: Mock the weather tool provider
@pytest.fixture
def mock_weather_tool():
    """Mock mellona's weather tool for unit testing"""
    with patch('mellona.tools.weather.WeatherTool.get_weather') as mock:
        mock.return_value = {
            "location_name": "Kansas City, Missouri, United States",
            "temperature_c": 22.0,
            "temperature_f": 72.0,
            "conditions": "Partly cloudy",
            "humidity_percent": 65,
            "wind_speed_kmh": 12.5,
            "wind_speed_mph": 7.8
        }
        yield mock

# Unit tests: Mock the LLM provider
@pytest.fixture
def mock_llm_provider():
    """Mock mellona's LLM provider for unit testing"""
    with patch('mellona.MellonaClient.call') as mock:
        mock.return_value = LLMResponse(
            text="It's currently 72°F and partly cloudy in Kansas City with 65% humidity.",
            tokens_used=15,
            model="llama-pro:latest"
        )
        yield mock

# Integration tests: Use real providers (requires mellona setup)
@pytest.fixture(scope="session")
def mellona_client():
    """Real mellona client for integration tests"""
    from mellona import MellonaClient
    return MellonaClient()
```

**Testing Plan:**
- Execute unit test suite with >95% pass rate (mocked providers)
- Execute integration test suite with >90% pass rate (real/live tools)
- Load test with production-like data volumes
- Chaos testing (kill process, network failure, tool timeout)
- Multi-user concurrent testing with weather queries
- Weather tool timeout handling (>5s response)

---

### Task 5.11: API Documentation & Examples
**Objective:** Document persistence API and usage patterns
**Estimated Hours:** 4
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] API reference complete
- [ ] Usage examples for common patterns
- [ ] Schema documentation
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Example clients provided

**Implementation Details:**

**Documentation Structure:**
1. Overview and concepts
2. API reference (methods, parameters, return values)
3. Data schema documentation
4. Configuration options
5. Usage examples:
   - Creating conversations
   - Storing messages
   - Retrieving context
   - Searching history
   - Managing retention
6. Troubleshooting common issues

**Example: Retrieving Context for Conversation**
```python
# Get most recent context
storage = PostgreSQLStorage(connection_url)
messages = await storage.get_messages(
    conversation_id,
    limit=50  # Last 50 messages
)

# Use in LLM
context = [{"role": m.role, "content": m.content} for m in messages]
response = await llm.generate(context)

# Store new message
await storage.add_message(conversation_id, "assistant", response)
```

**Testing Plan:**
- Validate all examples compile and run
- Test example output matches expectations
- Have new user follow examples

---

### Task 5.11b: Mellona Weather Tool Integration
**Objective:** Integrate mellona's weather tool into the agent system
**Estimated Hours:** 3
**Depends On:** Task 5.1 (Storage backend selected)
**Acceptance Criteria:**
- [ ] Weather tool imported from mellona
- [ ] Tool registered in chatterbox tool registry
- [ ] Weather queries stored in conversation history
- [ ] Test: Agent can answer "What's the weather in [location]?"
- [ ] Tool calls logged with location and result
- [ ] Documentation: how to use weather tool in conversations

**Implementation Details:**

**Add to Tool Registry:**
```python
# In src/chatterbox/tools/registry.py
from mellona.tools.weather import WeatherTool

def get_available_tools() -> List[Tool]:
    tools = [
        # ... existing tools ...
        WeatherTool.TOOL_DEFINITION,  # Add weather tool
    ]
    return tools
```

**Weather Tool Usage:**
```python
# Tool enables queries like:
# "What's the weather in Kansas City?"
# "Tell me the temperature in Paris, France"
# "Is it raining in London?"

# Tool returns:
# - location_name (resolved)
# - temperature_c, temperature_f
# - conditions (Clear, Cloudy, Rainy, etc.)
# - humidity_percent
# - wind_speed_kmh, wind_speed_mph
```

**Message Storage:**
- User message: "What's the weather in Kansas City?"
- Tool call logged: {tool: "get_weather", location: "Kansas City"}
- Tool result stored: {temperature_f: 72, conditions: "Partly cloudy", ...}
- Assistant message: "It's currently 72°F and partly cloudy in Kansas City..."

**Testing Plan:**
- Test weather query with known locations
- Verify results are stored in conversation history
- Test with various location formats (City, City State, City Country)
- Verify tool error handling for invalid locations
- Test conversation context includes weather results

---

### Task 5.12: Deployment & Migration
**Objective:** Prepare for production deployment
**Estimated Hours:** 4
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Migration scripts created
- [ ] Backward compatibility verified
- [ ] Rollback procedures documented
- [ ] Performance benchmarked
- [ ] Security review completed
- [ ] Deployment guide created

**Implementation Details:**

**Migration Strategy:**
1. Create backup of existing data
2. Run schema migrations
3. Populate new tables
4. Verify data integrity
5. Update application code
6. Monitor for issues

**Rollback Procedure:**
- Keep backup of previous version
- Document steps to revert
- Test rollback procedure

**Performance Baseline:**
- Message retrieval: <200ms
- Search: <500ms
- Context building: <100ms

**Testing Plan:**
- Test migrations on production-like data
- Verify rollback works
- Test performance in production environment

---

## Technical Implementation Details

### Architecture Overview

```
┌─────────────────────────────────────────┐
│         LLM Framework (Epic 4)          │
│    ┌───────────────────────────────┐    │
│    │  Conversation Management      │    │
│    └──────────────┬────────────────┘    │
│                   │                      │
└───────────────────┼──────────────────────┘
                    │ Uses
        ┌───────────▼──────────────┐
        │ Persistence Layer        │
        │ ┌──────────────────────┐ │
        │ │ Storage Abstraction  │ │
        │ │ Interface            │ │
        │ └──────────────────────┘ │
        │          ▲               │
        │          │               │
        │ ┌────────┴─────────────┐ │
        │ │                      │ │
        │ ▼                      ▼ │
        │ SQLite          PostgreSQL│
        │ (dev/single)    (prod)    │
        └─────────────────────────┘
           │                │
           │                │
    ┌──────▼─┐    ┌────────▼──────┐
    │Local   │    │Remote DB      │
    │SQLite  │    │PostgreSQL+    │
    │DB      │    │Redis Cache    │
    └────────┘    └───────────────┘
```

### Data Models

**Conversation:**
- Unique identifier (UUID)
- User ownership (user_id)
- Metadata (model, parameters)
- Timestamps (created, last_activity)

**Message:**
- Unique identifier (UUID)
- Parent conversation reference
- Role (user/assistant/system)
- Content (text)
- Token count for cost tracking
- Metadata (tool calls, reasoning)

**Context Snapshot:**
- Serialized message history
- Token count
- Timestamp
- Used for optimization

### Search Implementation

**Options:**
1. PostgreSQL full-text search (native)
2. Elasticsearch (external, more powerful)
3. SQLite FTS module (simple)

**Recommended:** PostgreSQL FTS for single-node, Elasticsearch for scale

---

## Testing Plan

### Unit Tests
- Message/Conversation CRUD operations
- Token counting accuracy
- Retention policy calculations
- Search query building

### Integration Tests
- Full conversation lifecycle
- Context retrieval and building
- Multi-turn coherence
- User isolation verification

### System Tests
- 24-hour stability
- Large dataset performance (100K+ messages)
- Concurrent user access
- Cleanup policy execution

### Acceptance Tests
- Context survives restart
- LLM has access to history
- Search works accurately
- Multi-user isolation enforced

---

## Estimated Timeline

**Day 1 (8 hours):**
- Task 5.1: Backend evaluation (4 hrs)
- Task 5.2: Schema design (4 hrs)

**Day 2 (8 hours):**
- Task 5.3: ORM models & repository (8 hrs)

**Day 3 (8 hours):**
- Task 5.4: Retention policy (6 hrs)
- Task 5.5: Context retrieval (2 hrs - carried over)

**Day 4 (8 hours):**
- Task 5.5: Context retrieval (4 hrs - continued)
- Task 5.6: Search interface (4 hrs)

**Day 5 (6 hours):**
- Task 5.7: Multi-user isolation (5 hrs)
- Task 5.8: Storage abstraction (1 hr - carried over)

**Day 5+ (9 hours):**
- Task 5.8: Storage abstraction (3 hrs)
- Task 5.9: LLM integration (6 hrs)
- Task 5.11b: Weather tool integration (3 hrs - parallel with 5.9)

**Final days (8 hours):**
- Task 5.10: Testing (8 hrs)
- Task 5.11: API Documentation (4 hrs)
- Task 5.12: Deployment (4 hrs)

**Total: ~41 hours (~1 week at 40 hrs/week, includes weather tool)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Database scaling issues | Medium | High | Performance test early; plan sharding strategy |
| Data loss on migration | Low | Critical | Backup first; test migration on copy; rollback plan |
| Search performance degradation | Medium | Medium | Implement indexes; consider Elasticsearch |
| Token counting inaccuracy | Low | Low | Use tokenizer library; validate against actual |
| Multi-user data leakage | Low | Critical | Code review; automated isolation tests |
| Context window token overflow | Low | Medium | Implement sliding window; token budget checks |
| Retention policy breaking changes | Low | Medium | Test retention extensively; gradual rollout |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Conversations persist across restarts
- [ ] Context retrieval works for LLM
- [ ] Search finds relevant historical context
- [ ] Multiple users can use system simultaneously
- [ ] Retention policy automatically cleans old data
- [ ] Token counting accurate for cost tracking

### Performance
- [ ] Context retrieval <200ms
- [ ] Search <500ms
- [ ] Storage write <50ms
- [ ] Can handle 1000+ messages per conversation

### Reliability
- [ ] No data loss in normal operation
- [ ] Graceful degradation if DB unavailable
- [ ] Migration path from non-persistent to persistent
- [ ] Backup/restore procedures documented

### Security
- [ ] User data isolated from other users
- [ ] No SQL injection vulnerabilities
- [ ] Authentication required for access
- [ ] Data encrypted in transit

### Usability
- [ ] API clear and intuitive
- [ ] Documentation complete with examples
- [ ] Configuration straightforward
- [ ] Easy to switch backends

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic enables persistent context storage as outlined in Phase 3 (Enhancement). It directly enables multi-turn conversations and provides the foundation for advanced context-aware features in subsequent epics.

**Dependencies Met by Previous Epics:**
- Epic 4: Conversation framework and LLM integration operational
- Epics 1-3: Infrastructure, Wyoming protocol, basic communication

**Enables Next Epics:**
- Epic 6: Backend deployment with persistent context
- Epic 8+: Advanced tools and features requiring historical context
- Epic 11: Cost tracking and analytics requiring message history

---

## Approval & Sign-Off

**Epic Owner:** [To be assigned]
**Technical Lead:** [To be assigned]
**Database Architect:** [To be assigned]

**Approved By:**
- [ ] Epic Owner
- [ ] Technical Lead
- [ ] Database Architect

**Approved Date:** _______________

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-05-12 (Epic 4 completion + 2 weeks)
