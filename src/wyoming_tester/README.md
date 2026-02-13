# Wyoming Satellite Emulator

A command-line tool that emulates a Wyoming protocol satellite device for testing Home Assistant Assist "Push-to-Talk" (PTT) workflows.

## Installation

### From Source (Recommended)
```bash
# Clone or navigate to the project directory
cd wyoming_tester

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### Requirements
- Python 3.10+
- ffmpeg (for audio format conversion)

On Ubuntu/Debian:
```bash
sudo apt install ffmpeg
```

On macOS:
```bash
brew install ffmpeg
```

## Usage

### Basic Usage
```bash
# Test with a WAV file
wyoming-tester --uri tcp://192.168.1.50:10700 --file hello.wav

# Use short options
wyoming-tester -u tcp://ha.local:10700 -f question.wav
```

### Advanced Usage
```bash
# Enable verbose logging to see all Wyoming events
wyoming-tester -u tcp://ha.local:10700 -f test.wav --verbose

# Multi-turn conversation (provide conversation ID from previous run)
wyoming-tester -u tcp://ha.local:10700 -f follow_up.wav --context abc123

# Custom output filename
wyoming-tester -u tcp://ha.local:10700 -f input.wav --output custom_response.wav
```

## Command Line Options

- `--uri`, `-u`: Wyoming endpoint URI (required)
  - Format: `tcp://host:port`
  - Example: `tcp://192.168.1.50:10700`

- `--file`, `-f`: Path to input WAV audio file (required)
  - Will be automatically converted to 16-bit, 16kHz, Mono PCM

- `--context`, `-c`: Conversation ID for multi-turn testing (optional)
  - Use the conversation ID printed from a previous run

- `--verbose`, `-v`: Enable verbose event logging (optional)
  - Shows all Wyoming protocol events for debugging

- `--output`, `-o`: Output filename for TTS response (optional)
  - Default: `response.wav`

## Output

The tool will display:
- 🎤 Transcription: The speech-to-text result
- 🤖 Intent: The detected intent name
- 💬 Conversation ID: For multi-turn conversations
- 💬 Response: The AI assistant's text response
- 🔊 TTS audio saved to: Path where TTS audio is saved

## Workflow

1. **Connection**: Connects to Wyoming endpoint via TCP
2. **Pipeline Setup**: Sends `run-pipeline` event (STT → TTS)
3. **Audio Transmission**:
   - Sends `audio-start` event with format parameters
   - Streams audio data in chunks
   - Sends `audio-stop` event
4. **Response Processing**:
   - Receives transcription and intent results
   - Receives AI response text
   - Receives TTS audio chunks
   - Saves TTS audio to file

## Troubleshooting

### Connection Issues
- Verify Home Assistant Wyoming integration is enabled
- Check firewall settings allow TCP connection on the specified port
- Ensure the URI format is correct: `tcp://host:port`

### Audio Issues
- Input file must be a valid audio format supported by ffmpeg
- Output TTS file will be 16-bit WAV format
- Check file permissions for reading input and writing output

### Protocol Issues
- Use `--verbose` flag to see all Wyoming events
- Check Home Assistant logs for Wyoming integration errors
- Ensure conversation agent is properly configured

## Development

### Project Structure
```
wyoming_tester/
├── __init__.py          # Package initialization
├── cli.py              # Command-line interface
├── protocol.py         # Wyoming protocol client
├── audio.py            # Audio processing utilities
├── pyproject.toml      # Package configuration
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details.