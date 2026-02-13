# OTA Deployment Tool

Python CLI tool for deploying firmware to ESP32 Chatterbox devices over Wi-Fi using the ESPHome OTA protocol.

## Features

- 🎯 **Single Device Deployment** - Deploy to individual devices by IP or hostname
- 📦 **Batch Deployment** - Deploy to multiple devices from JSON or CSV files
- 🔐 **Password Authentication** - Secure OTA endpoint with per-device passwords
- ⏱️ **Retry Logic** - Automatic retries with exponential backoff for resilience
- 📊 **Progress Indication** - Visual feedback during deployment
- 🛡️ **Error Handling** - Comprehensive error messages and connection validation
- 🌐 **Hostname Resolution** - Support for both IP addresses and mDNS hostnames

## Installation

### Prerequisites

- Python 3.8+
- `requests` library (used for HTTP communication)

### Setup

```bash
# Install dependencies
pip install requests

# Make script executable
chmod +x scripts/ota_deploy.py
```

## Usage

### Single Device Deployment

Deploy to a single device by IP address or hostname:

```bash
# Using IP address
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin

# Using mDNS hostname (e.g., esp32.local)
python scripts/ota_deploy.py --device esp32.local --binary firmware.bin

# With password authentication
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin --password mypassword
```

### Batch Deployment

Deploy to multiple devices using a batch file:

```bash
python scripts/ota_deploy.py --binary firmware.bin --batch devices.json
```

#### JSON Format

Create a `devices.json` file:

```json
[
  {
    "host": "192.168.1.100",
    "password": "device_specific_password"
  },
  {
    "host": "esp32-2.local"
  },
  {
    "host": "192.168.1.102",
    "password": "another_password"
  }
]
```

#### CSV Format

Create a `devices.csv` file:

```csv
host,password
192.168.1.100,device_specific_password
esp32-2.local,
192.168.1.102,another_password
```

### Advanced Options

```bash
# Custom OTA port (default: 8266)
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin --port 8266

# Custom retry count (default: 3)
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin --retries 5

# Custom timeout in seconds (default: 60)
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin --timeout 120

# Combine options
python scripts/ota_deploy.py \
  --device 192.168.1.100 \
  --binary firmware.bin \
  --password mypassword \
  --port 8266 \
  --retries 3 \
  --timeout 60
```

## Workflow Examples

### Development Workflow

```bash
# Build firmware with ESPHome
esphome compile firmware/voice-assistant.yaml

# Deploy to device over OTA
python scripts/ota_deploy.py \
  --device esp32-dev.local \
  --binary .esphome/build/esp32-s3-box-3/.pioenvs/esp32-s3-box-3/firmware.bin \
  --password dev_password
```

### Production Deployment

```bash
# Deploy to all production devices
python scripts/ota_deploy.py \
  --binary firmware.bin \
  --batch devices.json
```

### Staged Rollout

```bash
# Stage 1: Deploy to canary device
python scripts/ota_deploy.py --device canary.local --binary firmware.bin

# Stage 2: Deploy to group 1 after validation
python scripts/ota_deploy.py --batch group1.json --binary firmware.bin

# Stage 3: Deploy to group 2 after validation
python scripts/ota_deploy.py --batch group2.json --binary firmware.bin
```

## Configuration

### Device OTA Settings

Ensure your ESPHome configuration includes OTA component:

```yaml
ota:
  - platform: esphome
    id: ota_esphome
    password: "your_password_here"  # Optional
```

### Default Settings

The tool uses these defaults (all customizable):

| Setting | Default | Override |
|---------|---------|----------|
| OTA Port | 8266 | `--port` |
| Retries | 3 | `--retries` |
| Timeout | 60s | `--timeout` |

## Password Management

### Single Device

Pass password via command line:

```bash
python scripts/ota_deploy.py --device esp32.local --binary fw.bin --password mypassword
```

### Batch Deployment

**Option 1: Per-device passwords (recommended)**

Specify password in batch file (JSON/CSV):

```json
[
  {"host": "device1.local", "password": "password1"},
  {"host": "device2.local", "password": "password2"}
]
```

**Option 2: Global password**

Apply same password to all devices:

```bash
python scripts/ota_deploy.py --batch devices.json --binary fw.bin --password global_password
```

### Security Best Practices

- ✅ Use per-device passwords when possible
- ✅ Store batch files with sensitive passwords securely
- ✅ Don't commit passwords to version control (use `.gitignore`)
- ✅ Rotate passwords regularly
- ✅ Use strong, unique passwords per device

## Error Handling

The tool handles various error conditions:

| Error | Cause | Solution |
|-------|-------|----------|
| Binary file not found | Invalid `--binary` path | Verify firmware file exists |
| Connection timeout | Device not responding | Check IP/hostname, ensure device is online |
| Authentication failed | Wrong password | Verify OTA password in config |
| Bad request (400) | Invalid binary format | Verify binary is ESPHome firmware |
| Server error (500+) | Device-side issue | Check device logs, restart device |

### Retry Logic

The tool automatically retries failed requests with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: After 1 second
- Attempt 3: After 2 seconds
- Attempt 4: After 4 seconds

Customize with `--retries`:

```bash
python scripts/ota_deploy.py --device esp32.local --binary fw.bin --retries 5
```

## Output Examples

### Successful Single Device

```
📦 Deploying to 192.168.1.100 (192.168.1.100:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ✅ Deployment successful!
```

### Successful Batch

```
🚀 Starting batch deployment to 3 device(s)
   Binary: firmware.bin (1.2 MB)
============================================================

📦 Deploying to 192.168.1.100 (192.168.1.100:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ✅ Deployment successful!

📦 Deploying to esp32-2.local (192.168.1.101:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ✅ Deployment successful!

📦 Deploying to 192.168.1.102 (192.168.1.102:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ✅ Deployment successful!

============================================================

📊 Deployment Summary:
   Total devices: 3
   Successful:   3 ✅
   Failed:       0 ❌
   Success rate: 100.0%
```

### Failed Deployment

```
📦 Deploying to 192.168.1.100 (192.168.1.100:8266)
   Binary size: 1.2 MB
   Binary hash: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ⏳ Uploading...
   ❌ Deployment failed: Connection timeout - device not responding

❌ Error: Connection timeout - device not responding
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All deployments successful |
| 1 | One or more deployments failed |
| 130 | Deployment cancelled by user (Ctrl+C) |

## Troubleshooting

### Device Not Found

```bash
# Verify hostname resolves
ping esp32.local

# Or use IP directly
python scripts/ota_deploy.py --device 192.168.1.100 --binary firmware.bin
```

### Connection Timeout

```bash
# Increase timeout
python scripts/ota_deploy.py --device esp32.local --binary fw.bin --timeout 120

# Check device is online and OTA is enabled
esphome logs firmware/voice-assistant.yaml
```

### Authentication Failed

```bash
# Verify password matches device configuration
# Check voice-assistant.yaml for OTA password setting

# Try deployment with correct password
python scripts/ota_deploy.py --device esp32.local --binary fw.bin --password correct_password
```

### Batch File Issues

```bash
# Validate JSON syntax
python -m json.tool devices.json

# Check CSV format (header, proper escaping)
cat devices.csv | head
```

## Development Notes

### Code Structure

- `OTADeployer` - Main class handling deployment logic
- `load_batch_file()` - Parse JSON/CSV batch files
- `main()` - CLI entry point with argument parsing

### Adding Features

To extend the tool:

1. Add new methods to `OTADeployer` class
2. Update argument parser in `main()`
3. Add tests if modifying core logic
4. Update documentation

### Testing Locally

```bash
# Create test device configuration
cat > test_devices.json << EOF
[
  {"host": "192.168.1.100"}
]
EOF

# Dry-run test (verify arguments parse correctly)
python scripts/ota_deploy.py --binary firmware.bin --batch test_devices.json --timeout 5
```

## Related Documentation

- [ESPHome OTA Documentation](https://esphome.io/components/ota.html)
- [ESP32 S3 Box 3 Setup](../../docs/setup.md)
- [Device Configuration](../../firmware/voice-assistant.yaml)

## License

Part of the Chatterbox project. See LICENSE file for details.
