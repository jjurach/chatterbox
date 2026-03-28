# Cackle Chatterbox: Master Project Plan

**Document ID:** MASTER-CHATTERBOX-2026
**Purpose:** Index and roadmap for all 12 epics in the Chatterbox voice assistant project
**Status:** Active
**Last Updated:** 2026-03-24

---

## Purpose Statement

This master plan guides implementation of the Cackle Chatterbox voice assistant, from hardware foundation through production reliability. It coordinates 12 sequentially dependent epics that transform the ESP32-S3-BOX-3B into a fully-capable, production-ready voice assistant integrated with Home Assistant.

---

## Quick Navigation

- **Source of truth (all epics):** [docs/epics-plan.md](../../docs/epics-plan.md)
- **Clarifications & decisions:** [2026-03-24_clarifications-summary.md](2026-03-24_clarifications-summary.md)
- **Epic 1 details:** [2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md](2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md)
- **Epic 2 details:** [2026-03-24_epic-2-observability-monitoring.md](2026-03-24_epic-2-observability-monitoring.md)
- **Epics 3-4 details:** [2026-02-18_epic-3-4-wyoming-llm-project-plan.md](2026-02-18_epic-3-4-wyoming-llm-project-plan.md)
- **Epic 5 details:** [2026-03-24_epic-5-persistent-conversation-context.md](2026-03-24_epic-5-persistent-conversation-context.md)
- **Epic 6 details:** [2026-03-24_epic-6-backend-deployment-ha-connection.md](2026-03-24_epic-6-backend-deployment-ha-connection.md)
- **Epic 7 details:** [2026-03-24_epic-7-recording-pcm-streaming.md](2026-03-24_epic-7-recording-pcm-streaming.md)
- **Epic 8 details:** [2026-03-24_epic-8-receiving-audio-playback.md](2026-03-24_epic-8-receiving-audio-playback.md)
- **Epic 9 details:** [2026-03-24_epic-9-touchscreen-integration.md](2026-03-24_epic-9-touchscreen-integration.md)
- **Epic 10 details:** [2026-03-24_epic-10-continuous-conversation-wake-word.md](2026-03-24_epic-10-continuous-conversation-wake-word.md)
- **Epic 11 details:** [2026-03-24_epic-11-reliability-llm-fallback.md](2026-03-24_epic-11-reliability-llm-fallback.md)
- **Epic 12 details:** [2026-03-24_epic-12-documentation-maintenance.md](2026-03-24_epic-12-documentation-maintenance.md)
- **Project architecture:** [docs/architecture.md](../../docs/architecture.md)

---

## Epic Registry

### Epic 1: OTA & Foundation
**Status:** Ready for Testing | **Target Completion:** 2026-03-31

Establish foundational infrastructure for device state machine, OTA updates, and OCR-based validation.

**Key Deliverables:**
- Device state machine MVP (6 states: N, H, S, A, W, P)
- OTA deployment tool (Python CLI)
- OCR validator tool (/dev/video0 input)
- Secure password-protected OTA endpoint

**Team Effort:** ~50 hours
**Next:** Epic 2 (Wake Word Detection)
**Plan File:** [2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md](2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md)

---

### Epic 2: Observability & Serial Logging
**Status:** Planned | **Target Completion:** 2026-04-14

Establish serial logging infrastructure for device observability, troubleshooting, and monitoring. Phase 1 focuses on reliable serial logging; Home Assistant dashboard integration deferred to Phase 2.

**Key Deliverables:**
- Structured serial logging schema (JSON format, configurable levels)
- Serial logging integration on ESP32 firmware (all state transitions, audio, network events)
- Serial log capture service (Python background service with log rotation)
- `chatterbox-logs` CLI utility (capture, view, search, export sub-commands)
- Performance overhead <5% CPU impact

**Team Effort:** ~80 hours
**Depends On:** Epic 1
**Next:** Epic 3 (Wyoming Protocol & Testing)
**Plan File:** [2026-03-24_epic-2-observability-monitoring.md](2026-03-24_epic-2-observability-monitoring.md)

---

### Epic 3: Wyoming Protocol & Testing Infrastructure
**Status:** Complete (2026-02-19) | **Completion Date:** 2026-02-19

Validate Wyoming protocol implementation and establish comprehensive testing infrastructure for Home Assistant.

**Key Deliverables:**
- Wyoming protocol documentation and conversation flow mapping
- Home Assistant emulator for autonomous testing
- Whisper STT service validation (>90% accuracy)
- Piper TTS service validation and integration
- Test wave file corpus (15+ samples)
- Round-trip integration testing framework

**Team Effort:** ~120 hours
**Depends On:** Epic 2
**Completion Rationale:** All acceptance criteria met; full validation infrastructure operational
**Plan File:** [2026-02-18_epic-3-4-wyoming-llm-project-plan.md](2026-02-18_epic-3-4-wyoming-llm-project-plan.md)

---

### Epic 4: LLM Integration & Conversational AI
**Status:** Complete (2026-02-20) | **Completion Date:** 2026-02-20

Implement stateful, agentic conversation loop with LLM inference and tool calling capabilities.

**Key Deliverables:**
- Agentic conversation loop (LangChain/LangGraph-based)
- State machine for LLM inference and tool invocation
- Weather tool as reference implementation
- System prompt framework for LLM behavior customization
- In-memory context management
- Wyoming protocol integration (STT → LLM → TTS pipeline)
- End-to-end conversation testing (<5s latency for simple queries)

**Team Effort:** ~120 hours
**Depends On:** Epic 3
**Completion Rationale:** All acceptance criteria met; tool framework extensible; error handling robust
**Plan File:** [2026-02-18_epic-3-4-wyoming-llm-project-plan.md](2026-02-18_epic-3-4-wyoming-llm-project-plan.md)

---

### Epic 5: Context Persistence & History Management
**Status:** Planned | **Target Completion:** 2026-05-12

Implement persistent conversation history so context survives process restarts and enables cross-session awareness.

**Key Deliverables:**
- SQLite backend (Phase 1); PostgreSQL migration path via storage abstraction layer
- Conversation history retrieval and tracking with multi-turn context
- TTL-based retention policy with automatic purging (default 30 days)
- Context search tool for LLM queries (<200ms latency)
- Multi-user conversation isolation
- Storage abstraction interface enabling backend swapping

**Estimated Effort:** ~41 hours
**Depends On:** Epic 4; **Prerequisite:** Mellona integration (see [2026-02-25_mellona-migration-project-plan.md](2026-02-25_mellona-migration-project-plan.md))
**Next:** Epic 6 (Backend Deployment & HA Connection)
**Plan File:** [2026-03-24_epic-5-persistent-conversation-context.md](2026-03-24_epic-5-persistent-conversation-context.md)

---

### Epic 6: Backend Deployment & Home Assistant Connection
**Status:** Planned | **Target Completion:** 2026-05-26

Establish production-ready backend deployment with Docker and robust Home Assistant Wyoming integration.

**Key Deliverables:**
- Dockerfile with multi-stage builds for backend service
- docker-compose.yml for complete system orchestration (`docker-compose up` brings everything online)
- Stable Wyoming protocol connection to Home Assistant (auto-recovery)
- Multi-device deployment support with load balancing
- Rollback procedures without data loss

**Estimated Effort:** ~50 hours
**Depends On:** Epic 5
**Next:** Epic 7 (Recording & PCM Streaming)
**Plan File:** [2026-03-24_epic-6-backend-deployment-ha-connection.md](2026-03-24_epic-6-backend-deployment-ha-connection.md)

---

### Epic 7: Recording & PCM Streaming
**Status:** Planned | **Target Completion:** 2026-06-09

Implement voice recording on the ESP32-S3-BOX-3B and PCM packet transmission through the Wyoming protocol to Whisper STT.

**Key Deliverables:**
- Audio recording from box3b microphone (16kHz, 16-bit mono)
- Efficient PCM buffer management with circular buffers
- Audio stream transmission via Wyoming protocol
- Whisper STT integration (real-time speech-to-text)
- Push-to-talk and wake-word recording workflows
- `chatterbox-logs` serial log utility (separate CLI tool)

**Estimated Effort:** ~50 hours
**Depends On:** Epic 6
**Next:** Epic 8 (Receiving & Audio Playback)
**Plan File:** [2026-03-24_epic-7-recording-pcm-streaming.md](2026-03-24_epic-7-recording-pcm-streaming.md)

---

### Epic 8: Receiving & Audio Playback
**Status:** Planned | **Target Completion:** 2026-06-30

Implement the return audio path — backend sends TTS audio back to device for speaker playback. Completes bidirectional audio flow.

**Key Deliverables:**
- I2S audio output driver for ESP32-S3-BOX-3B speaker
- PCM audio reception from backend via Wyoming protocol
- Playback buffer management (<1s latency)
- Transition sounds (beep/click on state changes, configurable in ESPHome YAML)
- Volume control (persistent, configurable)
- Concurrent recording/playback handling

**Estimated Effort:** ~60 hours
**Depends On:** Epic 7
**Next:** Epic 9 (Touchscreen Integration & Device Coordination)
**Plan File:** [2026-03-24_epic-8-receiving-audio-playback.md](2026-03-24_epic-8-receiving-audio-playback.md)

---

### Epic 9: Touchscreen Integration & Device Coordination
**Status:** Planned | **Target Completion:** 2026-07-21

Integrate touchscreen interface for device interaction and enable multi-device coordination with room-aware responses.

**Key Deliverables:**
- Touchscreen UI for device interaction (screen-specific buttons per state)
- Device discovery and registration
- Room detection and location-aware responses
- Shared conversation context across devices
- Architectural decision: Arduino vs. ESPHome (evaluate both, document rationale)

**Estimated Effort:** ~90 hours
**Depends On:** Epic 8
**Next:** Epic 10 (Continuous Conversation & Wake Word)
**Plan File:** [2026-03-24_epic-9-touchscreen-integration.md](2026-03-24_epic-9-touchscreen-integration.md)

---

### Epic 10: Continuous Conversation & Wake Word
**Status:** Planned | **Target Completion:** 2026-08-04

Implement always-listening wake word detection (LOCAL on device, no HA streaming) and 5-second continuation window for follow-up speech.

**Key Deliverables:**
- Always-listening wake word using box3b's LOCAL voice model (no streaming to HA)
- Configurable wake words
- Automatic state transitions on wake detection (<500ms latency)
- 5-second red-light continuation window (speech detected → continues interaction)
- Power consumption <500mW in listen mode

**Estimated Effort:** ~50 hours
**Depends On:** Epic 9
**Next:** Epic 11 (Reliability & LLM Fallback)
**Plan File:** [2026-03-24_epic-10-continuous-conversation-wake-word.md](2026-03-24_epic-10-continuous-conversation-wake-word.md)

---

### Epic 11: Reliability & LLM Fallback
**Status:** Planned | **Target Completion:** 2026-08-18

Implement multi-LLM provider support with automatic failover. System cycles through provider chain (primary → secondary → local Ollama) on failure, with cost tracking and budget enforcement.

**Key Deliverables:**
- Multi-LLM provider abstraction (OpenAI, Anthropic, Ollama, etc.)
- Automatic failover with <2s transition latency
- Cost tracking accurate to within 1%
- Local Ollama fallback for offline/degraded operation
- Health checks and provider monitoring
- Context length tracking per LLM profile

**Target Availability:** >99.5% service uptime
**Estimated Effort:** ~80 hours
**Depends On:** Epic 10
**Next:** Epic 12 (Documentation & Maintenance)
**Plan File:** [2026-03-24_epic-11-reliability-llm-fallback.md](2026-03-24_epic-11-reliability-llm-fallback.md)

---

### Epic 12: Documentation & Maintenance
**Status:** Planned | **Duration:** Ongoing after Epic 11

Archiving, compacting history, reducing documentation clutter, and setting up long-term project sustainability.

**Key Deliverables:**
- Comprehensive documentation review and cleanup
- Community contribution guidelines
- Issue triage and prioritization process
- Dependency management and update strategy
- Long-term feature roadmap
- Support and troubleshooting resources

**Ongoing Activities:**
- Regular dependency updates
- Documentation maintenance and deduplication
- Performance monitoring and optimization

**Estimated Effort:** Ongoing
**Depends On:** Epic 11
**Plan File:** [2026-03-24_epic-12-documentation-maintenance.md](2026-03-24_epic-12-documentation-maintenance.md)

---

## Dependency Graph

```
Epic 1: OTA & Foundation
        ↓
Epic 2: Observability & Serial Logging
        ↓
Epic 3: Wyoming Protocol & Testing ✅
        ↓
Epic 4: LLM Integration ✅
        ↓
Epic 5: Context Persistence ⏳
        ↓
Epic 6: Backend Deployment & HA Connection ⏳
        ↓
Epic 7: Recording & PCM Streaming ⏳
        ↓
Epic 8: Receiving & Audio Playback ⏳
        ↓
Epic 9: Touchscreen Integration & Device Coordination ⏳
        ↓
Epic 10: Continuous Conversation & Wake Word ⏳
        ↓
Epic 11: Reliability & LLM Fallback ⏳
        ↓
Epic 12: Documentation & Maintenance ⏳
```

**Critical Path:** Epics 1-4 must complete sequentially (foundation and protocol layers required before LLM integration).

**Parallel Opportunities:** None (fully sequential due to architectural dependencies).

---

## Timeline Overview

### Phase 1: Foundation & Observability (Weeks 1-4)
- Week 1-2: Epic 1 - OTA & Foundation
- Week 3-4: Epic 2 - Observability & Serial Logging

### Phase 2: Protocol & Intelligence (Weeks 5-10)
- Week 5-7: Epic 3 - Wyoming Protocol & Testing ✅
- Week 8-10: Epic 4 - LLM Integration ✅

### Phase 3: Enhancement (Weeks 11-16)
- Week 11-12: Epic 5 - Context Persistence
- Week 13-14: Epic 6 - Backend Deployment & HA Connection
- Week 15-16: Epic 7 - Recording & PCM Streaming

### Phase 4: Audio & Device (Weeks 17-21)
- Week 17-18: Epic 8 - Receiving & Audio Playback
- Week 19-21: Epic 9 - Touchscreen Integration & Device Coordination

### Phase 5: Continuous Conversation & Reliability (Weeks 22-25)
- Week 22-23: Epic 10 - Continuous Conversation & Wake Word
- Week 24-25: Epic 11 - Reliability & LLM Fallback

### Phase 6: Ongoing (Beyond 25 weeks)
- Epic 12 - Documentation & Maintenance

**Total Estimated Duration:** ~6.5 months to production readiness

---

## Success Metrics by Phase

### Phase 1: Foundation (Weeks 1-4)
- [ ] Epic 1 ready for testing
- [ ] State machine MVP functional
- [ ] OTA deployment tool operational
- [ ] OCR validator >95% accurate
- [ ] Serial logging capturing all state transitions

### Phase 2: Intelligence (Weeks 5-10)
- [x] Wyoming protocol fully validated
- [x] End-to-end conversation latency <5s
- [x] Tool framework extensible
- [x] Weather tool operational

### Phase 3: Enhancement (Weeks 11-16)
- [ ] Persistent context working (SQLite backend)
- [ ] Docker deployment operational
- [ ] Device recording and PCM streaming working

### Phase 4: Audio & Device (Weeks 17-21)
- [ ] Bidirectional audio working (record + playback)
- [ ] Touchscreen interface functional
- [ ] Multi-device discovery working

### Phase 5: Continuous Conversation & Reliability (Weeks 22-25)
- [ ] Wake word detection LOCAL on device
- [ ] 5-second continuation window working
- [ ] Multi-LLM fallback operational
- [ ] System availability >99.5%

### Phase 6: Mature (Ongoing)
- [ ] Documentation reviewed and deduplicated
- [ ] Regular dependency updates
- [ ] Support documentation comprehensive

---

## Key Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Dependency delays from other projects | Medium | High | Build detailed task breakdown; identify blockers early |
| Performance issues in later epics | Medium | High | Implement perf. testing from Epic 6 onward |
| Scope creep in tool ecosystem | Medium | Medium | Strict acceptance criteria per epic |
| Multi-device coordination complexity | High | Medium | Start with simple discovery; iterate |
| Security gaps in production | Medium | High | Security epic (10) before production (11) |
| Community adoption challenges | Low | Low | Documentation and examples key (Epic 12) |

---

## Approval & Sign-Off

**Project Sponsor:** [To be assigned]
**Technical Lead:** [To be assigned]
**QA Owner:** [To be assigned]

**Approved By:**
- [ ] Sponsor
- [ ] Technical Lead
- [ ] QA Owner

**Date Approved:** _______________

---

## References & Resources

### Key Documentation
- **Source of truth (all epics):** [docs/epics-plan.md](../../docs/epics-plan.md)
- **Clarifications & decisions:** [2026-03-24_clarifications-summary.md](2026-03-24_clarifications-summary.md)
- **Epic 5 background proposal:** [docs/epic5-context-persistence-proposal.md](../../docs/epic5-context-persistence-proposal.md)

### Epic Plan Files
- **Epic 1:** [2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md](2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md)
- **Epic 2:** [2026-03-24_epic-2-observability-monitoring.md](2026-03-24_epic-2-observability-monitoring.md)
- **Epics 3-4:** [2026-02-18_epic-3-4-wyoming-llm-project-plan.md](2026-02-18_epic-3-4-wyoming-llm-project-plan.md)
- **Epic 5:** [2026-03-24_epic-5-persistent-conversation-context.md](2026-03-24_epic-5-persistent-conversation-context.md)
- **Epic 6:** [2026-03-24_epic-6-backend-deployment-ha-connection.md](2026-03-24_epic-6-backend-deployment-ha-connection.md)
- **Epic 7:** [2026-03-24_epic-7-recording-pcm-streaming.md](2026-03-24_epic-7-recording-pcm-streaming.md)
- **Epic 8:** [2026-03-24_epic-8-receiving-audio-playback.md](2026-03-24_epic-8-receiving-audio-playback.md)
- **Epic 9:** [2026-03-24_epic-9-touchscreen-integration.md](2026-03-24_epic-9-touchscreen-integration.md)
- **Epic 10:** [2026-03-24_epic-10-continuous-conversation-wake-word.md](2026-03-24_epic-10-continuous-conversation-wake-word.md)
- **Epic 11:** [2026-03-24_epic-11-reliability-llm-fallback.md](2026-03-24_epic-11-reliability-llm-fallback.md)
- **Epic 12:** [2026-03-24_epic-12-documentation-maintenance.md](2026-03-24_epic-12-documentation-maintenance.md)

### Architecture & Design
- **System Architecture:** [docs/architecture.md](../../docs/architecture.md)
- **Implementation Patterns:** [docs/implementation-reference.md](../../docs/implementation-reference.md)
- **Definition of Done:** [docs/definition-of-done.md](../../docs/definition-of-done.md)

### External Resources
- **Wyoming Protocol Docs:** https://www.rhasspy.org/wyoming/
- **Home Assistant:** https://www.home-assistant.io/
- **ESP32-S3-BOX-3B:** https://github.com/espressif/esp-box
- **LangChain Docs:** https://python.langchain.com/

---

**Document Owner:** Chatterbox Project Team
**Last Updated:** 2026-03-24
**Next Review Date:** 2026-04-14 (Epic 1 completion)
