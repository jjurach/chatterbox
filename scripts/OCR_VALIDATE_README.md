# OCR Validation Tool

Python CLI tool for validating Chatterbox device state by reading the display via video feed and using OCR to verify the displayed letter matches the expected device state.

## Features

- 👁️ **Video Feed Reading** - Captures frames from `/dev/video0` or custom video device
- 🔤 **OCR Letter Recognition** - Extracts and recognizes state letters (N, H, S, A, W, P)
- 📊 **Confidence Scoring** - Reports confidence levels for each detection (>95% target)
- 🔄 **Validation Loops** - Run continuous automated validation for stress testing
- 📈 **Batch Validation** - Validate multiple devices from batch file
- 📝 **Report Generation** - Generate JSON reports with detailed statistics
- ⚙️ **GPU Support** - Optional GPU acceleration for faster OCR processing

## Device States

The tool recognizes 6 device states by their display letters:

| Letter | State | Color | Meaning |
|--------|-------|-------|---------|
| N | UNINITIALIZED | Orange | Device booting up |
| H | IDLE | Purple | Ready for wake word |
| S | LISTENING | Blue | Recording voice input |
| A | THINKING | Red | Processing request |
| W | REPLYING | Yellow | Speaking response |
| P | ERROR | Green | Error state |

## Installation

### Prerequisites

- Python 3.8+
- OpenCV (`cv2`)
- EasyOCR
- Requests
- USB webcam or video device at `/dev/video0`

### Setup

```bash
# Install dependencies
pip install opencv-python easyocr requests

# Make script executable
chmod +x scripts/ocr_validate.py
```

### First Run

The first time you run the tool, it will download OCR models (~100MB):

```bash
python scripts/ocr_validate.py --device test
# Downloads language models...
# [download] EasyOCR text detection...
# [download] EasyOCR text recognition...
```

Models are cached locally for subsequent runs.

## Usage

### Single Device Validation

Validate device state once:

```bash
python scripts/ocr_validate.py --device esp32.local
```

**Output:**
```
ℹ️  [2026-02-13T15:30:45.123456] esp32.local: Detected H (85.3% confidence)
```

### Continuous Validation Loop

Run automated validation loop for testing/debugging:

```bash
# Run indefinitely
python scripts/ocr_validate.py --device esp32.local --loop

# Run for specific duration (60 seconds)
python scripts/ocr_validate.py --device esp32.local --loop --duration 60

# Custom interval between validations (10 seconds)
python scripts/ocr_validate.py --device esp32.local --loop --interval 10
```

### Batch Device Validation

Validate multiple devices from batch file:

```bash
python scripts/ocr_validate.py --batch devices.json
```

**devices.json format:**
```json
[
  {"host": "esp32-1.local"},
  {"host": "esp32-2.local"},
  {"host": "192.168.1.100"}
]
```

### Generate Validation Report

Save validation results to JSON file:

```bash
# Single device with report
python scripts/ocr_validate.py --device esp32.local --loop --duration 120 --report report.json

# Batch validation with report
python scripts/ocr_validate.py --batch devices.json --report batch_report.json
```

### Advanced Options

```bash
# Use GPU acceleration for faster OCR
python scripts/ocr_validate.py --device esp32.local --gpu

# Custom video device
python scripts/ocr_validate.py --device esp32.local --video-device /dev/video1

# Custom validation parameters
python scripts/ocr_validate.py \
  --device esp32.local \
  --loop \
  --interval 5 \
  --duration 300 \
  --report results.json
```

## Workflow Examples

### Development Validation

Verify display rendering during development:

```bash
# Quick validation
python scripts/ocr_validate.py --device esp32-dev.local

# Output:
# ✅ [2026-02-13T15:30:45.123456] esp32-dev.local: Detected H (92.1% confidence)
```

### Stress Testing

Run continuous validation to test stability:

```bash
# Run for 5 minutes with 2-second intervals
python scripts/ocr_validate.py \
  --device esp32.local \
  --loop \
  --interval 2 \
  --duration 300 \
  --report stress_test_report.json
```

### State Transition Validation

Verify device cycles through all states correctly:

```bash
# Run validation while manually triggering state changes
python scripts/ocr_validate.py --device esp32.local --loop --interval 3

# In another terminal, trigger state changes via Home Assistant
# Watch OCR tool detect: N → H → S → A → W → H
```

### Production Validation

Validate all production devices and generate report:

```bash
python scripts/ocr_validate.py \
  --batch production_devices.json \
  --report validation_report_$(date +%Y%m%d).json
```

## Output Examples

### Successful Validation

```
👁️  Opened video device: /dev/video0
✅ EasyOCR initialized successfully

ℹ️  [2026-02-13T15:30:45.123456] esp32.local: Detected H (92.1% confidence)

============================================================
📊 Validation Report
============================================================
Generated: 2026-02-13T15:30:45.123456

Summary:
  Total validations: 1
  Successful: 1 ✅
  Failed: 0 ❌
  Success rate: 100.0%

Confidence Statistics:
  Average: 92.1%
  Minimum: 92.1%
  Maximum: 92.1%
============================================================
```

### Continuous Loop with Report

```
==============================================================
🔄 Starting OCR Validation Loop
Device: esp32.local
Interval: 5s
Duration: 60s
==============================================================

[Iteration 1]
ℹ️  [2026-02-13T15:30:45.123456] esp32.local: Detected H (92.1% confidence)

[Iteration 2]
ℹ️  [2026-02-13T15:30:50.234567] esp32.local: Detected S (88.5% confidence)

[Iteration 3]
ℹ️  [2026-02-13T15:30:55.345678] esp32.local: Detected A (95.2% confidence)

⚠️  Validation loop stopped by user

============================================================
📊 Validation Report
============================================================
Generated: 2026-02-13T15:31:05.456789

Summary:
  Total validations: 3
  Successful: 3 ✅
  Failed: 0 ❌
  Success rate: 100.0%

Confidence Statistics:
  Average: 91.9%
  Minimum: 88.5%
  Maximum: 95.2%

By State:
  IDLE: 1 (100.0%)
  LISTENING: 1 (100.0%)
  THINKING: 1 (100.0%)

============================================================
```

## Report Format

JSON report structure:

```json
{
  "generated_at": "2026-02-13T15:30:45.123456",
  "summary": {
    "total_validations": 10,
    "successful": 10,
    "failed": 0,
    "success_rate": "100.0%",
    "confidence_stats": {
      "average": "91.5%",
      "minimum": "85.2%",
      "maximum": "97.8%"
    }
  },
  "by_state": {
    "IDLE": {
      "count": 3,
      "success_rate": "100.0%"
    },
    "LISTENING": {
      "count": 4,
      "success_rate": "100.0%"
    },
    "THINKING": {
      "count": 3,
      "success_rate": "100.0%"
    }
  },
  "results": [
    {
      "timestamp": "2026-02-13T15:30:45.123456",
      "device": "esp32.local",
      "detected_letter": "H",
      "expected_letter": null,
      "confidence": 0.921,
      "state": "IDLE",
      "success": true,
      "error": null
    }
  ]
}
```

## Troubleshooting

### Video Device Not Found

```
Failed to open video device: /dev/video0
```

**Solution:**
- Check device has USB camera connected
- Verify video device exists: `ls -l /dev/video*`
- Use `--video-device` to specify alternative: `--video-device /dev/video1`

### No Letters Detected

```
No letter detected in video feed
```

**Causes and solutions:**
- Camera not pointed at display
- Display brightness too low - adjust device/camera
- OCR confidence too low - check OCR model loaded correctly
- Video stream error - restart device/camera

### Low Confidence Scores

**Typical causes:**
- Suboptimal lighting (too bright/dark)
- Camera angle not perpendicular to display
- Display text too small (should be 100pt+)
- OCR model outdated

**Solutions:**
- Adjust lighting to reduce glare
- Position camera directly facing display
- Verify font size is 120pt in firmware
- Run validation in optimal conditions

### OCR Model Download Fails

```
Error downloading model files
```

**Solution:**
- Check internet connection
- Models cached in `~/.EasyOCR/model_*`
- Delete cache and retry: `rm -rf ~/.EasyOCR/`

### GPU Acceleration Issues

```
CUDA not available
```

**Solution:**
- Remove `--gpu` flag to use CPU
- Install CUDA toolkit if GPU available
- CPU-based OCR is sufficient for this application

## Performance Characteristics

### Validation Speed

- **Per-sample**: ~0.5-1.0 seconds (CPU)
- **Per-sample with GPU**: ~0.2-0.5 seconds
- **Default (5 samples)**: ~2.5-5.0 seconds per validation

### Accuracy

- **Single letter accuracy**: >95% in normal conditions
- **Confidence threshold**: 30% for detection, 95%+ target
- **Lighting tolerance**: Works across wide lighting range

### Resource Usage

- **Memory**: ~1-2 GB (OCR models)
- **CPU**: ~80-100% during OCR (single core)
- **Network**: None required (local video only)

## Development Notes

### Code Structure

- `DeviceState` - Enum for valid device states
- `ValidationResult` - Dataclass for validation results
- `OCRValidator` - Main class handling OCR validation

### Extending the Tool

Add new device states:

```python
class DeviceState(Enum):
    NEW_STATE = 'X'  # Your new state letter

    @property
    def color(self) -> str:
        color_map = {
            # ... existing entries ...
            'X': 'Your Color',
        }
        return color_map.get(self.value, 'Unknown')
```

### Testing Locally

```bash
# Dry-run (verify setup without video)
python scripts/ocr_validate.py --device test --video-device /dev/null

# With actual video
python scripts/ocr_validate.py --device test --video-device /dev/video0
```

## Integration with Automation

### Home Assistant

Use validation in automation:

```yaml
automation:
  - alias: Validate Device States
    trigger:
      platform: time
      at: "12:00:00"
    action:
      - service: shell_command.validate_devices
```

### CI/CD Pipeline

```bash
#!/bin/bash
# ci/validate_devices.sh

python scripts/ocr_validate.py \
  --batch devices.json \
  --report validation_report.json

# Check success rate
SUCCESS_RATE=$(jq '.summary.success_rate' validation_report.json)
if [ "$SUCCESS_RATE" != "100.0%" ]; then
  echo "Validation failed: $SUCCESS_RATE"
  exit 1
fi
```

## Related Documentation

- [OTA Deployment Tool](OTA_DEPLOY_README.md)
- [Device Display Configuration](../firmware/voice-assistant.yaml)
- [ESPHome Display Documentation](https://esphome.io/components/display/index.html)
- [EasyOCR Documentation](https://github.com/JaidedAI/EasyOCR)

## License

Part of the Chatterbox project. See LICENSE file for details.
