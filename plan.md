# Plan: Expose Whisper STT and Piper TTS Services

## Overview
Extend Chatterbox3b to provide dedicated Speech-to-Text (Whisper) and Text-to-Speech (Piper) services through both Wyoming protocol and RESTful JSON endpoints. This allows Home Assistant and other clients to use STT/TTS capabilities independently of the full voice assistant pipeline.

## Current Architecture Analysis
- Wyoming server currently receives `Transcript` events (pre-transcribed text) and sends `Synthesize` events (text for client-side TTS)
- No existing STT/TTS integration - transcription and synthesis happen externally
- Protocol-agnostic core with adapter pattern for different protocols
- Tool system for agent extensions

## Implementation Plan

### Phase 1: Dependencies and Core Services
1. **Add Dependencies**
   - `faster-whisper` for OpenAI Whisper STT
   - `piper-tts` for neural TTS synthesis
   - `fastapi` and `uvicorn` for REST API
   - Update `requirements.txt` and `pyproject.toml`

2. **Create STT/TTS Service Modules**
   - `cackle/services/stt.py` - Whisper integration
   - `cackle/services/tts.py` - Piper integration
   - Configuration management for models and voices

### Phase 2: Extend Wyoming Protocol Support
1. **STT Service via Wyoming**
   - Handle `Transcribe` events by buffering `AudioChunk`s
   - On `AudioStop`, run Whisper transcription
   - Return `Transcript` event with transcribed text
   - Support different Whisper model sizes (tiny, base, small, medium, large)

2. **TTS Service via Wyoming**
   - Handle `Synthesize` events by running Piper TTS
   - Stream synthesized audio as `AudioChunk` events
   - Support voice selection and audio format configuration

3. **Service Mode Configuration**
   - Add server modes: `full` (current VA), `stt_only`, `tts_only`, `combined`
   - Allow running dedicated STT/TTS servers on different ports

### Phase 3: REST API Implementation
1. **Create REST Adapter**
   - `cackle/adapters/rest/` directory
   - FastAPI application with endpoints:
     - `POST /stt` - Accept audio file/data, return JSON `{"text": "transcription"}`
     - `POST /tts` - Accept JSON `{"text": "input"}`, return audio file
   - Support multiple audio formats (WAV, MP3, FLAC)
   - Authentication and rate limiting

2. **Unified Server Architecture**
   - Option to run Wyoming and REST on same server instance
   - Shared STT/TTS services between protocols
   - Configurable ports (Wyoming: 10700, REST: 8080)

### Phase 4: Configuration and Settings
1. **Add Configuration Options**
   ```python
   # STT settings
   STT_MODEL = "base"  # tiny, base, small, medium, large
   STT_DEVICE = "cpu"   # cpu, cuda
   STT_LANGUAGE = "en"  # auto detection or specific

   # TTS settings
   TTS_VOICE = "en_US-lessac-medium"  # Piper voice name
   TTS_FORMAT = "wav"                 # wav, mp3
   TTS_SAMPLE_RATE = 22050

   # Server settings
   REST_PORT = 8080
   ENABLE_REST = True
   ENABLE_WYOMING_STT = True
   ENABLE_WYOMING_TTS = True
   ```

2. **Environment Variables**
   - Load from `.env` file or system environment
   - Validation and defaults

### Phase 5: Integration and Tools
1. **Agent Tools (Optional)**
   - `cackle/tools/builtin/stt_tool.py` - Allow agent to transcribe audio
   - `cackle/tools/builtin/tts_tool.py` - Allow agent to synthesize speech
   - Useful for agent processing audio files or generating responses

2. **Update Main Server**
   - Modify `src/main.py` to support service modes
   - CLI flags for enabling/disabling services
   - Graceful startup validation (check models downloaded)

### Phase 6: Testing and Documentation
1. **Unit Tests**
   - STT/TTS service functions
   - REST endpoint handlers
   - Wyoming event processing

2. **Integration Tests**
   - Full Wyoming STT/TTS pipeline
   - REST API requests/responses
   - Audio format handling

3. **Documentation Updates**
   - Update `docs/architecture.md` with new services
   - Add `docs/stt_tts_services.md` with usage examples
   - Update `docs/quickstart.md` with service setup
   - REST API documentation

## Usage Examples

### Wyoming Protocol
```python
# STT service
# Client sends: AudioStart, AudioChunk*, AudioStop, Transcribe
# Server responds: Transcript(text="hello world")

# TTS service
# Client sends: Synthesize(text="hello world")
# Server responds: AudioStart, AudioChunk*, AudioStop
```

### REST API
```bash
# STT
curl -X POST http://localhost:8080/stt \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav

# Response: {"text": "Hello world", "language": "en"}

# TTS
curl -X POST http://localhost:8080/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output speech.wav
```

## Benefits
- **Modular Services**: STT/TTS available independently of full VA
- **Protocol Flexibility**: Same services via Wyoming or REST
- **Home Assistant Integration**: Direct service access without full pipeline
- **Extensibility**: Easy to add more AI services (vision, etc.)
- **Performance**: Dedicated servers for specific workloads

## Migration Path
- Keep existing VA functionality unchanged
- Add new service modes as opt-in features
- Gradual rollout with backward compatibility
- Update examples and documentation incrementally

## Completion Criteria
The feature implementation is considered "done" when:
- All phases (1-6) of the implementation plan are completed
- All pytest tests complete successfully
- Documentation is updated and accurate
- Example usage works as demonstrated