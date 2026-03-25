# Chatterbox Epic Planning: Clarifications Summary
**Document Date:** 2026-03-24
**Purpose:** Record explicit user preferences for Epic implementation strategy

---

## Overview
This document captures 9 key clarifications provided by the project stakeholder regarding Epic implementation strategy. These decisions establish firm technical direction for the 12-epic Chatterbox project and should be referenced during implementation planning and execution.

---

## Clarification 1: Epic 6 - Docker + Docker Compose Deployment Strategy
**Epic:** 6 (Backend Deployment & Home Assistant Connection)
**Decision:** Use Docker and Docker Compose for production deployment

**Implementation Direction:**
- **Docker:** Multi-stage builds for optimized images
  - Minimize image size for efficient distribution
  - Health checks integrated into container configuration
  - Build time target: <5 minutes per image

- **Docker Compose:** Single-file orchestration of entire system
  - `docker-compose up` brings entire backend online
  - Includes: backend service, SQLite/PostgreSQL database, supporting services
  - Enables: multi-device deployments with load balancing
  - Single-command deployment for new instances (<15 minutes)

- **Scalability:** Multi-device architecture from day 1
  - Deployment automation for multiple Chatterbox instances
  - Rollback procedures without data loss
  - Production-grade operational procedures documented

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-6-backend-deployment-ha-connection.md`

---

## Clarification 2: Epic 9 - Evaluate Both Arduino + ESPHome, Decide Based on Findings
**Epic:** 9 (Touchscreen Integration & Device Coordination)
**Decision:** Research and evaluate both Arduino and ESPHome approaches; make selection decision based on technical findings

**Implementation Direction:**
- **Research Phase:** Create evaluation matrix comparing:
  - Arduino approach: native C++ implementation, direct hardware control
  - ESPHome approach: YAML-based configuration, abstraction layer
  - Decision criteria: performance, maintainability, flexibility, complexity

- **Evaluation Outputs:**
  - Feature comparison (touchscreen support, device coordination, integration ease)
  - Resource requirements (ROM, RAM, CPU)
  - Development velocity and code maintainability
  - Community support and documentation

- **Decision Point:** Document rationale for chosen approach with alternatives considered
  - This decision affects firmware architecture and testing strategy
  - Must be documented in Epic 9 completion deliverables

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-9-touchscreen-integration.md`

---

## Clarification 3: Epic 1 - Device Available Now (USB Connected)
**Epic:** 1 (OTA & Foundation)
**Status:** Hardware available for immediate testing

**Implementation Direction:**
- **Hardware Available:** ESP32-S3-BOX-3B device currently connected via USB
  - Enables real hardware testing immediately without waiting for device procurement
  - Parallel firmware development and physical validation
  - OCR validation tool can test against actual display output

- **Testing Advantage:** Real device testing possible now
  - State machine transitions can be validated on physical hardware
  - Display rendering can be validated with actual display and lighting
  - OTA deployment can be tested against real device
  - No need to estimate/simulate hardware behavior

- **Schedule Impact:** Can accelerate Epic 1 timeline
  - Early discovery of hardware-specific issues
  - Confidence in OTA mechanisms before full system integration
  - Foundation for downstream epics (Epics 2-4 depend on stable Epic 1)

**Reference Files:**
- `docs/epics-plan.md` (Epic 1 section)

---

## Clarification 4: Mellona - High Priority Integration BEFORE Epic 5
**Prerequisite:** Epic 5 (Persistent Conversation Context)
**Decision:** Mellona STT/TTS integration is HIGH PRIORITY and MUST complete before Epic 5

**Implementation Direction:**
- **Mellona STT/TTS Already Implemented:**
  - No need to build STT/TTS from scratch
  - Mellona provides production-quality speech recognition and synthesis
  - Already integrated in the codebase; use existing capabilities

- **Strategic Importance:**
  - Epic 4 (LLM Integration) provides agentic framework
  - Mellona provides audio I/O capabilities
  - Epic 5 depends on both for persistent context with audio metadata

- **Blocking Dependency:**
  - Do NOT start Epic 5 conversation persistence until Mellona integration confirmed working
  - Context persistence requires reliable audio I/O from Mellona
  - Audio metadata (confidence scores, language detection) enhances context storage

- **Pre-Epic-5 Checklist:**
  - [ ] Mellona STT/TTS fully integrated and tested
  - [ ] Audio quality validated (>90% accuracy)
  - [ ] Integration with Wyoming protocol confirmed
  - [ ] Performance baselines established
  - [ ] Documentation complete for context persistence team

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md` (Prerequisite section)

---

## Clarification 5: Epic 5 - SQLite Backend First, PostgreSQL as Future Migration
**Epic:** 5 (Persistent Conversation Context)
**Decision:** Implement SQLite for Phase 1; plan PostgreSQL migration path for future scalability

**Implementation Direction:**
- **Phase 1 (SQLite) - This Epic:**
  - Single file-based database (database.db)
  - Ideal for single-device or development deployments
  - No external dependencies (database included in deployment)
  - Sufficient performance for typical conversation volumes (100s-1000s of messages)
  - Simple operational model: copy file for backup/restore

- **Phase 2 (PostgreSQL) - Future Scalability:**
  - Enables distributed deployments across multiple devices
  - Horizontal scaling capability for high-volume scenarios
  - Advanced features: full-text search, JSONB columns, replication
  - Can be adopted when scaling needs arise

- **Storage Abstraction Layer (Critical):**
  - Design abstract `StorageBackend` interface during Epic 5
  - Implement SQLite behind abstraction
  - Document PostgreSQL implementation for Phase 2
  - Enable backend swapping without application code changes

- **Migration Path:**
  - Data schema compatible with both SQLite and PostgreSQL
  - Migration scripts prepared for future transition
  - No breaking changes to application API when switching backends

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md` (Backend Strategy section, Task 5.1)

---

## Clarification 6: Epic 7 - Serial Logging as Separate Utility Script with Sub-commands
**Epic:** 7 (Recording & PCM Streaming)
**Decision:** Serial logging tool is a standalone utility with multiple sub-commands

**Implementation Direction:**
- **Separate Utility Script:** Not integrated into main application
  - Standalone Python CLI tool: `chatterbox-logs`
  - Independent deployment and versioning
  - Can be used for debugging without running full Chatterbox service

- **Multiple Sub-commands:**
  ```bash
  chatterbox-logs capture --port /dev/ttyUSB0 --output logs/
  chatterbox-logs view [--tail] [--filter module=AUDIO]
  chatterbox-logs search --query "error" --date-range "today"
  chatterbox-logs export --format csv --output report.csv
  ```

- **Use Cases:**
  - Operator troubleshooting without full stack
  - Historical analysis of device behavior
  - Integration with other monitoring tools
  - Automated log aggregation scripts

- **Serial Logging as Phase 1 (Epic 2):**
  - Firmware provides structured JSON logs to serial port
  - `chatterbox-logs` utility captures and manages these logs
  - Phase 2 (future): Home Assistant integration, databases, web UI
  - Current approach: focus on reliable serial logging foundation

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-7-recording-pcm-streaming.md` (Executive Summary)
- `dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md` (Phase 1 vs Phase 2)

---

## Clarification 7: Epic 10 - Use box3b's LOCAL Voice Model (No HA Streaming)
**Epic:** 10 (Continuous Conversation & Wake Word)
**Decision:** Use box3b's built-in LOCAL voice model for wake word detection

**Implementation Direction:**
- **LOCAL Processing:** Wake word detection happens entirely on device
  - Model inference runs on ESP32-S3-BOX-3B
  - No streaming audio to Home Assistant for wake word processing
  - Privacy benefit: voice data never leaves device for wake word

- **Model Selection:**
  - Use box3b's integrated voice model capabilities
  - Evaluate pre-trained wake word models optimized for ESP32
  - Recommended: microWakeWord or similar (typically 50KB model size)

- **Performance Targets:**
  - Detection latency: <500ms from speech to wake detection
  - False positive rate: <2% (1 per 50 utterances)
  - False negative rate: <10% (1 per 10 wake words)
  - Power consumption: <500mW during continuous listening

- **Continuous Listening Architecture:**
  - Audio continuously captured but not transmitted until wake detected
  - Minimal data overhead during listening state
  - Rapid transition to recording state on wake word confidence >0.8
  - Timeout handling: 5-10 seconds of silence returns to listening

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-10-continuous-conversation-wake-word.md`

---

## Clarification 8: Epic 2 - Serial Logging FIRST (Phase 1), HA Integration LATER (Phase 2)
**Epic:** 2 (Observability & Serial Logging)
**Decision:** Implement serial logging Phase 1 now; defer Home Assistant integration to Phase 2

**Implementation Direction:**
- **Phase 1 (Epic 2 - This Cycle):**
  - Structured JSON logging on firmware (all events, errors, performance metrics)
  - Serial port capture service (Python background service)
  - Log file rotation with configurable retention
  - Command-line utilities for log viewing and searching
  - Configuration for debug vs. production logging levels
  - Performance overhead measurement (<5% CPU impact)

- **Phase 2 (Future Epic - Deferred):**
  - Home Assistant MQTT integration
  - Real-time video monitoring of device display
  - Lovelace dashboard for operator viewing
  - Log aggregation backend with database
  - Web UI for advanced log analysis
  - Alert automation and thresholds

- **Phase 1 Rationale:**
  - Serial logging is foundation for all upstream debugging
  - Establish reliable log capture before adding complexity
  - Operators can diagnose 90% of issues from serial logs
  - HA integration can be added incrementally without rework

- **Future Phase 2 Enablement:**
  - Serial logging Phase 1 provides structured data source
  - Phase 2 builds analytics/dashboarding on top
  - No breaking changes to serial logging in Phase 1

**Reference Files:**
- `dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md` (Phased approach explained)

---

## Clarification 9: scan-dev-notes.py - Standalone Utility Only
**Tool:** scan-dev-notes.py
**Decision:** This is a standalone utility script, not integrated as blocker/hook

**Implementation Direction:**
- **Standalone Execution:**
  - Can be run manually by developers for analysis
  - Not invoked automatically by CI/CD pipeline
  - Not used as pre-commit hook or build gate

- **Purpose:**
  - Scan development notes for project structure analysis
  - Generate reports or summaries from notes
  - Support documentation generation
  - Developer workflow tool (optional)

- **No Integration Requirements:**
  - Does not block commits or builds
  - Does not require external services
  - Does not need to be error-free for project to proceed
  - Provides value as optional tooling

**Reference:**
- Tool exists as utility but is not critical path

---

## Summary: Cross-Epic Dependencies and Sequencing

```
Sequential Critical Path (must complete in order):
  Epic 1 (OTA Foundation) ──┐
                            ├─→ Epic 2 (Serial Logging) ──┐
  [Mellona Integration]     ├─→ Epic 3 (Wyoming)         ├─→ Epic 4 (LLM)
                            │                             │
                            └─→ [Mellona Pre-Epic 5] ◄────┘
                                     │
                                     ├─→ Epic 5 (SQLite Context Persistence)
                                     │
                                     ├─→ Epic 6 (Docker Deployment)
                                     │
                                     ├─→ Epic 7 (Recording + Serial Logs utility)
                                     │
                                     └─→ Epics 8-12 (downstream features)

Key Decisions Applied:
  • Epic 1: Device available now - test immediately
  • Epic 2: Serial logging Phase 1 only (HA Phase 2)
  • Epic 5: Mellona prerequisite, SQLite Phase 1
  • Epic 6: Docker + docker-compose deployment
  • Epic 7: Serial logs as separate CLI utility
  • Epic 9: Arduino vs ESPHome evaluation needed
  • Epic 10: LOCAL voice model (no HA streaming)
  • scan-dev-notes.py: Standalone tool only
```

---

## How to Use This Document

**For Implementation Teams:**
1. Review your assigned epic section
2. Verify the clarification aligns with your understanding
3. Apply the decision to task planning and acceptance criteria
4. Reference this document in design decisions and code reviews

**For Project Planning:**
1. Use cross-epic dependencies to inform sequencing
2. Ensure Mellona integration completes before Epic 5 starts
3. Plan Phase 2 (HA integration) as separate initiative after Phase 1 (Serial Logging)
4. Account for Arduino vs ESPHome research time in Epic 9

**For Architecture Decisions:**
1. Implement storage abstraction in Epic 5 (enables future PostgreSQL migration)
2. Design serial logging for Phase 1 with Phase 2 extensibility in mind
3. Keep serial logging tool independent (separate repo/packaging)

---

## Document Status

**Status:** Complete - All 9 clarifications documented
**Last Updated:** 2026-03-24
**Owner:** Chatterbox Project Team
**Review Frequency:** As needed for epic implementation

---

## Appendix: Files Updated

**Documentation Files:**
- `docs/epics-plan.md` - Updated executive summary and epic descriptions

**Epic Plan Files Updated:**
- `dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md` - Phase 1/2 separation
- `dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md` - Mellona prerequisite, SQLite strategy
- `dev_notes/project_plans/2026-03-24_epic-6-backend-deployment-ha-connection.md` - Docker + Compose strategy
- `dev_notes/project_plans/2026-03-24_epic-7-recording-pcm-streaming.md` - Serial logging utility noted
- `dev_notes/project_plans/2026-03-24_epic-9-touchscreen-integration.md` - Arduino vs ESPHome research
- `dev_notes/project_plans/2026-03-24_epic-10-continuous-conversation-wake-word.md` - LOCAL voice model decision

**New Files:**
- `dev_notes/project_plans/2026-03-24_clarifications-summary.md` (this file)

---
