# ESP32-S3-BOX-3B Voice Assistant with Wyoming & LangChain

A monorepo for bootstrapping a voice assistant on the ESP32-S3-BOX-3B hardware using the Wyoming protocol and LangChain for LLM orchestration.

## Project Structure

```
.
├── backend/                      # Python Wyoming server for audio processing
│   ├── src/
│   │   └── main.py              # Main Wyoming server implementation
│   └── tests/
│       └── test_server.py       # Pytest tests for the server
├── firmware/                     # ESPHome configurations for the ESP32-S3-BOX-3B
│   └── voice-assistant.yaml     # ESPHome device configuration
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies (pytest, black, etc.)
└── README.md                     # This file
```

## Prerequisites

- **Hardware**: ESP32-S3-BOX-3B
- **OS**: Ubuntu Workstation (or any Linux/macOS with Python 3.10+)
- **Python**: 3.10 or higher
- **ESPHome**: For flashing firmware to the device
- **pip**: Python package manager

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chatterbox3b
```

### 2. Set Up Python Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

For production:

```bash
pip install -r requirements.txt
```

For development (includes testing and linting tools):

```bash
pip install -r requirements-dev.txt
```

## Usage

### Running the Wyoming Server

Start the Wyoming server on your Ubuntu host:

```bash
python backend/src/main.py
```

The server will bind to `0.0.0.0:10700` and wait for connections from the ESP32-S3-BOX-3B device.

### Running Tests

Execute the test suite with pytest:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with coverage:

```bash
pytest --cov=backend
```

### Code Formatting

Format code with Black:

```bash
black backend/
```

Sort imports with isort:

```bash
isort backend/
```

## Flashing the Device

### Step 1: Find Your Ubuntu Host IP

Get your Ubuntu machine's IP address:

```bash
hostname -I
```

This will output something like: `192.168.1.100 172.17.0.1`

Use the first IP (your local network IP).

### Step 2: Update the ESPHome Configuration

Edit `firmware/voice-assistant.yaml` and replace the placeholder:

```yaml
substitutions:
  backend_ip: "192.168.1.100"  # Use your actual IP from Step 1
```

### Step 3: Flash the Device

Install ESPHome if you haven't already:

```bash
pip install esphome
```

Flash the device via USB (make sure the device is connected):

```bash
cd firmware
esphome run voice-assistant.yaml
```

Follow the ESPHome prompts to select the USB serial port.

### Step 4: Verify Connection

Once flashed:

1. Power on the ESP32-S3-BOX-3B
2. Ensure it's connected to the same WiFi network as your Ubuntu host
3. Start the Wyoming server: `python backend/src/main.py`
4. The device should connect and be ready to process voice commands

## Architecture

### Backend Server

The Wyoming server in `backend/src/main.py`:
- Listens for incoming audio streams from the ESP32-S3-BOX-3B
- Processes audio using the Wyoming protocol
- Currently responds with a static "Hello world" TTS response
- Contains placeholders for LangChain LLM integration

### Firmware

The ESPHome configuration in `firmware/voice-assistant.yaml`:
- Configures the ESP32-S3-BOX-3B hardware peripherals (microphone, speaker, display)
- Connects to the Wyoming server for audio processing
- Handles WiFi connectivity

## LangChain Integration

The backend server includes commented placeholders for integrating LangChain:

```python
# Placeholder for LangChain integration
# from langchain.llms import OpenAI
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
```

To integrate an LLM:

1. Install LangChain dependencies in `requirements.txt`
2. Uncomment the placeholder imports
3. Modify the `_create_hello_world_response()` method to use your LLM chain
4. Process the audio content through your chain before generating the TTS response

## Development

### Project Structure Best Practices

- Use `src/` directory for the main application code
- Keep tests in `backend/tests/`
- Use type hints (Python 3.10+)
- Follow PEP 8 with Black for formatting

### Adding Dependencies

For production dependencies, add to `requirements.txt`:

```bash
pip install <package-name>
pip freeze > requirements.txt
```

For development-only dependencies, add to `requirements-dev.txt`.

## Troubleshooting

### Device Won't Connect

- Verify the `backend_ip` in `firmware/voice-assistant.yaml` matches your Ubuntu host
- Ensure both devices are on the same WiFi network
- Check firewall settings on Ubuntu (port 10700 should be open)
- Verify the Wyoming server is running: `python backend/src/main.py`

### Server Port Already in Use

If port 10700 is already in use, modify `backend/src/main.py`:

```python
server = VoiceAssistantServer(host="0.0.0.0", port=9999)  # Custom port
```

Update the port in `firmware/voice-assistant.yaml` accordingly.

### Serial Port Issues During Flashing

On Linux, you may need to add your user to the dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

## Resources

- [Wyoming Protocol Documentation](https://www.rhasspy.org/wyoming/)
- [ESPHome Documentation](https://esphome.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [ESP32-S3-BOX-3B Hardware Reference](https://github.com/espressif/esp-box)

## License

[Specify your license here]

## Contributing

[Add contributing guidelines here]
