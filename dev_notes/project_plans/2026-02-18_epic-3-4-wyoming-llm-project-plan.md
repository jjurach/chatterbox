# Epic 3 & 4: Wyoming Protocol and LLM Integration - Project Plan

**Status:** In Planning
**Created:** 2026-02-18
**Specification:** dev_notes/specs/spec-wyoming-protocol-llm-integration-20260218.md

## Epic Overview

These two epics establish the Wyoming protocol foundation (Epic 3) and build LLM-based conversational capabilities (Epic 4) for the Chatterbox voice assistant.

**Epic 3 Scope:** Wyoming Protocol Implementation and Validation
**Epic 4 Scope:** LLM Integration with Tool Calling (depends on Epic 3)
**Target Platform:** Home Assistant voice satellite integration
**Timeline:** Epic 3 must complete before Epic 4 begins

---

# Epic 3: Wyoming Protocol Implementation and Validation

## Epic 3 Overview

Validate that all necessary components are in place for Chatterbox backends to implement Wyoming protocol features required by Home Assistant. Establish comprehensive testing infrastructure to emulate Home Assistant interactions.

**Key Technologies:**
- Wyoming protocol (Home Assistant's voice satellite standard)
- Whisper (speech-to-text)
- Piper (text-to-speech)
- PCM audio streaming

## Epic 3 Goals & Acceptance Criteria

### Goal 1: Wyoming Protocol Research and Documentation
**Status:** Completed (2026-02-19)

Complete understanding of Wyoming protocol and actual conversation flows with Home Assistant.

**Acceptance Criteria:**
- [x] Wyoming protocol specification thoroughly documented
- [x] Actual conversation flows between Home Assistant and Wyoming services mapped
- [x] All protocol endpoints and expected behaviors documented
- [x] Message formats and PCM packet specifications documented
- [x] Integration patterns for STT, TTS, and assist services documented
- [ ] Protocol flow diagrams created (ASCII diagrams in docs; formal diagrams deferred)
- [x] Validation of protocol assumptions completed

### Goal 2: Home Assistant Emulator Implementation
**Status:** Not Started

Create an emulator that simulates Home Assistant's interactions with Chatterbox backends.

**Acceptance Criteria:**
- [ ] Emulator can generate PCM audio streams from wave files
- [ ] Emulator transmits PCM packets to Wyoming protocol endpoints
- [ ] Emulator receives and validates text responses
- [ ] Emulator receives and validates audio stream responses
- [ ] Emulator validates integrity and correctness of data transmission
- [ ] Support for 10-15 test wave files
- [ ] Automated test execution capability

### Goal 3: Test Wave File Corpus
**Status:** Not Started

Create standardized test inputs for repeatable validation.

**Acceptance Criteria:**
- [ ] 10-15 wave files generated with varied content
- [ ] Files contain sample statements and questions
- [ ] Files generated using Piper or similar TTS
- [ ] Files stored in source tree for version control
- [ ] Test corpus documented with expected transcriptions
- [ ] Wave files cover edge cases (short/long utterances, different voices, etc.)

### Goal 4: Speech-to-Text Service Validation
**Status:** Not Started

Validate Whisper-based STT endpoint via Wyoming protocol.

**Acceptance Criteria:**
- [ ] Chatterbox Whisper service accepts Wyoming protocol PCM streams
- [ ] Service correctly transcribes audio to text
- [ ] Text responses properly formatted per Wyoming protocol
- [ ] Transcription accuracy validated against known test inputs
- [ ] Service handles protocol handshake correctly
- [ ] Error handling for malformed audio streams
- [ ] Performance meets latency requirements (<2s for typical utterance)

**Flow Validation:**
1. Hardware wake word triggers audio capture on Box 3B
2. PCM audio stream transmitted to Home Assistant
3. Home Assistant relays stream to Chatterbox Whisper via Wyoming
4. Chatterbox transcribes audio to text
5. Text response returned through protocol chain

### Goal 5: Text-to-Speech Service Validation
**Status:** Not Started

Validate Piper-based TTS endpoint via Wyoming protocol.

**Acceptance Criteria:**
- [ ] Chatterbox Piper service accepts Wyoming protocol text requests
- [ ] Service generates PCM audio streams
- [ ] Audio streams properly formatted per Wyoming protocol
- [ ] Emulator can capture and save output as wave files
- [ ] Audio quality validated (clarity, no artifacts)
- [ ] Service handles protocol handshake correctly
- [ ] Error handling for malformed text inputs
- [ ] Performance meets latency requirements (<1s for typical response)

**Flow Validation:**
1. Home Assistant sends text to Chatterbox via Wyoming
2. Chatterbox invokes Piper TTS service
3. PCM audio stream generated and transmitted back
4. Home Assistant relays to Box 3B for playback

### Goal 6: Integration Testing Infrastructure
**Status:** Not Started

Establish automated testing framework for Wyoming protocol.

**Acceptance Criteria:**
- [ ] Script to generate wave files from text statements
- [ ] Automated test suite for all Wyoming endpoints
- [ ] Round-trip testing (text → TTS → STT → text validation)
- [ ] Error handling and edge case coverage
- [ ] Performance and latency measurements
- [ ] Automated validation reports
- [ ] CI/CD integration capability

## Epic 3 Task Breakdown

### Task 3.1: Research Wyoming Protocol Specification
**Priority:** P0 (Critical - blocks all other tasks)
**Owner:** TBD
**Depends On:** None
**Estimated Effort:** 8 hours

Deep dive into Wyoming protocol to understand actual implementation requirements.

**Subtasks:**
- Read Wyoming protocol specification documentation
- Study Home Assistant voice satellite integration code
- Analyze existing Wyoming service implementations (reference code)
- Document protocol handshake sequences
- Document PCM audio format requirements
- Document text message formats
- Identify protocol version compatibility requirements
- Map conversation flows for STT and TTS scenarios
- Create protocol flow diagrams

**Deliverables:**
- Wyoming protocol documentation (markdown in docs/)
- Protocol flow diagrams
- Message format specifications
- Integration patterns document

**Definition of Done:**
- Complete protocol documentation created
- All conversation flows mapped and validated
- Team has clear understanding of implementation requirements
- No ambiguities remain about protocol behavior

---

### Task 3.2: Design Home Assistant Emulator Architecture
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 3.1
**Estimated Effort:** 6 hours

Design the architecture for the Home Assistant emulator before implementation.

**Subtasks:**
- Define emulator component architecture
- Design wave file loading and PCM streaming mechanism
- Design Wyoming protocol client implementation
- Design response validation framework
- Define test execution and reporting interfaces
- Create architecture diagrams
- Document testing approach

**Deliverables:**
- Emulator architecture document
- Component diagrams
- Interface specifications
- Testing strategy document

**Definition of Done:**
- Architecture reviewed and approved
- All components clearly defined
- Testing strategy documented
- Ready for implementation

---

### Task 3.3: Create Test Wave File Corpus
**Priority:** P1 (High - needed for testing)
**Owner:** TBD
**Depends On:** Task 3.1
**Estimated Effort:** 4 hours

Generate standardized test wave files for repeatable testing.

**Subtasks:**
- Define test utterances covering various scenarios:
  - Simple commands ("Turn on the lights")
  - Questions ("What is the weather in Kansas?")
  - Short utterances (1-2 words)
  - Long utterances (full sentences)
  - Different speaking styles
- Generate 10-15 wave files using Piper TTS
- Document expected transcriptions for each file
- Store files in source tree (tests/corpus/ or similar)
- Create metadata file with transcription expectations
- Verify files are loadable and playable

**Technical Details:**
- Use Piper with appropriate voice model
- 16kHz sample rate (typical for Whisper)
- PCM format compatible with Wyoming protocol
- File naming convention: `test_001_turn_on_lights.wav`

**Deliverables:**
- 10-15 wave files in source tree
- Metadata file with expected transcriptions
- Documentation on corpus usage

**Definition of Done:**
- All wave files generated and stored
- Expected transcriptions documented
- Files verified playable and parseable
- Metadata file created

---

### Task 3.4: Implement Home Assistant Emulator Core
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 3.2, Task 3.3
**Estimated Effort:** 12 hours

Implement the core Home Assistant emulator functionality.

**Subtasks:**
- Create Python project structure for emulator
- Implement wave file loader
- Implement PCM audio stream generator
- Implement Wyoming protocol client
- Implement protocol handshake logic
- Implement audio streaming to STT endpoint
- Implement text sending to TTS endpoint
- Implement response receiver (text and audio)
- Add basic logging and debugging output

**Technical Details:**
- Language: Python 3.8+
- Wyoming protocol client library (if available) or custom implementation
- Wave file handling: `wave` module or `soundfile`
- Network: asyncio for protocol communication
- Logging: structured logging for debugging

**Deliverables:**
- Python emulator implementation
- Basic CLI interface for running tests
- Unit tests for core components

**Definition of Done:**
- Emulator can load wave files
- Emulator can send PCM streams via Wyoming protocol
- Emulator can send text via Wyoming protocol
- Emulator can receive and log responses
- Code has basic unit test coverage

---

### Task 3.5: Implement Emulator Validation Framework
**Priority:** P1 (High)
**Owner:** TBD
**Depends On:** Task 3.4
**Estimated Effort:** 8 hours

Add validation and reporting capabilities to the emulator.

**Subtasks:**
- Implement text transcription validator (compare expected vs actual)
- Implement audio stream validator (can save to wave file)
- Implement integrity checks for received data
- Create test result reporting system
- Add confidence scoring for validations
- Implement automated test runner
- Create summary reports with pass/fail statistics

**Technical Details:**
- Validation logic: string comparison with tolerance for minor variations
- Audio validation: save received PCM to temporary wave files
- Reporting: JSON output and human-readable summaries
- Test runner: iterate through corpus and aggregate results

**Deliverables:**
- Validation framework implementation
- Automated test runner
- Report generation system

**Definition of Done:**
- Can validate text transcriptions against expected
- Can save received audio as wave files
- Can run full test suite automatically
- Generates clear pass/fail reports

---

### Task 3.6: Validate Whisper STT Service
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 3.5
**Estimated Effort:** 6 hours

Use emulator to validate Whisper-based STT service via Wyoming protocol.

**Subtasks:**
- Configure Chatterbox Whisper service for Wyoming protocol
- Run emulator against STT endpoint with test corpus
- Analyze transcription accuracy
- Debug any protocol issues
- Tune Whisper parameters if needed
- Document any protocol quirks or issues
- Verify performance and latency
- Test error handling (invalid audio, connection failures)

**Test Scenarios:**
- All 10-15 wave files from corpus
- Edge cases: empty audio, very short audio, very long audio
- Protocol error scenarios: malformed requests, connection drops
- Performance: measure end-to-end latency

**Deliverables:**
- STT validation test results
- Performance measurements
- Documentation of any issues or configuration changes
- Updated emulator if protocol issues discovered

**Definition of Done:**
- All test wave files transcribed successfully
- Transcription accuracy meets requirements (>90% word accuracy)
- Latency within acceptable range (<2s per file)
- Error handling validated
- Documentation complete

---

### Task 3.7: Validate Piper TTS Service
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 3.5
**Estimated Effort:** 6 hours

Use emulator to validate Piper-based TTS service via Wyoming protocol.

**Subtasks:**
- Configure Chatterbox Piper service for Wyoming protocol
- Create test text corpus (can reuse expected transcriptions)
- Run emulator against TTS endpoint with test inputs
- Capture and save output wave files
- Manually verify audio quality (listen to samples)
- Verify PCM stream format correctness
- Document any protocol quirks or issues
- Verify performance and latency
- Test error handling (invalid text, connection failures)

**Test Scenarios:**
- Various text inputs (short, long, special characters)
- Edge cases: empty text, very long text
- Protocol error scenarios: malformed requests, connection drops
- Performance: measure end-to-end latency

**Deliverables:**
- TTS validation test results
- Sample output wave files
- Performance measurements
- Documentation of any issues or configuration changes

**Definition of Done:**
- All test texts successfully converted to audio
- Audio quality acceptable (clear, no artifacts)
- Latency within acceptable range (<1s per response)
- Error handling validated
- Documentation complete

---

### Task 3.8: Round-Trip Integration Testing
**Priority:** P1 (High)
**Owner:** TBD
**Depends On:** Task 3.6, Task 3.7
**Estimated Effort:** 6 hours

Validate full round-trip conversation flows through Wyoming protocol.

**Subtasks:**
- Create round-trip test: wave file → STT → TTS → wave file
- Validate text accuracy through the pipeline
- Validate audio quality after round-trip
- Test multi-turn conversation scenarios (if applicable)
- Measure end-to-end latency for full conversation
- Test concurrent requests (multiple parallel conversations)
- Document full conversation flows
- Create integration test suite

**Test Scenarios:**
- Single round-trip: audio in → text → audio out
- Text comparison: original transcription vs final output text
- Performance: total latency for full cycle
- Concurrency: multiple simultaneous requests

**Deliverables:**
- Round-trip integration test suite
- End-to-end performance measurements
- Full conversation flow documentation
- Test results and validation reports

**Definition of Done:**
- Round-trip tests pass with acceptable accuracy
- End-to-end latency measured and documented
- Concurrent request handling validated
- Integration test suite automated and repeatable

---

### Task 3.9: Create Epic 3 Documentation Package
**Priority:** P2 (Medium)
**Owner:** TBD
**Depends On:** Task 3.6, Task 3.7, Task 3.8
**Estimated Effort:** 4 hours

Consolidate all Epic 3 documentation and create comprehensive guide.

**Subtasks:**
- Consolidate Wyoming protocol documentation
- Document emulator usage and architecture
- Create testing guide (how to run tests, interpret results)
- Document STT and TTS service configurations
- Create troubleshooting guide
- Document known issues and workarounds
- Create README for test corpus
- Add code comments and docstrings

**Deliverables:**
- docs/wyoming-protocol.md (protocol documentation)
- docs/testing-infrastructure.md (emulator and testing guide)
- tests/corpus/README.md (test data documentation)
- Code documentation (docstrings, comments)

**Definition of Done:**
- All documentation complete and reviewed
- New team members can understand and use the system
- Testing guide enables others to run tests
- Known issues documented with workarounds

---

### Task 3.10: Epic 3 Sign-Off and Validation
**Priority:** P0 (Critical - Epic completion)
**Owner:** TBD
**Depends On:** All Epic 3 tasks
**Estimated Effort:** 4 hours

Final validation that all Epic 3 acceptance criteria are met.

**Subtasks:**
- Review all Epic 3 acceptance criteria
- Run complete test suite and verify all pass
- Verify all documentation is complete
- Conduct final code review
- Create Epic 3 completion report
- Tag release/milestone in version control
- Prepare handoff to Epic 4 team

**Validation Checklist:**
- [ ] Wyoming protocol fully documented
- [ ] Home Assistant emulator functional
- [ ] Test corpus complete (10-15 wave files)
- [ ] All protocol endpoints validated
- [ ] STT service confirmed working
- [ ] TTS service confirmed working
- [ ] Integration tests passing
- [ ] Performance requirements met
- [ ] Documentation complete

**Deliverables:**
- Epic 3 completion report
- Final test results
- Version control tag/release
- Epic 4 readiness confirmation

**Definition of Done:**
- All Epic 3 acceptance criteria met
- All tests passing
- Documentation reviewed and approved
- Epic 3 bead closed
- Epic 4 unblocked and ready to begin

---

# Epic 4: LLM Integration with Tool Calling

## Epic 4 Overview

Implement a stateful, agentic conversation loop that enables Chatterbox to process natural language queries, invoke tools as needed, and generate contextually appropriate responses. This epic builds on Epic 3's Wyoming protocol foundation.

**Key Technologies:**
- LangGraph or similar agentic framework
- LLM (Claude, GPT, or other)
- Tool calling architecture
- State machine for conversation management

**Dependency:** Epic 4 cannot begin until Epic 3 is complete.

## Epic 4 Goals & Acceptance Criteria

### Goal 1: Protocol Flow Clarification
**Status:** Not Started

Determine the exact conversation pattern used by Home Assistant.

**Acceptance Criteria:**
- [ ] Home Assistant conversation flow documented
- [ ] Determine if multi-endpoint or single-endpoint pattern
- [ ] Document where LLM integration fits in the flow
- [ ] Clarify if Chatterbox provides separate endpoints or combined
- [ ] Decision documented and architecture updated

**Pattern Options:**
- **Option A (Multi-Endpoint):** STT → HA → LLM Endpoint → HA → TTS
- **Option B (Single-Endpoint):** Combined Wyoming endpoint handles STT → LLM → TTS internally

### Goal 2: Agentic Loop State Machine
**Status:** Not Started

Implement state machine to manage conversation flow with LLM and tool calling.

**Acceptance Criteria:**
- [ ] State machine designed and documented
- [ ] Framework selected (LangGraph or alternative)
- [ ] State machine handles: input, LLM inference, tool invocation, response composition
- [ ] Supports iterative refinement (multi-turn tool calling)
- [ ] Error handling for LLM failures, tool failures
- [ ] State persistence for conversation context
- [ ] Integration with Wyoming protocol endpoints

**State Flow:**
1. Initial text input (from STT)
2. LLM inference request
3. Tool invocation decision
4. Tool execution
5. Result aggregation
6. Response composition
7. Final text output (to TTS)

### Goal 3: Weather Tool Implementation
**Status:** Not Started

Create reference tool implementation for weather queries.

**Acceptance Criteria:**
- [ ] Weather tool accepts location parameters
- [ ] Tool queries weather API (OpenWeatherMap, Weather.gov, or similar)
- [ ] Returns structured weather data
- [ ] Error handling for invalid locations, API failures
- [ ] Tool definition compatible with LLM framework
- [ ] Documentation on tool interface

**Capabilities:**
- Current conditions lookup
- Forecast retrieval
- Location parsing (city, state, coordinates)

### Goal 4: Tool Framework Architecture
**Status:** Not Started

Design extensible framework for adding additional tools beyond weather.

**Acceptance Criteria:**
- [ ] Standardized tool definition format
- [ ] Tool registration mechanism
- [ ] Tool invocation interface
- [ ] Error handling framework for tool failures
- [ ] Timeout and retry mechanisms
- [ ] Documentation on adding new tools
- [ ] Example: second tool implemented (time/date or similar)

### Goal 5: LLM Integration
**Status:** Not Started

Integrate LLM with system prompts and tool definitions.

**Acceptance Criteria:**
- [ ] LLM client implemented (Claude, OpenAI, or other)
- [ ] System prompt designed for voice assistant context
- [ ] Tool definitions passed to LLM correctly
- [ ] LLM responses parsed and processed
- [ ] Handle tool calling requests from LLM
- [ ] Handle direct text responses from LLM
- [ ] Error handling for LLM API failures
- [ ] Rate limiting and cost management

### Goal 6: Context Management
**Status:** Not Started

Design and implement (or plan) conversational context persistence.

**Acceptance Criteria:**
- [ ] Research LangGraph/LangChain context capabilities
- [ ] Determine if built-in features meet requirements
- [ ] If feasible: implement context persistence
- [ ] If complex: create detailed proposal for future epic
- [ ] Context includes: prior conversation turns, user preferences
- [ ] Context search capability (LLM can query "have we discussed X?")
- [ ] Storage design (DynamoDB, cloud storage, or local)

**Deliverable Options:**
- **Option A:** Working context persistence system
- **Option B:** Context stub + detailed proposal for Epic 5

### Goal 7: End-to-End Conversation Flow
**Status:** Not Started

Validate complete conversation flow from speech to response.

**Acceptance Criteria:**
- [ ] Audio input → STT → LLM → Tool → Response → TTS → Audio output
- [ ] Example: "What is the weather in Kansas?" returns accurate spoken response
- [ ] Multi-turn conversations work (if context implemented)
- [ ] Latency meets requirements (<5s total for simple query)
- [ ] Error handling tested (LLM fails, tool fails, TTS fails)
- [ ] Integration with Epic 3 infrastructure validated

## Epic 4 Task Breakdown

### Task 4.1: Research and Document Home Assistant Conversation Flow
**Priority:** P0 (Critical - blocks architecture decisions)
**Owner:** TBD
**Depends On:** Epic 3 completion
**Estimated Effort:** 6 hours

Clarify exactly how Home Assistant handles voice assistant conversations.

**Subtasks:**
- Study Home Assistant voice assistant pipeline documentation
- Analyze whether HA expects separate STT/LLM/TTS endpoints
- Determine if HA has built-in LLM integration or expects external
- Test with actual Home Assistant instance if possible
- Document conversation flow patterns
- Make architectural decision on endpoint structure
- Update Epic 4 architecture based on findings

**Research Questions:**
- Does HA send text to a separate "assist" endpoint after STT?
- Does HA expect Wyoming services to handle full conversation?
- Where does LLM integration fit in HA's architecture?
- Can we provide a combined Wyoming endpoint?

**Deliverables:**
- Home Assistant conversation flow documentation
- Architectural decision document
- Updated Epic 4 architecture diagrams

**Definition of Done:**
- Conversation flow fully understood
- Endpoint architecture decided
- Team aligned on implementation approach
- Documentation complete

---

### Task 4.2: Select and Evaluate Agentic Framework
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.1
**Estimated Effort:** 8 hours

Evaluate and select framework for agentic loop implementation.

**Subtasks:**
- Evaluate LangGraph capabilities and fit
- Evaluate alternatives (AutoGen, CrewAI, custom state machine)
- Create proof-of-concept with top candidate
- Test tool calling capabilities
- Test state persistence capabilities
- Document framework choice rationale
- Create initial project structure

**Evaluation Criteria:**
- Tool calling support
- State management capabilities
- Context persistence features
- Documentation and community support
- License compatibility
- Performance characteristics

**Deliverables:**
- Framework evaluation document
- Proof-of-concept implementation
- Framework selection decision
- Initial project structure

**Definition of Done:**
- Framework selected and justified
- POC demonstrates core capabilities
- Team aligned on choice
- Project structure created

---

### Task 4.3: Design Agentic Loop State Machine
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.2
**Estimated Effort:** 8 hours

Design the state machine for managing conversation flow.

**Subtasks:**
- Define all conversation states
- Define state transitions and triggers
- Design input handling (text from STT)
- Design LLM invocation logic
- Design tool invocation decision logic
- Design tool execution handling
- Design response composition logic
- Design output handling (text to TTS)
- Create state diagrams
- Document error handling strategies

**States (proposed):**
- RECEIVE_INPUT: Accept text from STT
- LLM_INFERENCE: Send to LLM with tools and context
- TOOL_DECISION: Parse LLM response for tool requests
- TOOL_EXECUTION: Execute requested tools
- RESULT_AGGREGATION: Collect tool results
- RESPONSE_COMPOSITION: LLM generates final response
- OUTPUT: Send text to TTS

**Deliverables:**
- State machine design document
- State transition diagrams
- Error handling documentation
- Interface specifications

**Definition of Done:**
- All states and transitions defined
- Error handling designed
- State diagrams created
- Ready for implementation

---

### Task 4.4: Implement Core Agentic Loop
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.3
**Estimated Effort:** 12 hours

Implement the core state machine and conversation loop.

**Subtasks:**
- Implement state machine framework
- Implement input handler
- Implement LLM client wrapper
- Implement tool invocation dispatcher
- Implement response composition logic
- Implement output handler
- Add logging and debugging output
- Create unit tests for state transitions

**Technical Details:**
- Use selected framework (LangGraph or alternative)
- Clean separation between states
- Async/await for IO operations
- Structured logging for debugging
- Type hints and documentation

**Deliverables:**
- Core agentic loop implementation
- Unit tests
- Integration test stubs

**Definition of Done:**
- State machine implemented
- Can process text input → LLM → output
- Unit tests passing
- Code reviewed

---

### Task 4.5: Implement Weather Tool
**Priority:** P1 (High - needed for validation)
**Owner:** TBD
**Depends On:** Task 4.3
**Estimated Effort:** 6 hours

Create weather tool as reference implementation.

**Subtasks:**
- Design tool interface (matches framework requirements)
- Select weather API (OpenWeatherMap, Weather.gov, etc.)
- Implement API client
- Implement location parsing
- Implement error handling
- Create tool definition for LLM
- Add unit tests
- Document tool usage

**Tool Interface:**
```python
def get_weather(location: str) -> dict:
    """
    Get current weather for a location.

    Args:
        location: City name, "City, State", or coordinates

    Returns:
        dict with temperature, conditions, forecast
    """
```

**Deliverables:**
- Weather tool implementation
- Tool definition for LLM
- Unit tests
- API documentation

**Definition of Done:**
- Tool successfully queries weather API
- Returns structured data
- Error handling works
- Tests passing
- Integrated with state machine

---

### Task 4.6: Implement Tool Framework
**Priority:** P1 (High)
**Owner:** TBD
**Depends On:** Task 4.5
**Estimated Effort:** 8 hours

Create extensible framework for tool management.

**Subtasks:**
- Design tool registration system
- Implement tool discovery mechanism
- Create standardized tool definition format
- Implement tool invocation dispatcher
- Add timeout mechanisms
- Add retry logic for transient failures
- Create tool testing utilities
- Implement second tool as validation (time/date tool)
- Document tool development guide

**Framework Features:**
- Dynamic tool registration
- Tool metadata (name, description, parameters)
- Automatic LLM tool definition generation
- Timeout and error handling
- Tool execution logging

**Deliverables:**
- Tool framework implementation
- Second reference tool (time/date)
- Tool development documentation
- Tool testing utilities

**Definition of Done:**
- Multiple tools can be registered
- Tools invoked correctly by state machine
- Timeout and retry work
- Documentation complete
- Second tool implemented and working

---

### Task 4.7: Integrate LLM with System Prompts
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.4, Task 4.6
**Estimated Effort:** 8 hours

Configure LLM integration with appropriate prompts and tool definitions.

**Subtasks:**
- Design system prompt for voice assistant context
- Configure LLM client (API keys, model selection)
- Implement tool definition passing to LLM
- Implement LLM response parsing
- Handle tool calling requests
- Handle direct text responses
- Add error handling for API failures
- Implement rate limiting
- Add cost tracking
- Test with various query types

**System Prompt Design:**
- Voice assistant persona
- Tool usage guidelines
- Response formatting rules
- Context awareness

**Deliverables:**
- LLM integration implementation
- System prompt configuration
- Response parsing logic
- Error handling and rate limiting

**Definition of Done:**
- LLM successfully invoked with tools
- Tool calls parsed correctly
- Direct responses handled
- Error handling works
- Rate limiting in place

---

### Task 4.8: Research Context Management Solutions
**Priority:** P1 (High)
**Owner:** TBD
**Depends On:** Task 4.2
**Estimated Effort:** 6 hours

Research and evaluate context persistence approaches.

**Subtasks:**
- Research LangGraph built-in context features
- Research LangChain memory modules
- Evaluate storage options (DynamoDB, S3, local DB)
- Assess complexity of implementation
- Create decision matrix: implement now vs future epic
- If feasible: design context storage schema
- If complex: create detailed proposal for Epic 5
- Document findings and recommendations

**Research Areas:**
- Conversation history storage
- Context search capabilities
- Multi-user support
- Privacy and security considerations
- Performance implications

**Deliverables:**
- Context management research document
- Decision: implement in Epic 4 or defer to Epic 5
- If defer: detailed Epic 5 proposal
- If implement: design document for Task 4.9

**Definition of Done:**
- Research complete
- Decision made and documented
- Next steps clear (implement or propose)

---

### Task 4.9: Implement Context Management (Conditional)
**Priority:** P1 (High) - Only if Task 4.8 decides to implement
**Owner:** TBD
**Depends On:** Task 4.8
**Estimated Effort:** 12 hours (if implemented)

Implement context persistence if Task 4.8 determines it's feasible.

**Subtasks:**
- Implement storage backend (DynamoDB, local DB, etc.)
- Implement conversation history tracking
- Implement context retrieval for LLM
- Add context search capability
- Implement context tool for LLM ("have we discussed X?")
- Add conversation session management
- Add privacy controls (data retention, deletion)
- Test with multi-turn conversations
- Document context system

**Storage Schema:**
- User/session ID
- Conversation turns (timestamp, input, output, tools used)
- Metadata (location, preferences, etc.)

**Deliverables:**
- Context storage implementation
- Context retrieval system
- Context search tool
- Multi-turn conversation tests
- Documentation

**Definition of Done:**
- Context persisted across conversations
- LLM can access prior context
- Context search works
- Privacy controls in place
- Tests passing

**Note:** If Task 4.8 decides to defer, this task is skipped and replaced with context stub.

---

### Task 4.10: Create Context Stub (Alternative to 4.9)
**Priority:** P2 (Medium) - Only if Task 4.8 decides to defer
**Owner:** TBD
**Depends On:** Task 4.8
**Estimated Effort:** 4 hours

Create context placeholder if deferring to future epic.

**Subtasks:**
- Create stub context interface
- Implement no-op context methods
- Document interface for future implementation
- Create Epic 5 proposal document
- Design future context architecture
- Estimate Epic 5 scope and effort

**Deliverables:**
- Context stub interface
- Epic 5 proposal document
- Future architecture design

**Definition of Done:**
- Stub allows system to work without context
- Future epic clearly scoped
- Interface defined for future implementation

---

### Task 4.11: Integrate with Wyoming Protocol Endpoints
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.4, Epic 3 completion
**Estimated Effort:** 8 hours

Connect agentic loop with Wyoming protocol STT/TTS endpoints.

**Subtasks:**
- Determine integration points based on Task 4.1 findings
- Implement input handler to receive text from STT
- Implement output handler to send text to TTS
- Handle protocol handshaking
- Add error handling for protocol failures
- Test with Epic 3 emulator
- Validate end-to-end flow
- Document integration architecture

**Integration Patterns (depends on Task 4.1):**
- **Option A:** Separate endpoint receives text from HA after STT
- **Option B:** Combined Wyoming endpoint wraps STT → LLM → TTS

**Deliverables:**
- Wyoming protocol integration
- Integration tests
- End-to-end validation

**Definition of Done:**
- Agentic loop receives text from Wyoming STT
- Agentic loop sends response to Wyoming TTS
- Protocol handshake works
- Error handling validated
- Integration tests passing

---

### Task 4.12: End-to-End Conversation Testing
**Priority:** P0 (Critical)
**Owner:** TBD
**Depends On:** Task 4.11, Task 4.7, Task 4.5
**Estimated Effort:** 10 hours

Validate complete conversation flows with real scenarios.

**Subtasks:**
- Create test scenarios (weather queries, general questions, etc.)
- Test with Epic 3 emulator (audio → STT → LLM → TTS → audio)
- Validate weather tool invocation
- Test multi-turn conversations (if context implemented)
- Measure end-to-end latency
- Test error scenarios (LLM failure, tool failure, etc.)
- Test concurrent requests
- Create automated test suite
- Generate test reports

**Test Scenarios:**
1. "What is the weather in Kansas?" - Tool calling
2. "What time is it?" - Tool calling (if time tool implemented)
3. "Tell me a joke" - Direct LLM response (no tools)
4. Multi-turn: "What's the weather?" → "How about tomorrow?" (if context works)
5. Error cases: Invalid location, API timeout, LLM failure

**Deliverables:**
- End-to-end test suite
- Performance measurements
- Test results and validation reports
- Identified issues and resolutions

**Definition of Done:**
- All test scenarios pass
- Latency within requirements (<5s for simple queries)
- Error handling validated
- Concurrent requests work
- Test suite automated

---

### Task 4.13: Performance Optimization
**Priority:** P2 (Medium)
**Owner:** TBD
**Depends On:** Task 4.12
**Estimated Effort:** 6 hours

Optimize conversation loop for latency and responsiveness.

**Subtasks:**
- Profile conversation flow to identify bottlenecks
- Optimize LLM API calls (streaming, caching)
- Optimize tool execution (parallel calls if possible)
- Implement response streaming if supported
- Add caching for repeated queries
- Test performance improvements
- Document optimization strategies

**Optimization Targets:**
- LLM inference time
- Tool execution time
- Network latency
- State transition overhead

**Deliverables:**
- Performance profiling results
- Optimization implementations
- Before/after performance comparison
- Documentation

**Definition of Done:**
- Performance improvements measured
- Latency reduced where possible
- Optimizations documented
- No regressions introduced

---

### Task 4.14: Create Epic 4 Documentation Package
**Priority:** P2 (Medium)
**Owner:** TBD
**Depends On:** All Epic 4 implementation tasks
**Estimated Effort:** 6 hours

Consolidate all Epic 4 documentation.

**Subtasks:**
- Document agentic loop architecture
- Document state machine design
- Document tool framework
- Create tool development guide
- Document LLM integration
- Document context management (or future plan)
- Create conversation flow diagrams
- Create troubleshooting guide
- Add code documentation (docstrings, comments)

**Deliverables:**
- docs/agentic-loop.md (architecture and design)
- docs/tool-development.md (guide for adding tools)
- docs/conversation-flows.md (end-to-end flows)
- Code documentation (docstrings, comments)

**Definition of Done:**
- All documentation complete and reviewed
- Tool development guide enables others to add tools
- Conversation flows clearly documented
- Troubleshooting guide helpful

---

### Task 4.15: Epic 4 Sign-Off and Validation
**Priority:** P0 (Critical - Epic completion)
**Owner:** TBD
**Depends On:** All Epic 4 tasks
**Estimated Effort:** 4 hours

Final validation that all Epic 4 acceptance criteria are met.

**Subtasks:**
- Review all Epic 4 acceptance criteria
- Run complete test suite and verify all pass
- Verify all documentation is complete
- Conduct final code review
- Create Epic 4 completion report
- Tag release/milestone in version control
- Demo complete system to stakeholders

**Validation Checklist:**
- [ ] Home Assistant conversation flow clarified and documented
- [ ] Agentic loop implemented and tested
- [ ] State machine functional
- [ ] Weather tool operational
- [ ] Tool framework extensible
- [ ] LLM integration working
- [ ] Context management designed/implemented or future epic proposed
- [ ] Wyoming protocol integration complete
- [ ] End-to-end conversations validated
- [ ] Performance meets requirements
- [ ] Documentation complete

**Deliverables:**
- Epic 4 completion report
- Final test results
- Version control tag/release
- System demonstration

**Definition of Done:**
- All Epic 4 acceptance criteria met
- All tests passing
- Documentation reviewed and approved
- Epic 4 bead closed
- System ready for production use or next epic

---

# Technical Architecture

## Overall System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Box 3B Device                       │
│  (Hardware wake word → Audio capture → PCM streaming)   │
└────────────────────┬────────────────────────────────────┘
                     │ PCM Audio
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Home Assistant                         │
│         (Voice Assistant Pipeline)                      │
└──┬──────────────────────────────────────────────────┬───┘
   │ Wyoming Protocol                                  │
   │ (PCM Audio)                                       │ (PCM Audio)
   ▼                                                   ▲
┌─────────────────────────────┐                       │
│  Chatterbox STT Service     │                       │
│  (Whisper via Wyoming)      │                       │
└──────────┬──────────────────┘                       │
           │ Text                                      │
           ▼                                           │
┌─────────────────────────────────────────────────────┐│
│       Chatterbox Agentic Loop (Epic 4)              ││
│                                                      ││
│  ┌──────────────────────────────────────────────┐  ││
│  │         State Machine (LangGraph)            │  ││
│  │                                              │  ││
│  │  Input → LLM Inference → Tool Decision      │  ││
│  │       ↓                          ↓           │  ││
│  │  Tool Execution ← ← ← ← ← ←     │           │  ││
│  │       ↓                                      │  ││
│  │  Response Composition → Output               │  ││
│  └──────────────────────────────────────────────┘  ││
│                                                      ││
│  ┌──────────────────────────────────────────────┐  ││
│  │            Tool Framework                    │  ││
│  │  • Weather Tool                              │  ││
│  │  • Time/Date Tool                            │  ││
│  │  • [Future: Home Control, etc.]              │  ││
│  └──────────────────────────────────────────────┘  ││
│                                                      ││
│  ┌──────────────────────────────────────────────┐  ││
│  │      Context Management (Optional)           │  ││
│  │  • Conversation History                      │  ││
│  │  • Context Search                            │  ││
│  └──────────────────────────────────────────────┘  ││
└──────────────────┬──────────────────────────────────┘│
                   │ Text Response                      │
                   ▼                                    │
           ┌──────────────────────────┐                │
           │  Chatterbox TTS Service  │                │
           │  (Piper via Wyoming)     │────────────────┘
           └──────────────────────────┘
```

## Epic 3: Testing Infrastructure

```
┌────────────────────────────────────────────────────────┐
│         Home Assistant Emulator (Epic 3)               │
│                                                         │
│  ┌────────────────┐      ┌─────────────────────┐      │
│  │  Wave File     │──►   │  PCM Stream         │      │
│  │  Loader        │      │  Generator          │      │
│  └────────────────┘      └──────────┬──────────┘      │
│                                     │                  │
│  ┌────────────────────────────────┐ │                 │
│  │  Test Corpus (10-15 files)    │ │                 │
│  │  • "Turn on lights"            │ │                 │
│  │  • "What's the weather?"       │ │                 │
│  │  • ...                         │ │                 │
│  └────────────────────────────────┘ │                 │
│                                     │                  │
│                                     ▼                  │
│               ┌──────────────────────────────┐         │
│               │  Wyoming Protocol Client     │         │
│               └──────────┬───────────────────┘         │
└──────────────────────────┼──────────────────────────────┘
                           │ Wyoming Protocol
                           ▼
        ┌──────────────────────────────────────┐
        │  Chatterbox Wyoming Services         │
        │  • STT (Whisper)                     │
        │  • TTS (Piper)                       │
        └──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  Validation Framework                │
        │  • Text accuracy validation          │
        │  • Audio integrity validation        │
        │  • Performance measurement           │
        │  • Test reporting                    │
        └──────────────────────────────────────┘
```

## Epic 4: Agentic Loop State Flow

```
    ┌─────────────────┐
    │ Text Input      │ (from STT)
    │ from Wyoming    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ RECEIVE_INPUT   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ LLM_INFERENCE   │ ◄──────┐
    │ (with tools +   │        │
    │  context)       │        │
    └────────┬────────┘        │
             │                 │
             ▼                 │
    ┌─────────────────┐        │
    │ TOOL_DECISION   │        │
    └────────┬────────┘        │
             │                 │
        ┌────┴────┐            │
        │         │            │
    No Tools   Tools Needed    │
        │         │            │
        │         ▼            │
        │  ┌─────────────────┐│
        │  │ TOOL_EXECUTION  ││
        │  └────────┬────────┘│
        │           │         │
        │           ▼         │
        │  ┌─────────────────┐│
        │  │ RESULT_         ││
        │  │ AGGREGATION     │┘
        │  └────────┬────────┘
        │           │
        │      More tools?
        │           │
        │        Yes├─────────┘
        │           │
        │          No
        │           │
        └───────────┤
                    │
                    ▼
           ┌─────────────────┐
           │ RESPONSE_       │
           │ COMPOSITION     │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ OUTPUT          │ (to TTS)
           └─────────────────┘
```

---

# Dependencies & Prerequisites

## Epic 3 Prerequisites

### Software
- Python 3.8+
- Wyoming protocol client library (or custom implementation)
- Wave file processing libraries (`wave`, `soundfile`)
- Whisper service configured
- Piper service configured

### Knowledge
- Wyoming protocol specification
- PCM audio formats
- Python async programming
- Testing frameworks

## Epic 4 Prerequisites

### Software
- Epic 3 completed and validated
- Python 3.8+
- LangGraph or selected agentic framework
- LLM API access (Claude API, OpenAI API, etc.)
- Weather API access
- Storage backend (if context implemented: DynamoDB, PostgreSQL, etc.)

### Knowledge
- Agentic framework (LangGraph/LangChain)
- LLM API usage and tool calling
- State machine design
- Async programming
- API integration

---

# Success Metrics

## Epic 3 Success Criteria

- ✅ Wyoming protocol fully documented and understood
- ✅ Home Assistant emulator functional and reliable
- ✅ Test corpus complete (10-15 wave files)
- ✅ All protocol endpoints validated
- ✅ STT service achieves >90% transcription accuracy
- ✅ TTS service produces clear, artifact-free audio
- ✅ Integration tests passing with >95% success rate
- ✅ Round-trip latency <3s for typical utterance
- ✅ Documentation complete and reviewed
- ✅ Epic 4 ready to begin

## Epic 4 Success Criteria

- ✅ Conversation flow pattern documented
- ✅ Agentic loop implemented and tested
- ✅ State machine handles all conversation scenarios
- ✅ Weather tool operational and accurate
- ✅ Tool framework supports multiple tools
- ✅ LLM integration working reliably
- ✅ Context management designed/implemented or future epic scoped
- ✅ Wyoming protocol integration validated
- ✅ End-to-end conversation latency <5s for simple queries
- ✅ Error handling robust (LLM failures, tool failures, network issues)
- ✅ Performance acceptable for real-time conversation
- ✅ Documentation complete and reviewed
- ✅ System ready for production use

---

# Risk Mitigation

## Epic 3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Wyoming protocol poorly documented | Medium | High | Deep research; test with actual HA instance; engage HA community |
| Whisper accuracy issues | Low | Medium | Use high-quality test corpus; tune Whisper parameters; test with various voices |
| Network reliability | Medium | Medium | Implement retry logic; test error handling; use local network for testing |
| PCM audio format issues | Medium | High | Validate formats early; test with known-good samples; refer to Wyoming spec |

## Epic 4 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| LLM latency too high | Medium | High | Use streaming; optimize prompts; consider local models for fallback |
| Tool calling unreliable | Low | Medium | Implement robust parsing; test with various LLM responses; add retry logic |
| Context persistence complexity | High | Medium | Research early (Task 4.8); defer to Epic 5 if too complex |
| Weather API reliability | Medium | Low | Implement caching; use multiple providers; add error handling |
| Integration with HA unclear | Medium | High | Research thoroughly (Task 4.1); test with actual HA; adjust architecture as needed |
| Cost of LLM API calls | Medium | Medium | Implement rate limiting; use caching; monitor costs; consider local models |

---

# Timeline Estimates

## Epic 3 Timeline

**Total Estimated Effort:** ~60 hours (1.5-2 weeks for single developer)

**Critical Path:**
1. Task 3.1: Wyoming research (8 hours)
2. Task 3.2: Emulator design (6 hours)
3. Task 3.3: Test corpus (4 hours) - can be parallel with 3.2
4. Task 3.4: Emulator implementation (12 hours)
5. Task 3.5: Validation framework (8 hours)
6. Tasks 3.6 + 3.7: STT and TTS validation (12 hours) - can be parallel
7. Task 3.8: Integration testing (6 hours)
8. Task 3.9: Documentation (4 hours)
9. Task 3.10: Sign-off (4 hours)

**Parallelization Opportunities:**
- Task 3.3 (test corpus) can start after 3.1
- Tasks 3.6 and 3.7 (STT/TTS validation) can run in parallel
- Task 3.9 (documentation) can be done incrementally

## Epic 4 Timeline

**Total Estimated Effort:** ~88-100 hours (2-2.5 weeks for single developer)

Note: Effort varies based on context management decision (Task 4.9 vs 4.10).

**Critical Path:**
1. Task 4.1: HA conversation flow research (6 hours)
2. Task 4.2: Framework evaluation (8 hours)
3. Task 4.3: State machine design (8 hours)
4. Task 4.4: Agentic loop implementation (12 hours)
5. Task 4.5: Weather tool (6 hours) - can be parallel with 4.4
6. Task 4.6: Tool framework (8 hours)
7. Task 4.7: LLM integration (8 hours)
8. Task 4.8: Context research (6 hours)
9. Task 4.9 OR 4.10: Context implementation or stub (12 or 4 hours)
10. Task 4.11: Wyoming integration (8 hours)
11. Task 4.12: E2E testing (10 hours)
12. Task 4.13: Optimization (6 hours) - can be parallel with 4.14
13. Task 4.14: Documentation (6 hours)
14. Task 4.15: Sign-off (4 hours)

**Parallelization Opportunities:**
- Task 4.5 (weather tool) can start after 4.3
- Task 4.8 (context research) can start early, after 4.2
- Task 4.13 (optimization) and 4.14 (documentation) can overlap

---

# Next Steps

## To Begin Epic 3:

1. **Immediate:** Start Task 3.1 (Wyoming protocol research)
2. **Setup:** Create Epic 3 parent bead and all task beads
3. **Organize:** Set up project structure for emulator and tests
4. **Dependencies:** Verify Whisper and Piper services are accessible

## To Begin Epic 4:

**Prerequisites:**
- Epic 3 must be complete (all beads closed)
- Wyoming protocol infrastructure validated
- Epic 3 emulator available for testing

**First Steps:**
1. Unblock Epic 4 bead (after Epic 3 completion)
2. Start Task 4.1 (HA conversation flow research)
3. Setup project structure for agentic loop
4. Obtain LLM API access

---

**Document Version:** 1.0
**Last Updated:** 2026-02-18
**Epic Owner:** TBD
**Related Beads:** chatterbox-6ao (planning bead)
