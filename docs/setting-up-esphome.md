# Setting Up ESPHome for Chatterbox

A comprehensive guide to installing, configuring, and managing ESPHome firmware for the Chatterbox voice assistant device (ESP32 S3 Box 3).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Initial Device Setup](#initial-device-setup)
4. [Over-The-Air (OTA) Updates](#over-the-air-ota-updates)
5. [Configuration Management](#configuration-management)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Topics](#advanced-topics)

## Prerequisites

### Hardware Requirements

- **Device:** ESP32 S3 Box 3 (or compatible ESP32-S3 board)
- **Connection:** USB cable for initial flashing
- **Network:** Wi-Fi connectivity (2.4GHz or 5GHz)

### Software Requirements

- **Python:** 3.8 or later
- **ESPHome:** 2025.5.0 or later
- **Arduino IDE:** 1.8.19+ (for manual USB flashing if needed)
- **Operating System:** Linux, macOS, or Windows

### Development Setup

```bash
# Install ESPHome via pip
pip install esphome

# Or via pip with specific version
pip install esphome==2025.5.0

# Verify installation
esphome version
```

## Installation

### Option 1: Using pip (Recommended)

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv esphome_env
source esphome_env/bin/activate  # On Windows: esphome_env\Scripts\activate

# Install ESPHome
pip install --upgrade esphome

# Verify installation
esphome version
```

### Option 2: Using Docker

```bash
# Pull ESPHome Docker image
docker pull ghcr.io/esphome/esphome:latest

# Run ESPHome in container
docker run --rm -it \
  -v "$(pwd)":/config \
  -p 6052:6052 \
  ghcr.io/esphome/esphome:latest
```

### Option 3: Home Assistant Add-on

If using Home Assistant, ESPHome is available as an official add-on through the Add-on Store.

## Initial Device Setup

### Step 1: Prepare the Configuration File

Use the provided `firmware/voice-assistant.yaml` as your base configuration:

```bash
# Copy the firmware configuration
cp firmware/voice-assistant.yaml esphome/chatterbox.yaml

# Edit configuration as needed
vim esphome/chatterbox.yaml
```

### Step 2: Create Secrets File

ESPHome uses a `secrets.yaml` file for sensitive information:

```yaml
# esphome/secrets.yaml
wifi_ssid: "Your_SSID"
wifi_password: "Your_WiFi_Password"
ota_password: "Your_OTA_Password_Min_8_Chars"
```

**Security Note:** Never commit secrets.yaml to version control. Add it to .gitignore.

### Step 3: Compile Firmware

```bash
# Validate configuration
esphome validate esphome/chatterbox.yaml

# Compile firmware
esphome compile esphome/chatterbox.yaml

# Output will be in esphome/chatterbox/.esphome/build/
```

### Step 4: Flash to Device (Initial Setup)

#### Option A: Using ESPHome CLI (Recommended)

```bash
# Connect device via USB
# ESPHome will detect the device automatically

esphome run esphome/chatterbox.yaml

# Select the USB port when prompted
# ESPHome will compile and flash automatically
```

#### Option B: Using esptool.py Directly

```bash
# Install esptool
pip install esptool

# Erase device flash
esptool.py -p /dev/ttyUSB0 erase_flash

# Flash compiled binary
esptool.py -p /dev/ttyUSB0 write_flash -z 0x0 \
  esphome/chatterbox/.esphome/build/firmware.bin
```

#### Option C: Using Web Installer

```bash
# Start a local web server
esphome dashboard esphome/

# Open browser to http://localhost:6052
# Use the web interface to flash your device
```

### Step 5: Verify Initial Setup

After flashing, the device should:
1. Boot up (you'll see logs in the serial console)
2. Connect to your Wi-Fi network
3. Appear as "esp32-s3-box-3" in your network
4. Connect to Home Assistant if configured

```bash
# View device logs
esphome logs esphome/chatterbox.yaml

# You should see:
# - Wi-Fi connection attempt
# - Home Assistant API connection
# - Voice assistant initialization
```

## Over-The-Air (OTA) Updates

OTA updates allow you to deploy new firmware to your device over Wi-Fi without needing a USB connection.

### ESPHome OTA Configuration

The `voice-assistant.yaml` file includes OTA configuration:

```yaml
api:

ota:
  - platform: esphome
    id: ota_esphome
    password: !secret ota_password
```

**Configuration Breakdown:**
- `platform: esphome` - Uses ESPHome's native OTA protocol
- `id: ota_esphome` - Unique identifier for this OTA endpoint
- `password` - Password for secure OTA (min 8 characters, from secrets.yaml)

### OTA Update Methods

#### Method 1: Using ESPHome CLI

```bash
# Simple OTA update to device on the network
esphome upload esphome/chatterbox.yaml --device 192.168.1.100

# Or use mDNS hostname
esphome upload esphome/chatterbox.yaml --device chatterbox.local

# With fallback addresses (tries each in order)
esphome upload esphome/chatterbox.yaml \
  --device chatterbox.local \
  --device 192.168.1.100 \
  --device /dev/ttyUSB0
```

#### Method 2: Using Web Dashboard

```bash
# Start dashboard
esphome dashboard esphome/

# In web interface:
# 1. Navigate to your device
# 2. Click the orange "OTA Update" button
# 3. Select the compiled firmware file
# 4. Confirm and wait for completion
```

#### Method 3: Using Home Assistant Integration

If integrated with Home Assistant:

1. Navigate to Settings → Devices & Services
2. Select the ESPHome device
3. Look for the "OTA Update" service
4. Trigger the update

### Python OTA Deployment Script

Create a Python script for automated OTA deployments:

```python
#!/usr/bin/env python3
"""
ESPHome OTA Deployment Tool
Deploys firmware to Chatterbox devices over Wi-Fi
"""

import subprocess
import sys
import argparse
from pathlib import Path

def deploy_firmware(device_address, config_file, upload_speed=460800):
    """Deploy firmware to device via OTA"""

    print(f"🚀 Deploying firmware to {device_address}...")

    try:
        cmd = [
            "esphome",
            "upload",
            str(config_file),
            "--device", device_address,
            "--upload_speed", str(upload_speed)
        ]

        result = subprocess.run(cmd, check=True)
        print(f"✅ Deployment successful!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def deploy_batch(devices_file, config_file):
    """Deploy to multiple devices from file"""

    devices = Path(devices_file).read_text().strip().split('\n')
    results = {}

    for device in devices:
        device = device.strip()
        if not device or device.startswith('#'):
            continue

        print(f"\n{'='*50}")
        success = deploy_firmware(device, config_file)
        results[device] = "✅" if success else "❌"

    # Print summary
    print(f"\n{'='*50}")
    print("📊 Deployment Summary:")
    for device, status in results.items():
        print(f"  {status} {device}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy ESPHome firmware via OTA"
    )
    parser.add_argument(
        "config",
        help="Path to ESPHome configuration (YAML)"
    )
    parser.add_argument(
        "--device",
        help="Device address (IP or hostname)"
    )
    parser.add_argument(
        "--batch",
        help="File with list of devices (one per line)"
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=460800,
        help="Upload speed (default: 460800)"
    )

    args = parser.parse_args()

    if args.device:
        deploy_firmware(args.device, args.config, args.speed)
    elif args.batch:
        deploy_batch(args.batch, args.config)
    else:
        parser.print_help()
        sys.exit(1)
```

**Usage:**

```bash
# Single device
python deploy.py esphome/chatterbox.yaml --device chatterbox.local

# Batch deployment
echo "chatterbox-01.local" > devices.txt
echo "chatterbox-02.local" >> devices.txt
python deploy.py esphome/chatterbox.yaml --batch devices.txt
```

## Configuration Management

### Structure

```
chatterbox/
├── firmware/
│   └── voice-assistant.yaml          # Main device configuration
├── esphome/
│   ├── chatterbox.yaml              # Link to firmware config
│   ├── secrets.yaml                 # Wi-Fi & OTA passwords (GITIGNORE)
│   └── includes/                    # Optional: split configuration
│       ├── audio.yaml
│       ├── display.yaml
│       └── voice_assistant.yaml
└── docs/
    └── setting-up-esphome.md        # This file
```

### Best Practices

#### 1. Use Substitutions for Device-Specific Values

```yaml
substitutions:
  device_name: "chatterbox-01"
  device_friendly: "Chatterbox - Kitchen"
  ota_password: !secret ota_password

esphome:
  name: ${device_name}
  friendly_name: ${device_friendly}
```

#### 2. Split Large Configurations

For large configurations, use `!include` statements:

```yaml
# voice-assistant.yaml
esphome:
  name: chatterbox

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

# Include components
voice_assistant: !include includes/voice_assistant.yaml
display: !include includes/display.yaml
```

#### 3. Version Control

Add to `.gitignore`:

```
# ESPHome
esphome/.esphome/
esphome/secrets.yaml
esphome/chatterbox.yaml
esphome/.DS_Store
*.bin
*.uf2
```

### Environment Variables

Control ESPHome behavior with environment variables:

```bash
# Set upload speed
export ESPHOME_UPLOAD_SPEED=921600

# Enable debug logging
export ESPHOME_LOG_LEVEL=DEBUG

# Set default dashboard port
export ESPHOME_DASHBOARD_PORT=6052
```

## Troubleshooting

### Device Won't Flash

**Problem:** USB connection not detected

**Solutions:**
1. Check USB cable (try different ports)
2. Install CH340 drivers (common on ESP32 devices)
3. Check device permissions on Linux:
   ```bash
   sudo usermod -aG dialout $USER
   newgrp dialout  # Activate group membership
   ```

### Wi-Fi Connection Issues

**Problem:** Device connects to Wi-Fi but can't reach Home Assistant

**Solutions:**
1. Verify SSID and password in secrets.yaml
2. Check device is on same network as Home Assistant
3. Ensure Wi-Fi network is 2.4GHz (some ESP32 don't support 5GHz)
4. Review logs:
   ```bash
   esphome logs esphome/chatterbox.yaml
   ```

### OTA Update Fails

**Problem:** OTA upload fails with "Connection timeout"

**Solutions:**
1. Verify device is on the network: `ping chatterbox.local`
2. Check mDNS resolution: `ping -c 1 chatterbox.local`
3. Ensure OTA password is correct in secrets.yaml
4. Try direct IP address instead of hostname
5. Check Wi-Fi signal strength (move device closer to router)

### Display Not Showing

**Problem:** Display is blank or showing incorrect content

**Solutions:**
1. Verify display configuration in YAML (SPI pins, model)
2. Check physical display connection
3. Review display-related logs
4. Try factory reset: Use factory_reset button (GPIO0)

### High Memory Usage

**Problem:** Device reboots frequently due to out-of-memory

**Solutions:**
1. Review loaded components - disable unused ones
2. Reduce voice assistant buffer sizes
3. Limit number of loaded wake words
4. Increase PSRAM: Check esp32 section in YAML

## Advanced Topics

### Custom Components

Add external components for extended functionality:

```yaml
external_components:
  # State machine component
  - source:
      type: git
      url: https://github.com/muxa/esphome-state-machine.git
      ref: main

  # Custom voice assistant enhancements
  - source:
      type: local
      path: custom_components/
```

### Custom YAML Lambdas

Write C++ code in YAML for complex logic:

```yaml
on_boot:
  priority: 600
  then:
    - lambda: |-
        ESP_LOGI("boot", "Device started with %d bytes free", esp_get_free_heap_size());
```

### Remote Configuration

Store configuration on GitHub and reference it:

```bash
# In your YAML
packages:
  base: github://username/repo/path/to/config.yaml@main
```

### OTA Security Hardening

#### 1. Strong Password

```yaml
ota:
  - platform: esphome
    password: !secret ota_password  # Min 8 chars, strong password
```

#### 2. Disable in Production (if not needed)

```yaml
ota:
  - platform: esphome
    safe_mode: false
    reboot_timeout: 10min
```

#### 3. Monitor OTA Attempts

```yaml
ota:
  - platform: esphome
    on_begin:
      then:
        - logger.log: "OTA update started!"
    on_progress:
      then:
        - logger.log: "OTA progress"
    on_end:
      then:
        - logger.log: "OTA finished!"
    on_error:
      then:
        - logger.log: "OTA failed!"
```

## References & Resources

### Official ESPHome Documentation

- [ESPHome OTA Platform Documentation][1]
- [Over-The-Air Updates - General Guide][2]
- [Web Server OTA Updates][3]
- [Command Line Interface Guide][4]
- [Getting Started with Command Line][5]

### Community Resources

- [ESP for Beginners - OTA Updates 2026][6]
- [Binary Tech Labs - Flashing Guide][7]
- [Community Forum - Windows Flashing][8]
- [LibreTiny - ESPHome Flashing][9]

### Tools & Utilities

- [ESP Web Tools][10] - Browser-based flashing
- [esptool.py][11] - Low-level ESP chip flashing

## Quick Reference

### Common Commands

```bash
# Validate configuration
esphome validate esphome/chatterbox.yaml

# Compile firmware
esphome compile esphome/chatterbox.yaml

# Flash device (USB)
esphome run esphome/chatterbox.yaml

# View device logs
esphome logs esphome/chatterbox.yaml

# OTA update
esphome upload esphome/chatterbox.yaml --device chatterbox.local

# Dashboard (web interface)
esphome dashboard esphome/

# Clean build files
esphome clean esphome/chatterbox.yaml
```

### Environment Setup

```bash
# Create virtual environment
python3 -m venv esphome_env
source esphome_env/bin/activate

# Install dependencies
pip install esphome

# Export helper script
alias esphome='python3 -m esphome'
```

---

## Document Info

**Last Updated:** 2026-02-13
**ESPHome Version:** 2025.5.0+
**Device:** ESP32 S3 Box 3
**Status:** Complete

[1]: https://esphome.io/components/ota/esphome/
[2]: https://esphome.io/components/ota/
[3]: https://esphome.io/components/ota/web_server/
[4]: https://esphome.io/guides/cli/
[5]: https://esphome.io/guides/getting_started_command_line/
[6]: https://www.espforbeginners.com/guides/esphome-ota-updates/
[7]: https://www.binarytechlabs.com/how-to-flash-esphome-firmware-a-friendly-step-by-step-guide/
[8]: https://community.home-assistant.io/t/compile-esphome-firmware-updates-on-a-windows-computer/675385
[9]: https://docs.libretiny.eu/docs/flashing/esphome/
[10]: https://esphome.github.io/esp-web-tools/
[11]: https://github.com/espressif/esptool
