"""FastAPI-based REST API for STT/TTS services."""

import io
import logging
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
import numpy as np

from cackle.services import WhisperSTTService, PiperTTSService
from cackle.agent import VoiceAssistantAgent

logger = logging.getLogger(__name__)


def create_app(
    mode: str = "full",
    stt_model: str = "base",
    stt_device: str = "cpu",
    tts_voice: str = "en_US-lessac-medium",
    ollama_base_url: str = "http://localhost:11434/v1",
    ollama_model: str = "llama3.1:8b",
    ollama_temperature: float = 0.7,
    conversation_window_size: int = 3,
) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        mode: Server mode ('full', 'stt_only', 'tts_only', 'combined')
        stt_model: Whisper model size
        stt_device: STT device (cpu, cuda)
        tts_voice: Piper voice name
        ollama_base_url: Ollama API base URL
        ollama_model: Ollama model name
        ollama_temperature: Model temperature
        conversation_window_size: Conversation history size

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Chatterbox3B STT/TTS API",
        description="Speech-to-Text and Text-to-Speech services",
        version="0.1.0",
    )

    # Initialize services
    stt_service: Optional[WhisperSTTService] = None
    tts_service: Optional[PiperTTSService] = None
    agent: Optional[VoiceAssistantAgent] = None

    if mode in ("stt_only", "combined"):
        stt_service = WhisperSTTService(
            model_size=stt_model,
            device=stt_device,
        )

    if mode in ("tts_only", "combined", "full"):
        tts_service = PiperTTSService(voice=tts_voice)

    if mode in ("full", "combined"):
        agent = VoiceAssistantAgent(
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            ollama_temperature=ollama_temperature,
            conversation_window_size=conversation_window_size,
        )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "mode": mode,
            "services": {
                "stt": stt_service is not None,
                "tts": tts_service is not None,
                "agent": agent is not None,
            },
        }

    @app.post("/stt")
    async def transcribe_audio(file: UploadFile = File(...)):
        """Transcribe audio to text.

        Accepts audio files in WAV, MP3, FLAC formats.

        Args:
            file: Audio file to transcribe

        Returns:
            JSON with transcribed text and metadata
        """
        if not stt_service:
            raise HTTPException(
                status_code=503,
                detail="STT service not available in this mode",
            )

        try:
            # Read audio file
            audio_data = await file.read()

            # For raw PCM, use directly; for file formats, let Whisper handle it
            if file.content_type == "audio/wav" or file.filename.endswith(".wav"):
                # Skip WAV header for raw PCM
                if audio_data.startswith(b"RIFF"):
                    # Parse WAV header to get PCM data
                    audio_data = _extract_wav_pcm(audio_data)

            # Transcribe
            result = await stt_service.transcribe(audio_data)

            return {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": result.get("confidence", 0.0),
            }

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/stt/file")
    async def transcribe_file(file: UploadFile = File(...)):
        """Transcribe audio file using file path.

        Useful for larger files. Supports WAV, MP3, FLAC formats.

        Args:
            file: Audio file to transcribe

        Returns:
            JSON with transcribed text and metadata
        """
        if not stt_service:
            raise HTTPException(
                status_code=503,
                detail="STT service not available in this mode",
            )

        try:
            import tempfile
            import os

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                result = await stt_service.transcribe_file(tmp_path)
                return {
                    "text": result["text"],
                    "language": result.get("language", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                }
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Error transcribing file: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/tts")
    async def synthesize_text(request: Request):
        """Synthesize text to speech.

        Request body: {"text": "Hello world"}

        Returns:
            Audio file in WAV format
        """
        if not tts_service:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available in this mode",
            )

        try:
            body = await request.json()
            text = body.get("text", "")

            if not text:
                raise HTTPException(status_code=400, detail="Text field is required")

            # Synthesize
            audio_bytes = await tts_service.synthesize(text)

            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/wav",
                headers={"Content-Disposition": "attachment; filename=speech.wav"},
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error synthesizing text: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/chat")
    async def chat(request: Request):
        """Send text to agent and get response (requires 'full' or 'combined' mode).

        Request body: {"text": "What time is it?"}

        Returns:
            JSON with agent response
        """
        if not agent:
            raise HTTPException(
                status_code=503,
                detail="Agent not available in this mode",
            )

        try:
            body = await request.json()
            text = body.get("text", "")

            if not text:
                raise HTTPException(status_code=400, detail="Text field is required")

            response = await agent.process_input(text)

            return {"response": response}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/stt-chat-tts")
    async def full_pipeline(file: UploadFile = File(...)):
        """Full pipeline: transcribe audio → chat → synthesize response.

        Only available in 'full' mode.

        Args:
            file: Audio file to process

        Returns:
            JSON with transcription, response, and audio synthesis details
        """
        if mode != "full":
            raise HTTPException(
                status_code=503,
                detail="Full pipeline only available in 'full' mode",
            )

        try:
            # Transcribe
            audio_data = await file.read()
            if audio_data.startswith(b"RIFF"):
                audio_data = _extract_wav_pcm(audio_data)

            transcription = await stt_service.transcribe(audio_data)

            # Chat
            response = await agent.process_input(transcription["text"])

            # Synthesize
            audio_bytes = await tts_service.synthesize(response)

            return {
                "transcription": transcription["text"],
                "language": transcription.get("language"),
                "agent_response": response,
                "audio_bytes": len(audio_bytes),
                "audio_format": "wav",
            }

        except Exception as e:
            logger.error(f"Error in full pipeline: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    @app.on_event("startup")
    async def startup_event():
        """Load models on startup."""
        if stt_service:
            logger.info("Preloading STT model...")
            await stt_service.load_model()

        if tts_service:
            logger.info("Preloading TTS voice...")
            await tts_service.load_voice()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        if stt_service:
            stt_service.unload_model()
        if tts_service:
            tts_service.unload_voice()

    return app


def _extract_wav_pcm(wav_data: bytes) -> bytes:
    """Extract PCM data from WAV file.

    Args:
        wav_data: Complete WAV file bytes

    Returns:
        Raw PCM audio data
    """
    import wave
    import io

    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wav_file:
            # Read all frames
            frames = wav_file.readframes(wav_file.getnframes())
            return frames
    except Exception as e:
        logger.warning(f"Could not parse WAV header, using raw data: {e}")
        # Fallback to raw data (skip potential WAV header)
        if wav_data.startswith(b"RIFF"):
            # Skip RIFF header (44 bytes is common)
            return wav_data[44:]
        return wav_data
