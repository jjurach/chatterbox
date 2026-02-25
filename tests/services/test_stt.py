"""Tests for Speech-to-Text service."""

import numpy as np
import pytest
from unittest.mock import Mock, AsyncMock, patch

from chatterbox.services.stt import WhisperSTTService


@pytest.fixture
def stt_service():
    """Create a mock STT service for testing."""
    with patch('chatterbox.services.stt.get_manager'):
        return WhisperSTTService(model_size="tiny", device="cpu")


@pytest.mark.asyncio
async def test_stt_service_init():
    """Test STT service initialization."""
    with patch('chatterbox.services.stt.get_manager'):
        service = WhisperSTTService(
            model_size="base",
            device="cpu",
            language="en",
        )

        assert service.model_size == "base"
        assert service.device == "cpu"
        assert service.language == "en"


@pytest.mark.asyncio
async def test_stt_service_unload_model(stt_service):
    """Test unloading the Whisper model (no-op with mellona)."""
    # With mellona, unload_model is a no-op
    stt_service.unload_model()
    # No assertion needed, just verify it doesn't raise an error


@pytest.mark.asyncio
async def test_stt_service_transcribe_empty_audio(stt_service):
    """Test transcribing empty audio."""
    # Mock the STT provider
    mock_provider = AsyncMock()
    mock_response = Mock()
    mock_response.text = ""
    mock_response.language = "en"
    mock_provider.transcribe.return_value = mock_response

    stt_service.stt_provider = mock_provider

    # Create empty audio data (16-bit PCM)
    empty_audio = np.zeros(16000, dtype=np.int16).tobytes()

    result = await stt_service.transcribe(empty_audio)

    assert "text" in result
    assert "language" in result
    assert "confidence" in result
    assert result["text"] == ""


@pytest.mark.asyncio
async def test_stt_service_transcribe_with_language():
    """Test transcribing with specific language."""
    with patch('chatterbox.services.stt.get_manager'):
        service = WhisperSTTService(
            model_size="tiny",
            device="cpu",
            language="en",
        )

        # Mock the STT provider
        mock_provider = AsyncMock()
        mock_response = Mock()
        mock_response.text = "test"
        mock_response.language = "en"
        mock_provider.transcribe.return_value = mock_response

        service.stt_provider = mock_provider

        # Create simple audio
        audio = np.zeros(16000, dtype=np.int16).tobytes()
        result = await service.transcribe(audio)

        assert result["language"] == "en"


def test_stt_service_init_parameters():
    """Test STT service parameter validation."""
    with patch('chatterbox.services.stt.get_manager'):
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
