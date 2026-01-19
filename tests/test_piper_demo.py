"""Tests for piper_demo.py functionality."""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Add the scripts directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from piper_demo import PiperDemo


class TestPiperDemo:
    """Test cases for PiperDemo class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.model_path = "/fake/model.onnx"
        self.config_path = "/fake/config.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            self.cache_dir = temp_dir
            self.demo = PiperDemo(self.model_path, self.config_path, self.cache_dir)

    def test_initialization(self):
        """Test PiperDemo initialization."""
        assert self.demo.model_path == self.model_path
        assert self.demo.config_path == self.config_path
        assert self.demo.cache_dir == self.cache_dir
        assert self.demo.tts_service is None
        assert self.demo.stats['total_operations'] == 0

    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        text = "Hello world"
        key1 = self.demo._get_cache_key(text)
        key2 = self.demo._get_cache_key(text)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
        assert key1 != self.demo._get_cache_key("Hello world!")  # Different text

    def test_cache_paths(self):
        """Test cache path generation."""
        cache_key = "test_key_123"
        cache_path = self.demo._get_cache_path(cache_key)
        metadata_path = self.demo._get_metadata_path(cache_key)

        assert cache_path.endswith(f"{cache_key}.wav")
        assert metadata_path.endswith(f"{cache_key}.json")
        assert self.cache_dir in cache_path

    def test_get_summary_empty(self):
        """Test summary with no operations."""
        summary = self.demo.get_summary()

        assert summary['total_operations'] == 0
        assert summary['cache_hits'] == 0
        assert summary['cache_misses'] == 0
        assert summary['cache_hit_rate_percent'] == 0.0

    def test_get_summary_with_operations(self):
        """Test summary with mock operations."""
        self.demo.stats['total_operations'] = 10
        self.demo.stats['cache_hits'] = 7
        self.demo.stats['cache_misses'] = 3
        self.demo.stats['total_synthesis_time'] = 1.5
        self.demo.stats['total_cached_time'] = 0.1

        summary = self.demo.get_summary()

        assert summary['total_operations'] == 10
        assert summary['cache_hits'] == 7
        assert summary['cache_misses'] == 3
        assert summary['cache_hit_rate_percent'] == 70.0
        assert summary['average_synthesis_time_seconds'] == 0.5  # 1.5 / 3
        assert summary['average_cached_time_seconds'] == pytest.approx(0.014, rel=1e-2)  # 0.1 / 7

    @pytest.mark.asyncio
    async def test_synthesize_with_cache_miss(self):
        """Test synthesis with cache miss."""
        # Mock TTS service
        from unittest.mock import AsyncMock
        mock_service = AsyncMock()
        self.demo.tts_service = mock_service

        # Mock file operations
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.dump'), \
             patch.object(self.demo, '_get_audio_info', return_value={
                 'duration_seconds': 2.5,
                 'file_size_bytes': 44100,
                 'sample_rate': 22050
             }):

            result = await self.demo.synthesize_with_cache("Test text")

            assert result['success'] is True
            assert result['cache_hit'] is False
            assert 'output_path' in result
            assert result['processing_time_seconds'] >= 0
            assert result['audio_info']['duration_seconds'] == 2.5

            # Verify stats were updated
            assert self.demo.stats['total_operations'] == 1
            assert self.demo.stats['cache_misses'] == 1
            assert self.demo.stats['cache_hits'] == 0

    @pytest.mark.asyncio
    async def test_synthesize_with_cache_hit(self):
        """Test synthesis with cache hit."""
        # Mock TTS service
        self.demo.tts_service = MagicMock()

        # Mock file operations for cache hit
        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2'), \
             patch('builtins.open', create=True), \
             patch('json.load', return_value={'text': 'Test text'}), \
             patch.object(self.demo, '_get_audio_info', return_value={
                 'duration_seconds': 2.5,
                 'file_size_bytes': 44100,
                 'sample_rate': 22050
             }):

            result = await self.demo.synthesize_with_cache("Test text")

            assert result['success'] is True
            assert result['cache_hit'] is True
            assert result['processing_time_seconds'] >= 0

            # Verify stats were updated
            assert self.demo.stats['total_operations'] == 1
            assert self.demo.stats['cache_hits'] == 1
            assert self.demo.stats['cache_misses'] == 0