"""Tests for wyoming_tester package."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydub import AudioSegment

from wyoming_tester.audio import AudioProcessor
from wyoming_tester.protocol import WyomingClient


class TestAudioProcessor:
    """Test AudioProcessor functionality."""

    def test_init(self):
        """Test AudioProcessor initialization."""
        processor = AudioProcessor()
        assert processor.SAMPLE_RATE == 16000
        assert processor.BIT_DEPTH == 16
        assert processor.CHANNELS == 1
        assert processor.CHUNK_SIZE == 1024

    def test_validate_wyoming_format(self):
        """Test Wyoming format validation."""
        processor = AudioProcessor()

        # Create a valid Wyoming format audio
        audio = AudioSegment.silent(
            duration=1000,  # 1 second
        ).set_frame_rate(16000).set_sample_width(2).set_channels(1)

        assert processor.validate_wyoming_format(audio)

        # Test invalid format
        invalid_audio = AudioSegment.silent(
            duration=1000,
        ).set_frame_rate(44100).set_sample_width(2).set_channels(1)  # Wrong sample rate

        assert not processor.validate_wyoming_format(invalid_audio)

    def test_get_pcm_chunks(self):
        """Test PCM chunk generation."""
        processor = AudioProcessor()

        # Create test audio
        audio = AudioSegment.silent(
            duration=100,  # Short audio
        ).set_frame_rate(16000).set_sample_width(2).set_channels(1)

        chunks = list(processor.get_pcm_chunks(audio))

        # Should have at least one chunk
        assert len(chunks) > 0

        # Each chunk should be bytes
        for chunk in chunks:
            assert isinstance(chunk, bytes)
            assert len(chunk) <= processor.CHUNK_SIZE

    def test_reconstruct_from_chunks(self):
        """Test audio reconstruction from chunks."""
        processor = AudioProcessor()

        # Create original audio
        original = AudioSegment.silent(
            duration=500,
        ).set_frame_rate(16000).set_sample_width(2).set_channels(1)

        # Get chunks
        chunks = list(processor.get_pcm_chunks(original))

        # Reconstruct
        reconstructed = processor.reconstruct_from_chunks(chunks)

        # Should have same properties
        assert reconstructed.frame_rate == original.frame_rate
        assert reconstructed.sample_width == original.sample_width
        assert reconstructed.channels == original.channels

    @patch('pydub.AudioSegment.from_file')
    def test_load_and_convert(self, mock_from_file):
        """Test audio loading and conversion."""
        processor = AudioProcessor()

        # Mock audio file
        mock_audio = Mock()
        mock_audio.frame_rate = 44100
        mock_audio.sample_width = 2
        mock_audio.channels = 2
        mock_from_file.return_value = mock_audio

        # Mock set methods
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio

        with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
            result = processor.load_and_convert(Path(tmp.name))

            # Verify conversion calls
            mock_audio.set_frame_rate.assert_called_with(16000)
            mock_audio.set_sample_width.assert_called_with(2)
            mock_audio.set_channels.assert_called_with(1)

    def test_save_wav(self):
        """Test WAV file saving."""
        processor = AudioProcessor()

        # Create test audio
        audio = AudioSegment.silent(
            duration=500,
        ).set_frame_rate(16000).set_sample_width(2).set_channels(1)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            processor.save_wav(audio, output_path)
            assert output_path.exists()

            # Verify we can load it back
            reloaded = AudioSegment.from_file(str(output_path))
            assert reloaded.frame_rate == 16000

        finally:
            output_path.unlink(missing_ok=True)


class TestWyomingClient:
    """Test WyomingClient functionality."""

    def test_init_valid_uri(self):
        """Test client initialization with valid URI."""
        client = WyomingClient("tcp://192.168.1.50:10700")

        assert client.uri == "tcp://192.168.1.50:10700"
        assert client.host == "192.168.1.50"
        assert client.port == 10700
        assert not client.connected

    def test_init_invalid_scheme(self):
        """Test client initialization with invalid scheme."""
        with pytest.raises(ValueError, match="Unsupported URI scheme"):
            WyomingClient("http://example.com:8080")

    def test_init_invalid_uri(self):
        """Test client initialization with invalid URI."""
        with pytest.raises(ValueError, match="Invalid URI format"):
            WyomingClient("tcp://invalid")

    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class):
        """Test successful connection."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = WyomingClient("tcp://192.168.1.50:10700")
        client.connect()

        assert client.connected
        mock_socket.connect.assert_called_with(("192.168.1.50", 10700))

    @patch('socket.socket')
    def test_connect_failure(self, mock_socket_class):
        """Test connection failure."""
        mock_socket = Mock()
        mock_socket.connect.side_effect = ConnectionError("Connection refused")
        mock_socket_class.return_value = mock_socket

        client = WyomingClient("tcp://192.168.1.50:10700")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            client.connect()

        assert not client.connected

    @patch('socket.socket')
    def test_context_manager(self, mock_socket_class):
        """Test context manager usage."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = WyomingClient("tcp://192.168.1.50:10700")

        with client:
            assert client.connected

        assert not client.connected
        mock_socket.close.assert_called_once()

    def test_send_event_not_connected(self):
        """Test sending event when not connected."""
        from wyoming.pipeline import RunPipeline, PipelineStage

        client = WyomingClient("tcp://192.168.1.50:10700")
        event = RunPipeline(
            start_stage=PipelineStage.ASR,
            end_stage=PipelineStage.TTS
        )

        with pytest.raises(ConnectionError, match="Not connected"):
            client.send_event(event)