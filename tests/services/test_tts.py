"""Tests for Text-to-Speech service."""

import pytest

from cackle.services.tts import PiperTTSService


@pytest.fixture
def tts_service():
    """Create a TTS service for testing."""
    return PiperTTSService(voice="en_US-lessac-medium", sample_rate=22050)


@pytest.mark.asyncio
async def test_tts_service_init():
    """Test TTS service initialization."""
    service = PiperTTSService(
        voice="en_US-lessac-medium",
        sample_rate=22050,
    )

    assert service.voice_name == "en_US-lessac-medium"
    assert service.sample_rate == 22050
    assert not service._loaded


@pytest.mark.asyncio
async def test_tts_service_load_voice(tts_service):
    """Test loading a Piper voice."""
    await tts_service.load_voice()

    assert tts_service._loaded
    assert tts_service.voice is not None


@pytest.mark.asyncio
async def test_tts_service_unload_voice(tts_service):
    """Test unloading a Piper voice."""
    await tts_service.load_voice()
    assert tts_service._loaded

    tts_service.unload_voice()
    assert not tts_service._loaded
    assert tts_service.voice is None


@pytest.mark.asyncio
async def test_tts_service_synthesize_empty_text(tts_service):
    """Test synthesizing empty text."""
    await tts_service.load_voice()

    result = await tts_service.synthesize("")

    # Empty text should produce minimal or empty audio
    assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_tts_service_synthesize_text(tts_service):
    """Test synthesizing text."""
    await tts_service.load_voice()

    text = "Hello world"
    result = await tts_service.synthesize(text)

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_tts_service_synthesize_long_text(tts_service):
    """Test synthesizing longer text."""
    await tts_service.load_voice()

    text = (
        "This is a longer sentence to test the text to speech service. "
        "It should produce a longer audio output compared to shorter sentences."
    )
    result = await tts_service.synthesize(text)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_tts_service_init_parameters():
    """Test TTS service parameter validation."""
    service = PiperTTSService(
        voice="en_US-grayson-medium",
        sample_rate=24000,
    )

    assert service.voice_name == "en_US-grayson-medium"
    assert service.sample_rate == 24000
