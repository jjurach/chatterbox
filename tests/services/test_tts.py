"""Tests for Text-to-Speech service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from chatterbox.services.tts import PiperTTSService


@pytest.fixture
def mock_tts_provider():
    """Create a mock mellona TTS provider."""
    provider = AsyncMock()
    provider.synthesize = AsyncMock()
    return provider


@pytest.fixture
def tts_service(mock_tts_provider):
    """Create a TTS service for testing with mocked mellona provider."""
    with patch('chatterbox.services.tts.get_manager') as mock_get_manager:
        mock_manager = Mock()
        mock_manager.get_tts_provider.return_value = mock_tts_provider
        mock_get_manager.return_value = mock_manager

        service = PiperTTSService(voice="en_US-lessac-medium", sample_rate=22050)
        service.tts_provider = mock_tts_provider
    return service


@pytest.mark.asyncio
async def test_tts_service_init():
    """Test TTS service initialization."""
    with patch('chatterbox.services.tts.get_manager') as mock_get_manager:
        mock_manager = Mock()
        mock_provider = Mock()
        mock_manager.get_tts_provider.return_value = mock_provider
        mock_get_manager.return_value = mock_manager

        service = PiperTTSService(
            voice="en_US-lessac-medium",
            sample_rate=22050,
        )

        assert service.voice_name == "en_US-lessac-medium"
        assert service.sample_rate == 22050
        assert service.tts_provider is mock_provider


@pytest.mark.asyncio
async def test_tts_service_load_voice(tts_service):
    """Test loading a voice (no-op with mellona)."""
    await tts_service.load_voice()
    # With mellona, load_voice is a no-op since mellona manages lifecycle


@pytest.mark.asyncio
async def test_tts_service_unload_voice(tts_service):
    """Test unloading a voice (no-op with mellona)."""
    tts_service.unload_voice()
    # With mellona, unload_voice is a no-op


@pytest.mark.asyncio
async def test_tts_service_synthesize_empty_text(tts_service, mock_tts_provider):
    """Test synthesizing empty text."""
    # Mock the mellona provider response
    mock_response = Mock()
    mock_response.audio_data = b""
    mock_tts_provider.synthesize.return_value = mock_response

    result = await tts_service.synthesize("")

    assert isinstance(result, bytes)
    mock_tts_provider.synthesize.assert_called_once()


@pytest.mark.asyncio
async def test_tts_service_synthesize_text(tts_service, mock_tts_provider):
    """Test synthesizing text."""
    # Mock the mellona provider response
    mock_response = Mock()
    mock_response.audio_data = b"\x00\x01" * 1000  # Simulate audio data
    mock_tts_provider.synthesize.return_value = mock_response

    text = "Hello world"
    result = await tts_service.synthesize(text)

    assert isinstance(result, bytes)
    assert len(result) > 0
    mock_tts_provider.synthesize.assert_called_once()


@pytest.mark.asyncio
async def test_tts_service_synthesize_long_text(tts_service, mock_tts_provider):
    """Test synthesizing longer text."""
    # Mock the mellona provider response for longer text
    mock_response = Mock()
    mock_response.audio_data = b"\x00\x01" * 5000  # Simulate longer audio
    mock_tts_provider.synthesize.return_value = mock_response

    text = (
        "This is a longer sentence to test the text to speech service. "
        "It should produce a longer audio output compared to shorter sentences."
    )
    result = await tts_service.synthesize(text)

    assert isinstance(result, bytes)
    assert len(result) > 0
    mock_tts_provider.synthesize.assert_called_once()


def test_tts_service_init_parameters():
    """Test TTS service parameter validation."""
    with patch('chatterbox.services.tts.get_manager') as mock_get_manager:
        mock_manager = Mock()
        mock_manager.get_tts_provider.return_value = Mock()
        mock_get_manager.return_value = mock_manager

        service = PiperTTSService(
            voice="en_US-grayson-medium",
            sample_rate=24000,
        )

        assert service.voice_name == "en_US-grayson-medium"
        assert service.sample_rate == 24000
