"""Tests for Speech-to-Text service."""

import numpy as np
import pytest

from chatterbox.services.stt import WhisperSTTService


@pytest.fixture
def stt_service():
    """Create a mock STT service for testing."""
    return WhisperSTTService(model_size="tiny", device="cpu")


@pytest.mark.asyncio
async def test_stt_service_init():
    """Test STT service initialization."""
    service = WhisperSTTService(
        model_size="base",
        device="cpu",
        language="en",
    )

    assert service.model_size == "base"
    assert service.device == "cpu"
    assert service.language == "en"
    assert not service._loaded


@pytest.mark.asyncio
async def test_stt_service_load_model(stt_service):
    """Test loading the Whisper model."""
    await stt_service.load_model()

    assert stt_service._loaded
    assert stt_service.model is not None


@pytest.mark.asyncio
async def test_stt_service_unload_model(stt_service):
    """Test unloading the Whisper model."""
    await stt_service.load_model()
    assert stt_service._loaded

    stt_service.unload_model()
    assert not stt_service._loaded
    assert stt_service.model is None


@pytest.mark.asyncio
async def test_stt_service_transcribe_empty_audio(stt_service):
    """Test transcribing empty audio."""
    await stt_service.load_model()

    # Create empty audio data (16-bit PCM)
    empty_audio = np.zeros(16000, dtype=np.int16).tobytes()

    result = await stt_service.transcribe(empty_audio)

    assert "text" in result
    assert "language" in result
    assert "confidence" in result
    assert result["text"] == ""  # Should be empty for silence


@pytest.mark.asyncio
async def test_stt_service_transcribe_with_language():
    """Test transcribing with specific language."""
    service = WhisperSTTService(
        model_size="tiny",
        device="cpu",
        language="en",
    )
    await service.load_model()

    # Create simple audio
    audio = np.zeros(16000, dtype=np.int16).tobytes()
    result = await service.transcribe(audio)

    assert result["language"] is not None or result["language"] == "en"


def test_stt_service_init_parameters():
    """Test STT service parameter validation."""
    service = WhisperSTTService(
        model_size="small",
        device="cuda",
        language="en",
        compute_type="float16",
    )

    assert service.model_size == "small"
    assert service.device == "cuda"
    assert service.language == "en"
    assert service.compute_type == "float16"
