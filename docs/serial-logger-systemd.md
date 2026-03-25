# Serial Logger Systemd Setup Guide

**Purpose:** Deploy the Chatterbox serial logging service as a background systemd service for production use

## Overview

The serial logger can be deployed as a systemd service to capture device logs continuously. This guide covers installation, configuration, and troubleshooting.

## Installation

### Prerequisites

- Python 3.10+ with chatterbox package installed
- Serial device connected (e.g., `/dev/ttyUSB0`)
- Systemd (Linux)
- User with sudo access

### Install Chatterbox

```bash
# Clone repository
git clone <repository-url>
cd hentown/modules/chatterbox

# Install in editable mode
pip install -e .

# Or install system-wide
sudo pip install .
```

## Configuration

### 1. Create Configuration File

Create `/etc/chatterbox/serial-logger.env`:

```bash
sudo mkdir -p /etc/chatterbox
sudo tee /etc/chatterbox/serial-logger.env > /dev/null <<'EOF'
# Serial connection settings
CHATTERBOX_SERIAL_PORT=/dev/ttyUSB0
CHATTERBOX_SERIAL_BAUD=115200
CHATTERBOX_SERIAL_TIMEOUT_SECONDS=1.0
CHATTERBOX_SERIAL_BUFFER_SIZE=4096

# Log file settings
CHATTERBOX_LOG_DIRECTORY=/var/log/chatterbox
CHATTERBOX_LOG_PREFIX=chatterbox-logs
CHATTERBOX_LOG_SUFFIX=.json

# Rotation settings
CHATTERBOX_LOG_ROTATE_DAILY=true
CHATTERBOX_LOG_MAX_SIZE_BYTES=10485760
CHATTERBOX_LOG_RETENTION_DAYS=30
CHATTERBOX_LOG_ARCHIVE_ENABLED=false
CHATTERBOX_LOG_ARCHIVE_COMPRESSION=false

# Service settings
CHATTERBOX_SERVICE_RECONNECT_MAX_ATTEMPTS=5
CHATTERBOX_SERVICE_RECONNECT_BACKOFF_MS=5000
CHATTERBOX_SERVICE_LOG_LEVEL=INFO
EOF

sudo chmod 600 /etc/chatterbox/serial-logger.env
```

### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/chatterbox
sudo chown chatterbox:chatterbox /var/log/chatterbox
sudo chmod 755 /var/log/chatterbox
```

### 3. Create Systemd User

```bash
# Create user if not exists
sudo useradd -r -s /bin/false -d /var/lib/chatterbox -m chatterbox

# Add to dialout group to access serial ports
sudo usermod -a -G dialout chatterbox
```

## Systemd Service Setup

### Create Service File

Create `/etc/systemd/system/chatterbox-serial-logger.service`:

```bash
sudo tee /etc/systemd/system/chatterbox-serial-logger.service > /dev/null <<'EOF'
[Unit]
Description=Chatterbox Serial Logger
Documentation=https://github.com/yourrepo/chatterbox
After=network.target syslog.target

[Service]
Type=simple
User=chatterbox
Group=chatterbox

# Load environment configuration
EnvironmentFile=/etc/chatterbox/serial-logger.env

# Restart policy
Restart=on-failure
RestartSec=10s
StartLimitInterval=300s
StartLimitBurst=5

# Service settings
StandardOutput=journal
StandardError=journal
SyslogIdentifier=chatterbox-serial-logger

# Resource limits
LimitNOFILE=4096
LimitNPROC=512

# Security settings (optional, but recommended)
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/chatterbox

# Execution
ExecStart=/usr/local/bin/chatterbox-serial-logger

[Install]
WantedBy=multi-user.target
EOF

sudo chmod 644 /etc/systemd/system/chatterbox-serial-logger.service
```

### Create Service Wrapper Script

Create `/usr/local/bin/chatterbox-serial-logger`:

```bash
sudo tee /usr/local/bin/chatterbox-serial-logger > /dev/null <<'EOF'
#!/usr/bin/env python3
"""Systemd service wrapper for serial log capture."""

import asyncio
import logging
import signal
from pathlib import Path

from chatterbox.config.serial_logging import get_serial_logging_settings
from chatterbox.services.serial_log_capture import SerialLogCapture

# Setup logging to journal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run serial logger service."""
    settings = get_serial_logging_settings()
    logger.info(f"Starting serial logger: {settings.get_summary()}")

    try:
        service = SerialLogCapture(settings=settings)
        logger.info(f"Serial port validation: {service.serial_config.port}")

        # Start background reading
        task = service.start_background_reading()

        # Handle graceful shutdown
        loop = asyncio.get_event_loop()

        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}, shutting down")
            task.cancel()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        # Wait for task
        await task
    except asyncio.CancelledError:
        logger.info("Service shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
EOF

sudo chmod 755 /usr/local/bin/chatterbox-serial-logger
```

## Installation & Startup

### Enable and Start Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable chatterbox-serial-logger

# Start service
sudo systemctl start chatterbox-serial-logger

# Check status
sudo systemctl status chatterbox-serial-logger

# View logs
sudo journalctl -u chatterbox-serial-logger -f
```

## Monitoring

### View Service Status

```bash
# Check if running
systemctl is-active chatterbox-serial-logger

# View recent logs
journalctl -u chatterbox-serial-logger -n 100

# Follow logs in real-time
journalctl -u chatterbox-serial-logger -f

# Show statistics
systemctl show chatterbox-serial-logger
```

### Log File Access

```bash
# View today's logs
cat /var/log/chatterbox/chatterbox-logs_$(date +%Y-%m-%d).json

# Search for errors
grep '"level": "ERROR"' /var/log/chatterbox/chatterbox-logs_*.json

# Count log entries by level
for level in DEBUG INFO WARN ERROR; do
  count=$(grep -c "\"level\": \"$level\"" /var/log/chatterbox/chatterbox-logs_*.json || echo 0)
  echo "$level: $count"
done
```

## Troubleshooting

### Service Won't Start

**Error:** `Service failed with exit code 1`

```bash
# Check logs for details
journalctl -u chatterbox-serial-logger -n 50 --no-pager

# Verify configuration
cat /etc/chatterbox/serial-logger.env

# Check serial port
ls -l /dev/ttyUSB*

# Test manual execution
/usr/local/bin/chatterbox-serial-logger
```

### Serial Port Permission Denied

**Error:** `PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'`

**Solution:**

```bash
# Verify user in dialout group
groups chatterbox

# Add to group if needed
sudo usermod -a -G dialout chatterbox

# Log out and log back in (or restart service)
sudo systemctl restart chatterbox-serial-logger

# Or use udev rules for direct access
sudo tee /etc/udev/rules.d/50-chatterbox-serial.rules > /dev/null <<'EOF'
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0660", GROUP="chatterbox"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```

### High CPU Usage

**Cause:** Serial loop not yielding properly

**Solution:** Adjust buffer settings in configuration:

```bash
# Increase buffer size
CHATTERBOX_SERIAL_BUFFER_SIZE=8192

# Increase timeout
CHATTERBOX_SERIAL_TIMEOUT_SECONDS=2.0

# Restart service
sudo systemctl restart chatterbox-serial-logger
```

### Logs Not Being Captured

**Check points:**

1. Verify serial device is connected:
   ```bash
   ls -l /dev/ttyUSB*
   ```

2. Verify service is running:
   ```bash
   systemctl status chatterbox-serial-logger
   ```

3. Check log directory permissions:
   ```bash
   ls -ld /var/log/chatterbox
   # Should show: drwxr-xr-x ... chatterbox chatterbox
   ```

4. Verify device is sending JSON logs:
   ```bash
   # Read directly from serial (Ctrl+C to stop)
   cat /dev/ttyUSB0
   ```

5. Monitor service in real-time:
   ```bash
   journalctl -u chatterbox-serial-logger -f
   ```

### Disk Space Issues

**Check usage:**

```bash
du -sh /var/log/chatterbox
df -h /var/log

# List files by size
ls -lhS /var/log/chatterbox/chatterbox-logs_*.json | head -10
```

**Solutions:**

1. Reduce retention period in config:
   ```bash
   CHATTERBOX_LOG_RETENTION_DAYS=7  # From 30
   ```

2. Enable compression:
   ```bash
   CHATTERBOX_LOG_ARCHIVE_COMPRESSION=true
   ```

3. Manually cleanup old logs:
   ```bash
   # Find logs older than 7 days
   find /var/log/chatterbox -name "chatterbox-logs_*.json" -mtime +7 -delete
   ```

## Uninstallation

To remove the service:

```bash
# Stop service
sudo systemctl stop chatterbox-serial-logger

# Disable from boot
sudo systemctl disable chatterbox-serial-logger

# Remove service file
sudo rm /etc/systemd/system/chatterbox-serial-logger.service

# Remove wrapper script
sudo rm /usr/local/bin/chatterbox-serial-logger

# Remove configuration
sudo rm -r /etc/chatterbox/

# Remove user (optional)
sudo userdel -r chatterbox

# Reload systemd
sudo systemctl daemon-reload
```

## Performance Tuning

### For High-Volume Logging

```bash
# Increase buffer
CHATTERBOX_SERIAL_BUFFER_SIZE=16384

# Larger log files (reduce rotation overhead)
CHATTERBOX_LOG_MAX_SIZE_BYTES=104857600  # 100 MB

# Longer retention if disk space available
CHATTERBOX_LOG_RETENTION_DAYS=90

# Enable compression for archives
CHATTERBOX_LOG_ARCHIVE_COMPRESSION=true
```

### For Low-Resource Systems

```bash
# Smaller buffer
CHATTERBOX_SERIAL_BUFFER_SIZE=1024

# Smaller log files (faster rotation)
CHATTERBOX_LOG_MAX_SIZE_BYTES=1048576  # 1 MB

# Shorter retention
CHATTERBOX_LOG_RETENTION_DAYS=7

# Disable archiving
CHATTERBOX_LOG_ARCHIVE_ENABLED=false
```

## See Also

- [Serial Logging Schema](serial-logging-schema.md) - JSON format specification
- [Configuration Reference](../src/chatterbox/config/serial_logging.py) - Config classes
- [Service Implementation](../src/chatterbox/services/serial_log_capture.py) - Source code

---

**Last Updated:** 2026-03-25
**Status:** Ready for Production
