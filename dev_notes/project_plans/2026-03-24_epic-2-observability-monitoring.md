# Epic 2: Serial Logging Infrastructure (Phase 1) - Project Plan

**Document ID:** EPIC-2-SERIAL-LOGGING-2026
**Epic Title:** Serial Logging Infrastructure & Observability (Phase 1)
**Status:** Planned
**Target Completion:** 2026-04-14
**Estimated Duration:** 2 weeks (~80 hours)
**Last Updated:** 2026-03-24
**Implementation Strategy:** Serial logging as Phase 1; HA dashboard/integration deferred to Phase 2

---

## Executive Summary

Epic 2 Phase 1 establishes reliable serial logging infrastructure for comprehensive observability of the Chatterbox system. This phase focuses on structured serial logging, firmware integration, and log capture utilities. Home Assistant dashboard integration (video monitoring, MQTT entities, advanced analytics) is deferred to Phase 2 as a future enhancement. The primary target is the ESP32-S3-BOX-3B hardware, with focus on capturing device state transitions, audio events, network communication, and performance metrics via serial port.

---

## Goals & Success Criteria

### Phase 1 (Epic 2) Goals
1. Establish structured serial logging for all device operations
2. Implement serial log capture service with file rotation and persistence
3. Create command-line utilities for log viewing and searching
4. Build serial logging on firmware with configurable verbosity
5. Enable operator troubleshooting from serial logs alone

### Phase 2 (Future Epic) Goals
1. Implement real-time video monitoring of box3b display state
2. Create Home Assistant dashboard for device monitoring
3. Build log aggregation backend with full-text search
4. Create web UI for log analysis and historical review
5. Enable remote troubleshooting without physical access

### Phase 1 Success Criteria (Epic 2)
- [ ] Serial logging captures 100% of device state transitions
- [ ] Structured JSON logging format on firmware
- [ ] Serial log capture service operational and reliable
- [ ] Log files persisted with configurable rotation and retention
- [ ] Command-line utilities functional (capture, view, search)
- [ ] Performance baseline established via serial logs
- [ ] Operators can diagnose device issues from serial logs
- [ ] System logging overhead <5% CPU impact
- [ ] Documentation complete for operators

### Phase 2 Success Criteria (Future Enhancement)
- [ ] Video monitoring captures display state with <500ms latency
- [ ] HA dashboard displays real-time device metrics and state
- [ ] Log aggregation backend with full-text search
- [ ] Web UI for log analysis and historical review
- [ ] Remote troubleshooting without physical access
- [ ] System alert thresholds defined and tested

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 1 (OTA & Foundation):** Framework ready, device state machine operational
- **Wyoming Protocol:** Basic device communication established
- **Home Assistant:** Core integration framework in place

### Prerequisites
- ES P32 serial/USB drivers installed on monitoring host
- MQTT broker available (for HA integration)
- Python 3.9+ environment with required dependencies
- Video capture device access (/dev/video0 on box3b)

### Blockers to Identify
- Device serial port stability
- Home Assistant API availability/authentication
- Network bandwidth for video streaming

---

## Detailed Task Breakdown

### Task 2.1: Serial Logging Infrastructure Design
**Objective:** Define structured logging schema for all device events
**Estimated Hours:** 8
**Acceptance Criteria:**
- [ ] Logging schema documented (JSON-based format)
- [ ] Log levels defined (DEBUG, INFO, WARN, ERROR, CRITICAL)
- [ ] Structured fields captured (timestamp, module, state, event type)
- [ ] Log rotation strategy defined (max size, retention)
- [ ] Implementation guide for firmware integration

**Implementation Details:**
- Design log entry structure with required fields
- Define standard prefixes for each module (DEVICE, AUDIO, NETWORK, LLM)
- Create log level mapping to severity
- Plan buffer management for resource-constrained device

**Testing Plan:**
- Validate schema against sample log entries
- Test with maximum expected throughput (100 events/sec)
- Verify log line length doesn't exceed serial buffer

---

### Task 2.2: Serial Logging Integration on Firmware
**Objective:** Implement structured logging on ESP32 firmware
**Estimated Hours:** 12
**Depends On:** Task 2.1
**Acceptance Criteria:**
- [ ] All state transitions logged to serial port
- [ ] Audio events logged (record start/stop, buffer levels)
- [ ] Network events logged (connection attempts, packet stats)
- [ ] Memory/resource usage logged every 60 seconds
- [ ] Log output testable via serial monitor

**Implementation Details:**
- Create logging macros for different modules
- Integrate with existing state machine (Epic 1)
- Implement circular buffer for log buffering
- Configure serial output baud rate (115200)
- Add conditional logging levels (debug vs. production)

**Testing Plan:**
- Monitor serial output during state transitions
- Verify all event types are captured
- Test with verbose and quiet logging modes
- Measure performance overhead (<5% CPU impact)

---

### Task 2.3: Video Monitoring Service (Python)
**Objective:** Build Python service to capture and stream display state
**Estimated Hours:** 16
**Depends On:** Task 2.1
**Acceptance Criteria:**
- [ ] Captures /dev/video0 at 5 fps minimum
- [ ] Latency <500ms from display to monitoring service
- [ ] Supports MJPEG streaming over HTTP
- [ ] Integrates with Home Assistant as camera entity
- [ ] Graceful fallback if camera unavailable
- [ ] Resource usage <10% CPU, <50MB RAM

**Implementation Details:**
- Use OpenCV or similar for video capture
- Implement MJPEG HTTP server for streaming
- Add compression to reduce bandwidth
- Create Home Assistant camera component integration
- Implement reconnection logic with exponential backoff

**Testing Plan:**
- Stream to multiple clients simultaneously
- Test with various network conditions
- Verify image quality under different lighting
- Monitor resource usage over extended run
- Test recovery from camera disconnection

---

### Task 2.4: Serial Log Capture Service (Python)
**Objective:** Build background service to capture and persist serial logs
**Estimated Hours:** 12
**Depends On:** Task 2.2
**Acceptance Criteria:**
- [ ] Captures all serial output in real-time
- [ ] Saves to local log files with rotation
- [ ] Structured log parsing (JSON extraction)
- [ ] Uploads logs to Home Assistant MQTT
- [ ] Handles serial port disconnection gracefully
- [ ] Runs as systemd service

**Implementation Details:**
- Create serial port reader with ring buffer
- Implement log file rotation (daily + size-based)
- Parse JSON log entries for structured storage
- Push key metrics to MQTT topic
- Implement watchdog for service health

**Testing Plan:**
- Verify all serial data captured without loss
- Test log rotation at boundary conditions
- Validate MQTT message format
- Test restart recovery and state preservation
- Stress test with high log volume (500+ lines/sec)

---

### Task 2.5: Home Assistant Integration - MQTT Entities
**Objective:** Create MQTT entities in HA for device monitoring
**Estimated Hours:** 10
**Depends On:** Task 2.4
**Acceptance Criteria:**
- [ ] Device state entity (binary_sensor)
- [ ] Audio status entity (sensor)
- [ ] Memory usage entity (sensor)
- [ ] Network status entity (sensor)
- [ ] Last activity timestamp (sensor)
- [ ] All entities auto-discovered via MQTT

**Implementation Details:**
- Define MQTT topic structure for device metrics
- Create Home Assistant MQTT discovery payloads
- Map device states to HA state values
- Implement entity naming convention
- Configure automations for state changes

**Testing Plan:**
- Verify entity discovery in HA UI
- Test state updates in real-time
- Validate MQTT message format
- Test auto-discovery with HA restart
- Verify historical data preservation

---

### Task 2.6: Home Assistant Dashboard Creation
**Objective:** Build visual dashboard for device monitoring
**Estimated Hours:** 14
**Depends On:** Tasks 2.3, 2.5
**Acceptance Criteria:**
- [ ] Dashboard displays live video feed
- [ ] Real-time state indicator with state history
- [ ] Memory/CPU usage charts (24-hour)
- [ ] Network status and connection info
- [ ] Recent log entries (last 20 events)
- [ ] Quick action buttons (restart, logs view, etc.)
- [ ] Mobile responsive design

**Implementation Details:**
- Create custom dashboard using Lovelace YAML
- Add template sensors for computed metrics
- Implement charts using ApexCharts or similar
- Create collapse/expand sections for organization
- Add notification automation for critical events

**Testing Plan:**
- Verify dashboard loads on various devices
- Test with real-time data updates
- Check mobile responsiveness
- Validate all buttons and automations work
- Test with missing/offline devices

---

### Task 2.7: Log Aggregation Backend
**Objective:** Build centralized log aggregation service
**Estimated Hours:** 14
**Depends On:** Task 2.4
**Acceptance Criteria:**
- [ ] Logs persisted in searchable database (SQLite/PostgreSQL)
- [ ] Retention policy enforced (30-day default)
- [ ] Full-text search capability on log content
- [ ] Log filtering by module, level, timestamp
- [ ] API for log retrieval
- [ ] Automated cleanup of expired logs

**Implementation Details:**
- Design database schema for log storage
- Implement Python service for log ingestion
- Create REST API for querying logs
- Add log indexing for search performance
- Implement TTL-based retention policy

**Testing Plan:**
- Insert logs at high throughput (1000/sec)
- Test search performance with large dataset (1M+ logs)
- Verify retention policy execution
- Test API under concurrent requests
- Validate search accuracy

---

### Task 2.8: Web UI for Log Viewing
**Objective:** Create web interface for exploring aggregated logs
**Estimated Hours:** 12
**Depends On:** Task 2.7
**Acceptance Criteria:**
- [ ] Real-time log tail view
- [ ] Advanced filtering UI (module, level, time range)
- [ ] Log detail view with context
- [ ] Export logs to CSV/JSON
- [ ] Search highlighting in results
- [ ] Responsive design

**Implementation Details:**
- Build with Flask/FastAPI backend
- Create React/Vue frontend for UI
- Implement WebSocket for live updates
- Add filter persistence to localStorage
- Create export functionality

**Testing Plan:**
- Test with various log volumes
- Verify search performance
- Test filter combinations
- Validate export file format and completeness
- Test responsive design

---

### Task 2.9: Alert Configuration & Automation
**Objective:** Implement alert thresholds and notification system
**Estimated Hours:** 10
**Depends On:** Tasks 2.5, 2.7
**Acceptance Criteria:**
- [ ] Alert thresholds defined for key metrics
- [ ] Memory usage alert (>80% threshold)
- [ ] Network disconnection detection
- [ ] Consecutive error logging alert
- [ ] Notifications via Home Assistant (push/email)
- [ ] Alert acknowledgment system

**Implementation Details:**
- Define baseline metrics for each device type
- Create alert condition evaluator
- Implement notification aggregation (avoid spam)
- Add alert history and acknowledgment tracking
- Create HA automations for notifications

**Testing Plan:**
- Trigger each alert condition manually
- Verify notifications sent correctly
- Test alert suppression and throttling
- Validate alert history persistence
- Test acknowledgment functionality

---

### Task 2.10: Performance Monitoring & Metrics
**Objective:** Establish baseline performance metrics and monitoring
**Estimated Hours:** 8
**Depends On:** Task 2.4
**Acceptance Criteria:**
- [ ] CPU usage baseline established (<40% avg)
- [ ] Memory usage baseline established (<50% avg)
- [ ] Network latency baseline (<100ms avg)
- [ ] Metrics collected continuously
- [ ] Trend analysis over time
- [ ] Graphing of historical metrics

**Implementation Details:**
- Add system metric collection to serial logging
- Create metrics aggregation service
- Build timeseries database schema
- Implement graphing interface
- Define normal operating ranges

**Testing Plan:**
- Collect metrics over 7-day period
- Analyze performance under various loads
- Verify graph accuracy and responsiveness
- Test with resource-constrained scenarios
- Validate baseline reproducibility

---

### Task 2.11: Remote Log Access & Remote Diagnostics
**Objective:** Enable troubleshooting without physical device access
**Estimated Hours:** 10
**Depends On:** Tasks 2.4, 2.8
**Acceptance Criteria:**
- [ ] Secure VPN or SSH tunnel for log access
- [ ] Real-time log tailing capability
- [ ] Remote serial console access (for debugging)
- [ ] Device info dump functionality
- [ ] Remote screenshot capability
- [ ] Security: Authentication and access control

**Implementation Details:**
- Implement SSH-based serial port forwarding
- Create remote log tailing command
- Add device info REST endpoint
- Implement screenshot generation from video feed
- Implement role-based access control

**Testing Plan:**
- Test remote access from different networks
- Verify security of authentication
- Test serial console commands
- Validate device info completeness
- Performance test with high-latency connections

---

### Task 2.12: Documentation & Runbooks
**Objective:** Document observability system and troubleshooting guides
**Estimated Hours:** 12
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Observability architecture documented
- [ ] Setup guides for monitoring infrastructure
- [ ] Troubleshooting guide for common issues
- [ ] Alert runbooks (response procedures)
- [ ] Best practices for log analysis
- [ ] Examples of common queries/filters

**Implementation Details:**
- Write architecture documentation
- Create step-by-step setup guides
- Document all tools and their purpose
- Create troubleshooting decision trees
- Add examples of debugging workflows

**Testing Plan:**
- Have new user follow setup guides
- Verify all documented procedures work
- Validate examples are accurate
- Test troubleshooting guide effectiveness
- Get peer review of documentation

---

### Task 2.13: Integration Testing & System Validation
**Objective:** End-to-end testing of observability system
**Estimated Hours:** 12
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] All components integrated and working
- [ ] Data flows correctly through entire pipeline
- [ ] No data loss under normal operation
- [ ] System recovers from failures gracefully
- [ ] Performance meets all requirements
- [ ] Documentation complete and accurate

**Implementation Details:**
- Create integration test scenarios
- Simulate various failure modes
- Test end-to-end data flows
- Verify performance under load
- Run stability tests (24-hour runs)

**Testing Plan:**
- Execute integration test suite
- Simulate device restarts, network failures
- Measure end-to-end latency
- Stress test with multiple devices
- Validate all success criteria met

---

### Task 2.14: Monitoring Infrastructure Deployment
**Objective:** Deploy monitoring stack to production environment
**Estimated Hours:** 8
**Depends On:** All previous tasks
**Acceptance Criteria:**
- [ ] Services running on designated host
- [ ] Home Assistant integration live
- [ ] All metrics flowing correctly
- [ ] Dashboards accessible and functional
- [ ] Backup and recovery tested
- [ ] Documentation for deployment kept current

**Implementation Details:**
- Deploy Python services with systemd
- Configure Home Assistant integrations
- Set up database backups
- Configure network/firewall rules
- Document deployment procedures

**Testing Plan:**
- Verify all services start correctly
- Test service restart recovery
- Validate backup/restore process
- Test firewall rule effectiveness
- Document any deployment issues

---

### Task 2.15: Retrospective & Lessons Learned
**Objective:** Review epic completion and document learnings
**Estimated Hours:** 6
**Depends On:** All other tasks
**Acceptance Criteria:**
- [ ] Epic retrospective completed
- [ ] Lessons documented
- [ ] Improvements identified for next phase
- [ ] Performance vs. estimates reviewed
- [ ] Quality metrics analyzed

**Implementation Details:**
- Conduct team retrospective meeting
- Document findings
- Identify process improvements
- Plan adjustments for Epic 3

---

## Technical Implementation Details

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           Home Assistant + Dashboard                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Lovelace Dashboard  │  Camera Entity │ Sensors   │   │
│  └──────────────────────────────────────────────────┘   │
│                         ▲                                 │
└─────────────────────────┼─────────────────────────────────┘
                          │ MQTT
    ┌─────────────────────┴──────────────────────┐
    │                                            │
┌───▼──────────────────┐          ┌─────────────▼────┐
│  Video Monitor Svc   │          │ Serial Log Svc   │
│  (video streaming)   │          │ (log capture)    │
└───┬──────────────────┘          └──────┬──────────┘
    │                                    │
    │ /dev/video0                        │ /dev/ttyUSB0
    │                                    │
┌───▼────────────────────────────────────▼────────┐
│     ESP32-S3-BOX-3B                            │
│  ┌──────────────────────────────────────────┐  │
│  │ Firmware: State Machine + Logging        │  │
│  │ Serial Output: Structured Logs           │  │
│  │ Display: State Indicators                │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘

Additional Components:
┌─────────────────────────────────┐
│  Log Aggregation Backend        │
│  ┌───────────────────────────┐  │
│  │ Database (SQLite/PG)      │  │
│  │ Search/Query Engine       │  │
│  │ Retention Policy Engine   │  │
│  └───────────────────────────┘  │
└─────────────┬───────────────────┘
              │
         Web UI for logs
```

### Key Components

1. **Serial Logging (Firmware)**
   - Structured JSON logs to serial port
   - Minimal overhead on device
   - Configuration for debug/production modes

2. **Video Monitoring Service**
   - Captures from /dev/video0
   - MJPEG streaming over HTTP
   - Home Assistant camera integration

3. **Serial Log Capture Service**
   - Python background service
   - Real-time serial reading
   - MQTT publishing of key metrics

4. **Log Aggregation**
   - Centralized storage
   - Full-text search
   - Retention policies

5. **Home Assistant Integration**
   - MQTT discovery
   - Lovelace dashboard
   - Alert automation

### Data Flow

```
Device Event → Firmware Logging → Serial Port →
Log Capture Service → Database + MQTT →
HA Dashboard + Web UI
```

### Security Considerations
- Serial port access restricted to monitoring service user
- MQTT authentication configured
- Log data sanitized (no sensitive PII)
- Web UI behind Home Assistant authentication
- Remote access via VPN/SSH only

---

## Testing Plan

### Unit Testing
- Serial logging macro functionality (firmware)
- Log parsing and JSON extraction
- MQTT message formatting
- Database query performance

### Integration Testing
- End-to-end log flow from device to storage
- Video feed capture and streaming
- MQTT integration with Home Assistant
- Dashboard data updates in real-time

### System Testing
- 24-hour stability test
- Log retention policy enforcement
- Multi-device monitoring simultaneously
- Performance under high log volume (1000+ logs/sec)

### Acceptance Testing
- Operator can monitor device without physical access
- All alerts fire correctly
- Dashboard responsive and accurate
- Logs searchable and historical data preserved

---

## Estimated Timeline

**Week 1 (40 hours):**
- Days 1-2: Task 2.1 - Serial logging design
- Days 2-3: Task 2.2 - Firmware integration
- Days 3-4: Task 2.3 - Video monitoring service
- Days 4-5: Task 2.4 - Serial log capture service

**Week 2 (40 hours):**
- Days 1-2: Tasks 2.5 & 2.6 - HA integration and dashboard
- Days 2-3: Task 2.7 - Log aggregation backend
- Days 3: Task 2.8 - Web UI for logs
- Days 4: Tasks 2.9 & 2.10 - Alerts and metrics
- Days 4-5: Task 2.11 - Remote diagnostics
- Days 5: Tasks 2.12-2.15 - Documentation and validation

**Total: ~80 hours (~2 weeks at 40 hrs/week)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Serial port instability | Medium | High | Test extensively; implement watchdog; graceful reconnection |
| Video capture performance degradation | Low | Medium | Optimize compression; limit fps; test on target hardware |
| MQTT broker unavailability | Medium | Medium | Implement queue buffering; retry logic; graceful degradation |
| Database query performance | Medium | Medium | Implement indexing; test with large datasets; consider sharding |
| Home Assistant version compatibility | Low | Low | Test with supported HA versions; version constraints in docs |
| Network bandwidth for video | Medium | Low | Implement adaptive bitrate; compression optimization |
| Log volume exceeds storage | Low | Medium | Implement aggressive retention; compression; archive old logs |
| Security vulnerabilities in monitoring | Medium | High | Security review; minimal surface area; authentication required |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] All state transitions logged and visible in UI
- [ ] Video feed displays real-time device state
- [ ] Dashboard provides complete device overview
- [ ] Operators can diagnose issues from logs alone
- [ ] Alerts notify of critical conditions
- [ ] Historical data preserved for analysis

### Performance
- [ ] Video latency <500ms
- [ ] Log capture without data loss
- [ ] Dashboard loads <2 seconds
- [ ] Search results <1 second for recent data
- [ ] System overhead <10% of device resources

### Reliability
- [ ] System recovers from service restarts
- [ ] No data loss in normal operation
- [ ] Graceful degradation if components fail
- [ ] 99% availability of monitoring
- [ ] 30-day log retention maintained

### Documentation
- [ ] Setup guide complete and tested
- [ ] Troubleshooting guide with common scenarios
- [ ] API documentation for log access
- [ ] Dashboard user guide
- [ ] Architecture documentation

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic enables the observability goals outlined in the master plan Phase 1 (Foundation & Hardware). It establishes monitoring infrastructure that will be crucial for debugging and optimizing all subsequent epics.

**Dependencies Met by Previous Epics:**
- Epic 1: Device state machine and framework foundation
- Wyoming Protocol: Basic device communication established

**Enables Next Epic:**
- Epic 3: Wyoming Protocol & Testing (builds on observability for protocol validation)

---

## Approval & Sign-Off

**Epic Owner:** [To be assigned]
**Technical Lead:** [To be assigned]
**QA Lead:** [To be assigned]

**Approved By:**
- [ ] Epic Owner
- [ ] Technical Lead
- [ ] QA Lead

**Approved Date:** _______________

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-04-14 (Epic 1 completion)
