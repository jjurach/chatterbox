# Chatterbox Wyoming Protocol and LLM Integration Specification

**Document ID:** SPEC-CHATTERBOX-20260218
**Created:** 2026-02-18
**Status:** Draft
**Epics Covered:** Epic 3, Epic 4

---

## Executive Summary

This specification outlines the implementation and validation of Wyoming protocol support in the Chatterbox project, enabling integration with Home Assistant's voice assistant ecosystem. The work is structured across two major epics: Epic 3 focuses on Wyoming protocol implementation and testing infrastructure, while Epic 4 introduces LLM-based conversational capabilities with tool calling support.

---

## Epic 3: Wyoming Protocol Implementation and Validation

### Objective

Validate and confirm that all necessary components are in place for Chatterbox backends to implement the Wyoming protocol features required by Home Assistant. Establish comprehensive testing infrastructure to emulate Home Assistant interactions.

### Background

The Wyoming protocol is Home Assistant's standard for voice satellite communication, enabling:
- Speech-to-text (STT) services via Whisper
- Text-to-speech (TTS) services via Piper
- Bidirectional PCM audio streaming
- Text-based assist queries

The Chatterbox project aims to implement an Alexa-like voice assistant device (Box 3B) that integrates with Home Assistant through these Wyoming protocol endpoints.

### Key Requirements

#### 3.1 Protocol Research and Documentation
- **Research Phase:** Conduct thorough investigation of the Wyoming protocol specification
- **Documentation:** Create comprehensive documentation of:
  - Actual conversation flows between Home Assistant and Wyoming services
  - All protocol endpoints and their expected behaviors
  - Message formats and PCM packet specifications
  - Integration patterns for STT, TTS, and assist services
- **Validation:** Confirm assumptions about protocol flow and adjust implementation plan based on findings

#### 3.2 Home Assistant Emulator
- **Purpose:** Create an emulator that simulates Home Assistant's interactions with Chatterbox backends
- **Capabilities:**
  - Generate PCM audio streams from pre-recorded wave files
  - Transmit PCM packets to Wyoming protocol endpoints
  - Receive and validate responses (both text and audio streams)
  - Validate integrity and correctness of transmitted data
- **Test Data:** Utilize 10-15 pre-generated wave files as test inputs
  - Files should contain various sample statements/questions
  - Generated using Piper or similar TTS service
  - Stored in source tree for reproducible testing

#### 3.3 Speech-to-Text Service Validation
- **Service:** Whisper-based STT endpoint
- **Flow:**
  1. Hardware wake word triggers audio capture on Box 3B device
  2. PCM audio stream transmitted to Home Assistant
  3. Home Assistant relays stream to Chatterbox Whisper service via Wyoming protocol
  4. Chatterbox transcribes audio to text
  5. Text response returned through protocol chain
- **Testing:**
  - Emulator generates PCM streams from wave files
  - Chatterbox STT service processes streams
  - Validate transcription accuracy against known inputs

#### 3.4 Text-to-Speech Service Validation
- **Service:** Piper-based TTS endpoint
- **Flow:**
  1. Home Assistant sends text to Chatterbox via Wyoming protocol
  2. Chatterbox invokes Piper TTS service
  3. PCM audio stream generated and transmitted back to Home Assistant
  4. Home Assistant relays to Box 3B for playback
- **Testing:**
  - Emulator sends text queries
  - Chatterbox TTS generates audio streams
  - Emulator captures output as temporary wave files
  - Validate audio quality and content integrity

#### 3.5 Integration Testing Infrastructure
- **Input Processing:**
  - Script to generate wave files from text statements
  - Standardized test corpus for repeatable validation
  - Wave file storage in source tree
- **Output Validation:**
  - Temporary wave file construction from received PCM streams
  - Automated integrity checks
  - Comparison mechanisms for validating round-trip accuracy
- **Test Coverage:**
  - All Wyoming protocol endpoints
  - Error handling and edge cases
  - Performance and latency measurements

### Deliverables

1. Wyoming protocol research documentation
2. Home Assistant emulator implementation
3. Test wave file corpus (10-15 samples)
4. Integration test suite
5. Protocol flow diagrams and documentation
6. Validation reports confirming all components are operational

### Task Breakdown

Epic 3 will consist of 5-10 individual beads (tasks), each addressing specific components of the protocol implementation and testing infrastructure.

---

## Epic 4: LLM Integration with Tool Calling

### Objective

Implement a stateful, agentic conversation loop that enables Chatterbox to process natural language queries, invoke tools as needed, and generate contextually appropriate responses. This epic builds upon Epic 3's Wyoming protocol foundation.

### Background

Modern voice assistants require more than simple speech recognition and synthesis. They need the ability to understand intent, access external services, and maintain conversational context. Epic 4 introduces LLM-based intelligence to Chatterbox, enabling features like weather queries, home automation control, and contextual conversations.

### Key Requirements

#### 4.1 Agentic Loop Architecture
- **Framework:** Implement using LangGraph or similar agentic framework
- **State Machine:** Design state engine to manage:
  - Initial text input from STT
  - LLM inference requests
  - Tool invocation decisions
  - Tool execution results
  - Response composition
  - Iterative refinement (multi-turn tool calling)
- **Integration:** Seamlessly integrate with Wyoming protocol endpoints from Epic 3

#### 4.2 Conversation Flow

**Example Scenario:** "What is the weather in Kansas today?"

1. **Speech Input:** Box 3B captures audio, sends via Wyoming protocol
2. **Transcription:** Whisper STT converts to text
3. **LLM Processing:** Text passed to agentic loop with:
   - System prompt
   - Available tools array
   - Optional: Prior conversation context
4. **Tool Invocation:** LLM determines weather tool is needed
   - State machine transitions to tool execution state
   - Weather tool invoked with geographic parameters
   - Tool result captured
5. **Response Composition:** Tool result returned to LLM
   - LLM generates natural language response
   - May invoke additional tools if needed
   - Final response text generated
6. **Speech Output:** Response text sent to Piper TTS
7. **Audio Return:** PCM stream sent back through Wyoming protocol to Box 3B

#### 4.3 Tool System

**Initial Tool:** Weather Service
- **Capability:** Provide geographic-based weather information
- **Parameters:** Location (city, state, coordinates)
- **Response:** Current conditions, forecast, etc.
- **Purpose:** Serve as reference implementation for tool calling pattern

**Tool Framework:**
- Extensible architecture for adding additional tools
- Standardized tool definition format
- Error handling for tool failures
- Timeout and retry mechanisms

#### 4.4 Context Management

**Conversational Context:**
- **Prior Context Access:** Enable agents to access previous conversation turns
- **Context Search:** Implement search capability within conversation history
- **Context Tool:** Allow LLM to query "have we discussed X before?"
- **Storage:** Design for persistent storage (DynamoDB, cloud storage, etc.)

**Implementation Approach:**
- **Phase 1:** Investigate LangGraph/LangChain built-in context features
- **Phase 2:** If features exist and are straightforward, implement as part of Epic 4
- **Phase 3:** If complex, create placeholder/stub and propose future epic
- **Deliverable:** Either working context persistence or detailed proposal for future implementation

#### 4.5 Protocol Clarification

**Research Required:** Determine exact Home Assistant conversation pattern:

**Option A - Multi-Endpoint:**
1. PCM → Wyoming STT → Text
2. Text → Home Assistant → Chatterbox LLM Endpoint
3. Response → Home Assistant → Chatterbox TTS Endpoint
4. PCM ← TTS

**Option B - Single-Endpoint:**
1. PCM → Wyoming Combined Endpoint
2. Internal: STT → LLM → Tool Loop → TTS
3. PCM ← Wyoming Combined Endpoint

**Decision:** Confirm actual Home Assistant protocol and implement accordingly.

### Deliverables

1. State machine implementation (LangGraph-based)
2. Weather tool reference implementation
3. Tool calling framework
4. LLM integration with system prompts and tool definitions
5. Context management system (implemented or designed)
6. Integration with Epic 3 Wyoming protocol endpoints
7. End-to-end conversation testing
8. Documentation of conversation flows and state transitions
9. If applicable: Proposal for future context persistence epic

### Task Breakdown

Epic 4 will consist of multiple beads addressing state machine design, tool implementation, LLM integration, and end-to-end testing.

---

## Dependencies

- **Epic 4 depends on Epic 3:** Wyoming protocol infrastructure must be validated before LLM integration
- **Sequential Execution:** Epic 3 must reach completion before Epic 4 begins

---

## Success Criteria

### Epic 3
- [ ] Wyoming protocol fully documented
- [ ] Home Assistant emulator functional
- [ ] All protocol endpoints validated
- [ ] Test infrastructure operational
- [ ] STT and TTS services confirmed working
- [ ] Integration tests passing

### Epic 4
- [ ] Agentic loop implemented and tested
- [ ] Weather tool operational
- [ ] End-to-end conversation flow validated
- [ ] Context management designed/implemented
- [ ] Integration with Wyoming protocol confirmed
- [ ] Performance meets latency requirements

---

## Future Considerations

- Additional tool implementations (home automation, calendar, reminders, etc.)
- Advanced context persistence and conversation history management
- Multi-user support and personalization
- Performance optimization for real-time conversation
- Security and privacy considerations for cloud storage

---

## Notes

This specification captures the vision for Chatterbox as an intelligent, extensible voice assistant platform. The two-epic structure allows for incremental development and validation, ensuring solid protocol foundations before adding conversational intelligence.
