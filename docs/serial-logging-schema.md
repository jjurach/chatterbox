# Serial Logging Schema - ESP32 Device Logs

**Version:** 1.0
**Date:** 2026-03-25
**Purpose:** Structured logging schema for capturing device logs from ESP32 via serial connection

## Overview

This schema defines a JSON-based structured logging format for ESP32 devices to emit logs that can be captured, parsed, and archived by the Chatterbox serial log capture service. The schema is designed to:

- Minimize firmware resource overhead (resource-constrained ESP32)
- Support multiple log levels (DEBUG, INFO, WARN, ERROR)
- Provide context via module prefixes and structured fields
- Enable efficient log rotation and storage
- Allow real-time filtering and analysis on the monitoring host

## Schema Specification v1.0

### JSON Log Entry Format

Each log entry is a complete JSON object on a single line:

```json
{
  "timestamp": 1714521600000,
  "level": "INFO",
  "module": "audio.capture",
  "message": "Starting audio capture",
  "context": {
    "sample_rate": 16000,
    "channels": 1
  },
  "trace_id": "a1b2c3d4e5f6"
}
```

### Field Definitions

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | integer (ms) | Milliseconds since epoch | `1714521600000` |
| `level` | string | Log level: DEBUG, INFO, WARN, ERROR | `"INFO"` |
| `module` | string | Module/component identifier | `"audio.capture"` |
| `message` | string | Human-readable log message | `"Starting audio capture"` |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context` | object | Structured context data (key-value pairs) | `{"sample_rate": 16000}` |
| `trace_id` | string | Correlation ID for request tracing | `"a1b2c3d4e5f6"` |
| `error_code` | integer | Numeric error code | `500` |
| `stack_trace` | string | Stack trace for ERROR logs | `"Exception at line 42"` |

### Log Levels

| Level | Severity | Use Case |
|-------|----------|----------|
| DEBUG | 0 | Detailed diagnostics (verbose) |
| INFO | 1 | General informational messages |
| WARN | 2 | Warning conditions (degraded state) |
| ERROR | 3 | Error conditions (failure) |

### Module Naming Convention

Module identifiers should use dot notation to represent component hierarchy:

```
<system>.<subsystem>.<component>

Examples:
- audio.capture        (audio subsystem, capture component)
- audio.playback       (audio subsystem, playback component)
- wifi.connection      (WiFi subsystem, connection component)
- device.sensor        (device subsystem, sensor component)
- ha.integration       (Home Assistant integration)
```

## Examples

### Basic Info Log

```json
{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Device initialized"}
```

### Audio Capture with Context

```json
{
  "timestamp": 1714521605234,
  "level": "INFO",
  "module": "audio.capture",
  "message": "Audio buffer full, processing",
  "context": {
    "buffer_size_bytes": 32000,
    "sample_rate": 16000,
    "duration_ms": 1000
  }
}
```

### Error with Stack Trace

```json
{
  "timestamp": 1714521610500,
  "level": "ERROR",
  "module": "wifi.connection",
  "message": "Connection failed",
  "error_code": 3,
  "context": {
    "ssid": "HomeNetwork",
    "attempts": 5
  },
  "stack_trace": "WiFiError: Max retries exceeded at wifi_init (line 234)"
}
```

### Debug Log with Trace ID

```json
{
  "timestamp": 1714521600123,
  "level": "DEBUG",
  "module": "ha.integration",
  "message": "Processing intent",
  "trace_id": "req-a1b2c3d4",
  "context": {
    "intent_name": "turn_on_light",
    "entity_id": "light.bedroom"
  }
}
```

## Firmware Implementation Guide

### C/C++ Implementation (ESP-IDF)

This section provides guidance for ESP32 firmware developers to emit logs in this schema.

#### Step 1: Create a Logging Macro

```c
#include <stdio.h>
#include <time.h>
#include <sys/time.h>

// Helper to get current time in milliseconds
static uint64_t get_timestamp_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

// Simple logging macro (no context)
#define LOG(level, module, message) \
    printf("{\"timestamp\": %lld, \"level\": \"%s\", \"module\": \"%s\", \"message\": \"%s\"}\n", \
           get_timestamp_ms(), level, module, message)

// Logging macro with context (use snprintf to build context)
#define LOG_CTX(level, module, message, context_str) \
    printf("{\"timestamp\": %lld, \"level\": \"%s\", \"module\": \"%s\", \"message\": \"%s\", \"context\": %s}\n", \
           get_timestamp_ms(), level, module, message, context_str)
```

#### Step 2: Use in Firmware Code

```c
// Simple info log
LOG("INFO", "startup", "Device booted");

// Log with context
char context[256];
snprintf(context, sizeof(context),
         "{\"sample_rate\": %d, \"channels\": %d}",
         16000, 1);
LOG_CTX("INFO", "audio.capture", "Starting capture", context);

// Error log with error code
printf("{\"timestamp\": %lld, \"level\": \"ERROR\", \"module\": \"wifi.connection\", "
       "\"message\": \"Connection failed\", \"error_code\": %d}\n",
       get_timestamp_ms(), err_code);
```

#### Step 3: Buffer Considerations

For resource-constrained devices:

- **Minimal buffering:** Emit logs immediately to serial (let host buffer)
- **No log queue:** Avoid in-device buffering (adds complexity)
- **Line-buffered output:** Ensure each JSON object is a complete line (`\n` terminated)
- **Context size:** Keep context JSON < 256 bytes to avoid stack overflow
- **Message length:** Keep message field < 128 bytes

### Output to Serial

Configure ESP32 UART output to send logs to the host:

```c
// ESP-IDF UART configuration (example)
uart_config_t uart_config = {
    .baud_rate = 115200,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_DISABLE,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
};
uart_driver_install(UART_NUM_0, 1024, 1024, 0, NULL, 0);
uart_param_config(UART_NUM_0, &uart_config);
uart_set_pin(UART_NUM_0, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
```

### Python Implementation (Host Side)

A Python service will capture and parse these JSON logs. See `src/chatterbox/services/serial_log_capture.py`.

## Log Rotation Strategy

### Time-Based Rotation

- **Daily rotation:** New log file at midnight UTC
- **Filename pattern:** `chatterbox-logs_YYYY-MM-DD.json`
- **Retention:** Keep last 30 days (configurable)

### Size-Based Rotation

- **Max file size:** 10 MB per log file
- **Overflow handling:** New file created when limit reached
- **Naming:** `chatterbox-logs_YYYY-MM-DD_HH-MM-SS.json` for size-rotated files

### Archive Strategy

- **Compression:** Optional gzip compression of old logs
- **Archive path:** `logs/archive/` subdirectory
- **Cleanup:** Automatic deletion after retention period

## Parsing and Storage

### Host-Side Processing (Python)

1. **Real-time capture:** Tail serial port, line-by-line
2. **JSON validation:** Parse each line, skip malformed entries
3. **Filtering:** Filter by level, module, timestamp range
4. **Storage:** Write valid entries to log file (one JSON per line)
5. **Rotation:** Apply rotation policy based on date/size

### Search and Analysis

Log files can be searched using standard tools:

```bash
# Find all ERROR logs
grep '"level": "ERROR"' chatterbox-logs_2026-03-25.json

# Find logs from specific module
grep '"module": "audio.capture"' chatterbox-logs_2026-03-25.json

# Find logs in time range (requires timestamp)
jq 'select(.timestamp > 1714521600000 and .timestamp < 1714608000000)' chatterbox-logs_2026-03-25.json
```

## Backward Compatibility

Future schema versions:
- **v1.x:** Minor additions (optional new fields) will remain backward compatible
- **v2.0+:** Breaking changes will use a new `schema_version` field
- **Current:** Assume v1.0 if no version field present

## Configuration Reference

See `src/chatterbox/config/serial_logging.py` for capture service configuration.

### Environment Variables

```bash
# Serial port device
CHATTERBOX_SERIAL_PORT=/dev/ttyUSB0

# Baud rate
CHATTERBOX_SERIAL_BAUD=115200

# Log directory
CHATTERBOX_LOG_DIRECTORY=/var/log/chatterbox

# Daily rotation enabled
CHATTERBOX_LOG_ROTATE_DAILY=true

# Max log file size (bytes)
CHATTERBOX_LOG_MAX_SIZE=10485760

# Retention days
CHATTERBOX_LOG_RETENTION_DAYS=30

# Buffer size
CHATTERBOX_SERIAL_BUFFER_SIZE=4096
```

## Troubleshooting

### Issue: Garbled or incomplete JSON in logs

**Cause:** Serial connection interrupted or baud rate mismatch

**Solution:**
1. Verify baud rate matches: `stty -a /dev/ttyUSB0`
2. Check USB cable connection
3. Try lower baud rate: 9600 or 57600
4. Enable serial port debugging

### Issue: High CPU usage on monitor host

**Cause:** Serial reading loop not yielding

**Solution:**
1. Increase buffer size in config
2. Use async/await (see implementation)
3. Add small sleep between read cycles

### Issue: Log rotation not happening

**Cause:** Service not running or disk space issue

**Solution:**
1. Check service status: `systemctl status chatterbox-serial-logger`
2. Verify log directory permissions: `ls -l /var/log/chatterbox`
3. Check available disk space: `df /var/log`

## Related Documentation

- [Serial Log Capture Service](../src/chatterbox/services/serial_log_capture.py) - Python implementation
- [Configuration](../src/chatterbox/config/serial_logging.py) - Service configuration
- [Tests](../tests/unit/test_services/test_serial_log_capture.py) - Unit test patterns
- [Systemd Setup](../docs/serial-logger-systemd.md) - Production deployment

---

**Last Updated:** 2026-03-25
**Schema Version:** 1.0
**Status:** Active
