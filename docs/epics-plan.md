# Cackle Chatterbox: 12-Epic Implementation Plan

**Document Purpose:** Comprehensive overview of all 12 epics for the Chatterbox voice assistant project, including completion status, deliverables, dependencies, and sequencing.

**Last Updated:** 2026-03-24

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Epic Overview Table](#epic-overview-table)
3. [Epic Summaries](#epic-summaries)
4. [Dependency Graph](#dependency-graph)
5. [Timeline and Sequencing](#timeline-and-sequencing)
6. [Testing Criteria by Epic](#testing-criteria-by-epic)

---

## Executive Summary

The Cackle Chatterbox project is a 12-epic initiative to build a complete, production-ready voice assistant device (ESP32-S3-BOX-3B) integrated with Home Assistant. The epics are organized in dependency-ordered phases:

- **Foundation Phase** (Epic 1): OTA & device state machine
- **Hardware Integration Phase** (Epics 2-3): Wake word, Wyoming protocol, testing infrastructure
- **Intelligence Phase** (Epics 4-5): LLM integration, context persistence with Mellona STT/TTS pre-integrated
- **Enhancement & Production Phase** (Epics 6-12): Backend deployment, audio, touchscreen, reliability, documentation

**Key Strategic Decisions:**
- **Mellona Integration:** High-priority pre-requisite for Epic 5 (already implemented STT/TTS)
- **Backend Storage:** SQLite for single-device, PostgreSQL as future migration path
- **Deployment:** Docker + Docker Compose for production deployment
- **Wake Word:** box3b's LOCAL voice model (no streaming to HA)
- **Serial Logging:** Phase 1 (before HA integration in Phase 2)
- **Device Testing:** Available now via USB - can start testing immediately

---

## Epic Overview Table

| # | Name | Status | Focus Area | Duration | Depends On |
|---|------|--------|-----------|----------|-----------|
| 1 | OTA & Foundation | **Ready for Testing** | Device state machine, OTA updates, OCR validation | 2 weeks | — |
| 2 | Observability & Serial Logging | Planned | Serial logging infrastructure, log capture service, operator utilities | 2 weeks | Epic 1 |
| 3 | Wyoming Protocol & Testing | **Complete** | Wyoming protocol implementation, STT/TTS validation, test infrastructure | 3 weeks | Epic 2 |
| 4 | LLM Integration | **Complete** | Agentic loop, tool calling, conversation handling | 3 weeks | Epic 3 |
| 5 | Context Persistence | Planned | Conversation history storage, multi-user isolation, context search | 2 weeks | Epic 4 |
| 6 | Backend Deployment & HA Connection | Planned | Docker deployment, docker-compose orchestration, HA Wyoming connection | 2 weeks | Epic 5 |
| 7 | Recording & PCM Streaming | Planned | Voice recording on device, PCM transmission, Whisper STT integration | 2 weeks | Epic 6 |
| 8 | Receiving & Audio Playback | Planned | Return audio path, speaker playback, transition sounds | 1.5 weeks | Epic 7 |
| 9 | Touchscreen Integration & Device Coordination | Planned | Touchscreen UI, multi-device discovery, room-aware responses | 3 weeks | Epic 8 |
| 10 | Continuous Conversation & Wake Word | Planned | Always-listening local wake word, automatic state transitions | 2 weeks | Epic 9 |
| 11 | Reliability & LLM Fallback | Planned | Multi-LLM providers, automatic fallback, cost tracking, local fallback | 2 weeks | Epic 10 |
| 12 | Documentation & Maintenance | Planned | Sustainability, documentation, community support | Ongoing | Epic 11 |

---

## Epic Summaries

### Epic 1: OTA & Foundation

**Status:** Ready for Testing (In Progress)
**Completion Target:** 2026-03-31
**Device Available:** Yes - Connected via USB, can start testing immediately

**Purpose:** Establish foundational infrastructure for the Chatterbox device, including a working state machine with visual indicators and reliable Over-The-Air update capabilities.

**Key Deliverables:**
- Device state machine MVP cycling through 6 states (N, H, S, A, W, P) with color-coded display
- Large letter display (100pt+) on each screen for OCR validation
- Python OTA deployment tool supporting single/batch device firmware updates
- OCR validator tool reading /dev/video0 and recognizing device state
- Secure OTA endpoint with password protection

**Acceptance Criteria:**
- [ ] State machine transitions work correctly through all 6 states
- [ ] Each state displays corresponding letter with >95% OCR confidence
- [ ] Colors match specification (Orange/Purple/Blue/Red/Yellow/Green)
- [ ] OTA deployment tool successfully deploys firmware to devices
- [ ] OCR validation achieves >95% accuracy in normal lighting
- [ ] Documentation complete and tested
- [ ] Physical device testing completed (available now via USB)

**Key Risks:**
- OCR accuracy in varying lighting conditions (Mitigation: preprocessing, lighting adjustment)
- OTA reliability (Mitigation: retry logic, serial fallback)
- Display rendering issues (Mitigation: early physical device testing)

**Testing Criteria:**
- [ ] Deploy firmware via OTA to device
- [ ] Verify state machine cycles through all states
- [ ] Verify all letters display correctly with correct colors
- [ ] Run OCR validation tool and verify accuracy
- [ ] Test error recovery (failed OTA, bad OCR)

---

### Epic 2: Observability & Serial Logging (Phase 1)

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 1
**Notes:** Serial logging as Phase 1; HA integration moved to Phase 2 (future epic)

**Purpose:** Establish serial logging infrastructure for device observability, troubleshooting, and monitoring. Phase 1 focuses on reliable serial logging; Home Assistant dashboard integration deferred to Phase 2.

**Key Deliverables:**
- Structured serial logging schema (JSON format, configurable levels)
- Serial logging integration on ESP32 firmware
- Serial log capture service (Python background service)
- Log file rotation and persistence
- Structured logging macros for all device modules
- Performance baseline metrics collection via serial logs
- Documentation for setup and troubleshooting

**Acceptance Criteria:**
- [ ] Serial logging captures 100% of device state transitions
- [ ] All state transitions logged with timestamps and context
- [ ] Audio events logged (record start/stop, errors)
- [ ] Network events logged with packet statistics
- [ ] Memory/resource usage logged periodically
- [ ] Log output format valid JSON for structured parsing
- [ ] Log files rotated daily with configurable retention
- [ ] Performance overhead <5% CPU impact
- [ ] Serial log capture service runs reliably as systemd service

**Testing Criteria:**
- [ ] Monitor serial output during state transitions
- [ ] Verify all event types captured
- [ ] Test with verbose and quiet logging modes
- [ ] Validate log searchability and indexing
- [ ] 24-hour stability test for log capture

**Future Phase 2:** Home Assistant integration, MQTT entities, Lovelace dashboard, log aggregation backend, web UI for log viewing

---

### Epic 3: Wyoming Protocol & Testing Infrastructure

**Status:** Complete (2026-02-19)
**Reference:** dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md

**Purpose:** Validate Wyoming protocol implementation and establish comprehensive testing infrastructure for Home Assistant integration.

**Key Deliverables:**
- Complete Wyoming protocol documentation and conversation flow mapping
- Home Assistant emulator for testing without HA installation
- Test wave file corpus (15+ samples with known content)
- Whisper STT service validation and integration
- Piper TTS service validation and integration
- Round-trip integration testing framework

**Acceptance Criteria:**
- [x] Wyoming protocol fully documented
- [x] STT service transcription validated against known inputs
- [x] TTS service audio output verified
- [x] Integration tests passing for all protocol endpoints
- [x] Test corpus complete and documented
- [x] Emulator enabling autonomous testing

**Testing Criteria:**
- [x] All Wyoming protocol endpoints functional
- [x] STT accuracy within acceptable range (>90% for clear audio)
- [x] TTS audio quality acceptable for playback
- [x] Round-trip audio processing latency <3 seconds
- [x] Integration tests fully automated

---

### Epic 4: LLM Integration & Conversational AI

**Status:** Complete (2026-02-20)
**Reference:** dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md

**Purpose:** Implement stateful, agentic conversation loop with LLM inference and tool calling capabilities.

**Key Deliverables:**
- Agentic conversation loop using LangChain/LangGraph
- State machine for managing LLM inference, tool invocation, and response composition
- Weather tool as reference implementation for tool calling
- System prompt framework for LLM behavior customization
- In-memory context management (placeholder for persistent storage in Epic 5)
- Wyoming protocol integration with STT/TTS endpoints
- Comprehensive end-to-end conversation testing

**Acceptance Criteria:**
- [x] Agentic loop successfully processes natural language queries
- [x] Tool framework extensible for additional tools
- [x] Weather tool provides accurate geographic-based weather data
- [x] Multi-turn conversation context tracked in-memory
- [x] End-to-end latency <5 seconds for simple queries
- [x] Integration with Wyoming protocol complete
- [x] Error handling robust and documented

**Testing Criteria:**
- [x] Direct LLM queries (no tool calling)
- [x] Tool-invoked queries (weather, time, etc.)
- [x] Multi-turn conversations with context awareness
- [x] Error scenarios (invalid inputs, API failures)
- [x] Concurrent conversation handling
- [x] Latency measurements within SLA

---

### Epic 5: Context Persistence & History Management

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 4
**Prerequisites:** Mellona integration (HIGH PRIORITY - must complete BEFORE Epic 5)

**Purpose:** Implement persistent conversation history storage so context survives process restarts and enables cross-session awareness. Mellona's integrated STT/TTS enables rich audio context logging.

**Backend Strategy:**
- **Phase 1:** SQLite for single-device/development (default)
- **Phase 2+:** PostgreSQL migration path for scalable deployments (optional)
- Storage abstraction layer enables backend swapping without code changes

**Key Deliverables:**
- Persistent conversation storage backend (SQLite primary, PostgreSQL-ready abstraction)
- History retention policy with configurable TTL (default 30 days)
- Context search tool enabling LLM to query prior conversations
- Multi-user isolation ensuring conversation privacy
- Storage abstraction interface enabling backend swapping
- Retention policy enforcement and automatic purging
- Mellona audio context integration for rich conversation history

**Acceptance Criteria:**
- [ ] Conversation history survives process restart
- [ ] Storage supports concurrent access
- [ ] Write latency <10ms per turn
- [ ] TTL-based automatic purging functional
- [ ] Context search tool working with <200ms latency
- [ ] Multi-user isolation enforced with no cross-contamination
- [ ] Mellona STT/TTS context logged and retrievable
- [ ] SQLite backend fully operational
- [ ] PostgreSQL migration path documented

**Testing Criteria:**
- [ ] History retrieval after restart
- [ ] Concurrent conversation handling
- [ ] Retention policy enforcement
- [ ] Context search accuracy
- [ ] User isolation validation
- [ ] Performance under load with 1000+ messages
- [ ] SQLite and PostgreSQL backends tested equivalently

---

### Epic 6: Backend Deployment & Home Assistant Connection

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 5

**Purpose:** Establish production-ready backend deployment infrastructure with Docker containerization and robust Home Assistant integration.

**Deployment Strategy:**
- **Docker:** Multi-stage builds, minimal images, health checks
- **Docker Compose:** Single-command full system deployment (backend, DB, services)
- **Scalability:** Multi-device support with load balancing
- **HA Integration:** Reliable Wyoming protocol connection with automatic recovery

**Key Deliverables:**
- Dockerfile with multi-stage builds for backend service
- docker-compose.yml for complete system orchestration
- Stable Wyoming protocol connection to Home Assistant
- Comprehensive logging and monitoring integration
- Deployment automation and rollback procedures
- Production-grade operational procedures

**Acceptance Criteria:**
- [ ] Docker image builds reliably with <5 min build time
- [ ] docker-compose brings entire system up in single command
- [ ] Wyoming protocol connection stable for >24 hours
- [ ] Deployment takes <15 minutes for new instance
- [ ] Rollback procedure works without data loss
- [ ] System automatically recovers from common failures
- [ ] All logs properly structured and searchable

**Testing Criteria:**
- [ ] Docker build and run tests
- [ ] docker-compose full system integration
- [ ] Wyoming protocol stability testing
- [ ] Multi-device deployment scenario
- [ ] Rollback procedure validation

---

### Epic 7: Recording & PCM Streaming

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 6

**Serial Logging Tool:** Available as separate utility script with multiple sub-commands
- `chatterbox-logs capture` - Capture serial logs
- `chatterbox-logs view` - View/tail logs
- `chatterbox-logs search` - Search log archives
- `chatterbox-logs export` - Export logs to CSV/JSON

**Purpose:** Implement voice recording on the ESP32-S3-BOX-3B device and PCM packet transmission to the backend through Home Assistant. Enable reliable audio capture, efficient transmission, and integration with the Wyoming protocol and Whisper STT.

**Key Deliverables:**
- Audio recording from ESP32-S3-BOX-3B microphone (16kHz, 16-bit mono)
- Efficient PCM buffer management with circular buffers
- Audio stream transmission via Wyoming protocol
- Whisper STT integration for real-time speech-to-text
- Audio quality optimization and noise management
- Error handling and network recovery
- Push-to-talk and wake-word detection workflows

**Acceptance Criteria:**
- [ ] Audio recording from box3b microphone at 16kHz 16-bit mono
- [ ] PCM buffer maintained with <500ms latency
- [ ] Audio packets streamed reliably to backend
- [ ] Whisper STT integration <3 second latency for typical speech
- [ ] Recording quality acceptable for speech recognition (>90% accuracy)
- [ ] System handles continuous recording for 8+ hours
- [ ] Error recovery from network issues functional

**Testing Criteria:**
- [ ] Full audio chain working end-to-end
- [ ] Recording quality acceptable
- [ ] Latency <500ms for complete chain
- [ ] No data loss under normal conditions
- [ ] System stable over 8+ hours
- [ ] Whisper accuracy >90%

---

### Epic 8: Receiving & Audio Playback

**Status:** Planned
**Estimated Duration:** 1.5 weeks
**Depends On:** Epic 7
**Reference:** `dev_notes/project_plans/2026-03-24_epic-8-receiving-audio-playback.md`

**Purpose:** Implement the return audio path, enabling the backend to send audio responses back to the ESP32-S3-BOX-3B for playback through the speaker. Completes the bidirectional audio flow and adds transition sounds (start/end/error tones).

**Key Deliverables:**
- I2S audio output driver for ESP32-S3-BOX-3B speaker
- PCM audio reception from backend via Wyoming protocol
- Playback buffer management
- Transition sounds (beep/click on state changes)
- Volume control (configurable via ESPHome YAML)
- Concurrent recording/playback handling

**Acceptance Criteria:**
- [ ] Audio received from backend without data loss
- [ ] Playback latency <1 second from reception
- [ ] Speaker output at appropriate volume levels
- [ ] Transition sounds working correctly (blue→red, green→blue)
- [ ] No interference between recording and playback
- [ ] Volume control functional and persistent
- [ ] Error audio played on failures

**Testing Criteria:**
- [ ] Full bidirectional audio chain end-to-end
- [ ] Transition sound quality and timing
- [ ] Volume control accuracy
- [ ] Concurrent recording and playback stability
- [ ] Network failure recovery during playback

---

### Epic 9: Touchscreen Integration & Device Coordination

**Status:** Planned
**Estimated Duration:** 3 weeks
**Depends On:** Epic 8
**Research:** Arduino vs. ESPHome approaches - evaluate both, decide based on findings

**Purpose:** Integrate touchscreen interface for device interaction and enable multiple Chatterbox devices to coordinate, share context, and provide room-aware functionality.

**Key Deliverables:**
- Touchscreen UI for device interaction
- Device discovery and registration
- Room detection and location-aware responses
- Shared conversation context across devices
- Device-to-device communication protocol
- Multi-device conversation coordination
- Distributed state synchronization
- Architectural decision: Arduino vs. ESPHome with justification

**Acceptance Criteria:**
- [ ] Touchscreen interface functional and responsive
- [ ] Devices auto-discover each other
- [ ] Room-aware responses working
- [ ] Context shared between devices
- [ ] Latency acceptable for distributed system
- [ ] Failover handling for device loss
- [ ] Arduino/ESPHome evaluation documented with decision rationale

**Testing Criteria:**
- [ ] Touchscreen responsiveness and accuracy
- [ ] Discovery consistency
- [ ] Room detection accuracy
- [ ] Context synchronization correctness
- [ ] Failover recovery time
- [ ] Network failure handling

---

### Epic 10: Continuous Conversation & Wake Word (LOCAL)

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 9
**Wake Word Strategy:** Use box3b's LOCAL voice model (no streaming to Home Assistant)

**Purpose:** Implement always-listening wake word detection and continuous conversation capabilities. Device listens for customizable wake word locally (using box3b's built-in voice model), automatically transitions to recording, processes audio through the full pipeline, and returns to idle listening after conversation completes.

**Key Deliverables:**
- Always-listening wake word detection using box3b LOCAL model
- Support for custom/configurable wake words
- Automatic state transitions on wake detection
- 5-second red light "listening" indicator
- False positive/negative mitigation and calibration
- Continuous conversation workflows
- Low power consumption in listen mode
- Integration with existing voice pipeline

**Acceptance Criteria:**
- [ ] Wake word detection latency <500ms
- [ ] False positive rate <2% (1 per 50 utterances)
- [ ] False negative rate <10% (1 per 10 wake words)
- [ ] Red light activates within 100ms of wake
- [ ] Red light deactivates appropriately after response
- [ ] Multiple wake words supported
- [ ] Continuous conversation without push-button
- [ ] Power consumption in listen mode <500mW
- [ ] LOCAL model (no HA streaming) confirmed working

**Testing Criteria:**
- [ ] Wake word detection >95% accuracy
- [ ] False positive/negative rate validation
- [ ] Extended operation stability (8+ hours)
- [ ] Power consumption measurements
- [ ] LED behavior verification
- [ ] Continuous conversation workflows tested

---

### Epic 11: Reliability & LLM Fallback

**Status:** Planned
**Estimated Duration:** 2 weeks
**Depends On:** Epic 10
**Reference:** `dev_notes/project_plans/2026-03-24_epic-11-reliability-llm-fallback.md`

**Purpose:** Implement production-grade reliability with multi-LLM provider support and automatic fallback. System gracefully handles provider outages, rate limits, and cost overruns. Falls back through a chain of providers (primary → secondary → local Ollama fallback).

**Key Deliverables:**
- Multi-LLM provider abstraction layer (OpenAI, Anthropic, Ollama, etc.)
- Automatic provider failover on failure/rate-limit
- Cost tracking and budget enforcement
- Local Ollama fallback for offline/degraded operation
- Health checks and provider monitoring
- Graceful degradation with user-visible status

**Acceptance Criteria:**
- [ ] At least 2 LLM providers integrated and working
- [ ] Failover latency <2 seconds
- [ ] Fallback trigger accuracy >95%
- [ ] Cost tracking accurate to within 1%
- [ ] Local fallback provides reasonable responses
- [ ] Service uptime >99.5% despite provider issues
- [ ] Automatic recovery from transient failures

**Testing Criteria:**
- [ ] Provider failover simulation
- [ ] Cost tracking accuracy under load
- [ ] Local fallback quality validation
- [ ] Recovery from network partition
- [ ] Budget enforcement testing

---

### Epic 12: Long-Term Maintenance & Community

**Status:** Planned
**Estimated Duration:** Ongoing
**Depends On:** Epic 11

**Purpose:** Establish sustainable maintenance practices and community engagement.

**Key Deliverables:**
- Comprehensive documentation
- Community contribution guidelines
- Issue triage and prioritization process
- Dependency management and updates
- Long-term feature roadmap
- Support and troubleshooting resources

**Acceptance Criteria:**
- [ ] Documentation complete and accessible
- [ ] Contribution guidelines clear
- [ ] Issue process established
- [ ] Community feedback loop working
- [ ] Roadmap public and updated regularly

**Testing Criteria:**
- [ ] Documentation accuracy
- [ ] Contribution workflow validation
- [ ] Issue tracking effectiveness
- [ ] Community engagement metrics
- [ ] Roadmap alignment with user needs

---

## Dependency Graph

```
Epic 1 (OTA & Foundation)
    ↓
Epic 2 (Observability & Serial Logging)
    ↓
Epic 3 (Wyoming Protocol & Testing) ✅
    ↓
Epic 4 (LLM Integration) ✅
    ↓
Epic 5 (Context Persistence)
    ↓
Epic 6 (Backend Deployment & HA Connection)
    ↓
Epic 7 (Recording & PCM Streaming)
    ↓
Epic 8 (Receiving & Audio Playback)
    ↓
Epic 9 (Touchscreen Integration & Device Coordination)
    ↓
Epic 10 (Continuous Conversation & Wake Word)
    ↓
Epic 11 (Reliability & LLM Fallback)
    ↓
Epic 12 (Documentation & Maintenance)
```

**Critical Path:** Epics 1-4 must complete sequentially before proceeding with 5-12.

---

## Timeline and Sequencing

### Phase 1: Foundation (Weeks 1-4)
- **Epic 1:** OTA & Foundation (Weeks 1-2) [READY FOR TESTING]
- **Epic 2:** Observability & Serial Logging (Weeks 3-4) [PLANNED]

### Phase 2: Infrastructure (Weeks 5-10)
- **Epic 3:** Wyoming Protocol & Testing (Weeks 5-7) [COMPLETE]
- **Epic 4:** LLM Integration (Weeks 8-10) [COMPLETE]

### Phase 3: Enhancement (Weeks 11-16)
- **Epic 5:** Context Persistence (Weeks 11-12) [PLANNED]
- **Epic 6:** Backend Deployment & HA Connection (Weeks 13-14) [PLANNED]
- **Epic 7:** Recording & PCM Streaming (Weeks 15-16) [PLANNED]

### Phase 4: Expansion (Weeks 17-21)
- **Epic 8:** Receiving & Audio Playback (Weeks 17-18) [PLANNED]
- **Epic 9:** Touchscreen Integration & Device Coordination (Weeks 19-21) [PLANNED]

### Phase 5: Production (Weeks 22-26)
- **Epic 10:** Continuous Conversation & Wake Word (Weeks 22-23) [PLANNED]
- **Epic 11:** Reliability & LLM Fallback (Weeks 24-25) [PLANNED]

### Phase 6: Maintenance (Ongoing)
- **Epic 12:** Documentation & Maintenance (Ongoing) [PLANNED]

**Total Estimated Timeline:** ~6.5 months to production readiness (including buffer)

---

## Testing Criteria by Epic

### Testing Progression by Epic

| Epic | Unit Tests | Integration Tests | End-to-End Tests | Performance Tests |
|------|-----------|------------------|-----------------|------------------|
| 1 | ✓ | ✓ | ✓ | — |
| 2 | ✓ | ✓ | ✓ | ✓ |
| 3 | ✓ | ✓ | ✓ | ✓ |
| 4 | ✓ | ✓ | ✓ | ✓ |
| 5 | ✓ | ✓ | ✓ | ✓ |
| 6 | ✓ | ✓ | ✓ | ✓ |
| 7 | ✓ | ✓ | ✓ | ✓ |
| 8 | ✓ | ✓ | ✓ | ✓ |
| 9 | ✓ | ✓ | ✓ | ✓ |
| 10 | ✓ | ✓ | ✓ | ✓ |
| 11 | ✓ | ✓ | ✓ | ✓ |
| 12 | — | — | ✓ | — |

### Key Quality Gates

**Before Epic Completion:**
1. All acceptance criteria met
2. All tests passing (unit, integration, end-to-end)
3. Code review approved
4. Documentation complete
5. No critical known issues

**Before Next Epic Start:**
1. Previous epic passed quality review
2. Dependencies resolved
3. Team capacity allocated
4. Success metrics established

---

## Epic Completion Status Summary

**Completed Epics:**
- ✅ Epic 3: Wyoming Protocol & Testing (2026-02-19)
- ✅ Epic 4: LLM Integration (2026-02-20)

**Ready for Testing:**
- 🔄 Epic 1: OTA & Foundation (in progress, ready for testing phase)

**Planned:**
- ⏳ Epics 2, 5-12

**Total Progress:** 2/12 complete, 1/12 ready for testing, 9/12 planned

---

## References

### Completed Epic Plans
- **Epic 1 Plan:** `dev_notes/project_plans/2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md`
- **Epic 3-4 Plan:** `dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md`

### Planned Epic Plans
- **Epic 2 Plan:** `dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md`
- **Epic 5 Plan:** `dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md`
- **Epic 6 Plan:** `dev_notes/project_plans/2026-03-24_epic-6-backend-deployment-ha-connection.md`
- **Epic 7 Plan:** `dev_notes/project_plans/2026-03-24_epic-7-recording-pcm-streaming.md`
- **Epic 8 Plan:** `dev_notes/project_plans/2026-03-24_epic-8-receiving-audio-playback.md`
- **Epic 9 Plan:** `dev_notes/project_plans/2026-03-24_epic-9-touchscreen-integration.md`
- **Epic 10 Plan:** `dev_notes/project_plans/2026-03-24_epic-10-continuous-conversation-wake-word.md`
- **Epic 11 Plan:** `dev_notes/project_plans/2026-03-24_epic-11-reliability-llm-fallback.md`
- **Epic 12 Plan:** `dev_notes/project_plans/2026-03-24_epic-12-documentation-maintenance.md`

### Supporting Documents
- **Clarifications & Decisions:** `dev_notes/project_plans/2026-03-24_clarifications-summary.md`
- **Mellona Migration (Epic 5 Prerequisite):** `dev_notes/project_plans/2026-02-25_mellona-migration-project-plan.md`
- **Context Persistence Proposal (Epic 5 Background):** `docs/epic5-context-persistence-proposal.md`
- **Chatterbox Architecture:** `docs/architecture.md`
- **Project README:** `README.md`

---

**Document Owner:** Chatterbox Project Team
**Last Updated:** 2026-03-24
