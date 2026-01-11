# Role: Lead AI Platform Engineer
# Goal: Bootstrap a Monorepo for an ESP32-S3-BOX-3B Voice Assistant using Wyoming & LangChain.

## Context:
- Hardware: ESP32-S3-BOX-3B.
- Protocol: Wyoming (for audio streaming).
- Logic: LangChain (for LLM orchestration).
- OS: Ubuntu Workstation.

## Tasks:
1. Create a modern Python project structure using a `src/` directory for the backend.
2. Generate a `firmware/` directory for ESPHome YAML configurations.
3. Use `requirements.txt` for production and `requirements-dev.txt` for development (pytest, black).
4. The `backend/`, `firmware/` directories, and `requirements.txt`, `requirements-dev.txt`, `README.md` files should all be at the project root level.
5. Implement a "Hello World" Wyoming server in Python that returns a static text response.
6. Provide a starter `voice-assistant.yaml` for ESPHome.

## File Contents Required:

### 1. `backend/src/main.py`
- Setup a TCP server using the `wyoming` library.
- Create a simple LangChain pipeline placeholder (e.g., a commented-out section showing where an `LLMChain` would integrate).
- Implement an event handler that responds to 'voice-start' with a "Hello world" event. This response should be a Text-to-Speech (TTS) event to speak 'Hello world', rather than performing actual Automatic Speech Recognition (ASR).

### 2. `firmware/voice-assistant.yaml`
- Use the `esp32_s3_box_3` package.
- Configure the `voice_assistant` component to use the `wyoming` protocol.
- **IMPORTANT**: Leave a placeholder `${backend_ip}` for the Ubuntu host IP.

### 3. `backend/tests/test_server.py`
- A pytest script to ensure the TCP port opens correctly.

### 4. `README.md`
- Instructions for `pip install`.
- Command to run tests: `pytest`.
- Instructions on finding the Ubuntu IP (`hostname -I`) and flashing via `esphome run`.

## Output Style:
- Provide full file content in clear Markdown code blocks.
- Use modern Python 3.10+ type hinting.
