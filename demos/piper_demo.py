#!/usr/bin/env python3
"""
Piper TTS Demo Script with Caching and Summarization

This script provides a standalone Piper TTS demonstration with intelligent caching
and detailed operation summarization. It can be used independently or integrated
with chat-demo.sh for TTS-only testing.

Features:
- Piper TTS synthesis with configurable models
- File-based caching with hash-based keys
- Operation summarization (timing, file sizes, cache statistics)
- Command-line interface for easy integration
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import wave

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatterbox.services.tts import PiperTTSService


class PiperDemo:
    """Piper TTS Demo with caching and summarization capabilities."""

    def __init__(self, model_path: str, config_path: str, cache_dir: Optional[str] = None):
        """Initialize Piper demo.

        Args:
            model_path: Path to Piper ONNX model file
            config_path: Path to Piper config JSON file
            cache_dir: Directory for caching synthesized audio (optional)
        """
        self.model_path = model_path
        self.config_path = config_path
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', 'tmp', 'piper_cache')
        self.tts_service: Optional[PiperTTSService] = None
        self.stats = {
            'total_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_synthesis_time': 0.0,
            'total_cached_time': 0.0,
            'operations': []
        }

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize the TTS service."""
        if self.tts_service is None:
            self.tts_service = PiperTTSService(
                model_path=self.model_path,
                config_path=self.config_path
            )
            await self.tts_service.load_voice()

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text and model paths."""
        # Create hash from text and model paths for uniqueness
        content = f"{text}|{self.model_path}|{self.config_path}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get full path for cached audio file."""
        return os.path.join(self.cache_dir, f"{cache_key}.wav")

    def _get_metadata_path(self, cache_key: str) -> str:
        """Get full path for cached metadata file."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _is_cached(self, cache_key: str) -> bool:
        """Check if audio is cached."""
        return os.path.exists(self._get_cache_path(cache_key))

    def _save_metadata(self, cache_key: str, metadata: Dict) -> None:
        """Save metadata for cached audio."""
        metadata_path = self._get_metadata_path(cache_key)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, cache_key: str) -> Optional[Dict]:
        """Load metadata for cached audio."""
        metadata_path = self._get_metadata_path(cache_key)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None

    def _get_audio_info(self, file_path: str) -> Dict:
        """Get audio file information."""
        try:
            with wave.open(file_path, 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
                file_size = os.path.getsize(file_path)
                return {
                    'duration_seconds': duration,
                    'file_size_bytes': file_size,
                    'sample_rate': wf.getframerate(),
                    'channels': wf.getnchannels(),
                    'sample_width': wf.getsampwidth()
                }
        except Exception as e:
            return {'error': str(e)}

    async def synthesize_with_cache(
        self,
        text: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """Synthesize text to speech with caching.

        Args:
            text: Text to synthesize
            output_path: Optional output path (if not provided, uses cache)

        Returns:
            Dictionary with operation results and metadata
        """
        await self.initialize()

        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)

        operation_start = time.time()
        cache_hit = self._is_cached(cache_key)

        if cache_hit:
            # Use cached audio
            self.stats['cache_hits'] += 1
            cached_time = time.time() - operation_start
            self.stats['total_cached_time'] += cached_time

            # Copy cached file to output if requested
            if output_path and output_path != cache_path:
                import shutil
                shutil.copy2(cache_path, output_path)
                final_path = output_path
            else:
                final_path = cache_path

            # Load metadata
            metadata = self._load_metadata(cache_key) or {}
            audio_info = self._get_audio_info(final_path)

        else:
            # Synthesize new audio
            self.stats['cache_misses'] += 1

            # Generate audio
            synthesis_start = time.time()
            if output_path:
                await self.tts_service.synthesize_to_file(text, output_path)
                final_path = output_path
            else:
                await self.tts_service.synthesize_to_file(text, cache_path)
                final_path = cache_path

            synthesis_time = time.time() - synthesis_start
            self.stats['total_synthesis_time'] += synthesis_time

            # Get audio information
            audio_info = self._get_audio_info(final_path)

            # Create metadata
            metadata = {
                'text': text,
                'model_path': self.model_path,
                'config_path': self.config_path,
                'synthesis_time_seconds': synthesis_time,
                'created_at': time.time(),
                'cache_key': cache_key
            }

            # Save metadata for cached files
            if not output_path:
                self._save_metadata(cache_key, metadata)

        total_time = time.time() - operation_start
        self.stats['total_operations'] += 1

        # Record operation
        operation = {
            'text': text[:50] + '...' if len(text) > 50 else text,
            'cache_hit': cache_hit,
            'total_time_seconds': total_time,
            'audio_info': audio_info,
            'output_path': final_path,
            'timestamp': time.time()
        }
        self.stats['operations'].append(operation)

        return {
            'success': True,
            'cache_hit': cache_hit,
            'output_path': final_path,
            'audio_info': audio_info,
            'processing_time_seconds': total_time,
            'metadata': metadata
        }

    def get_summary(self) -> Dict:
        """Get summarization statistics."""
        total_operations = self.stats['total_operations']
        cache_hits = self.stats['cache_hits']
        cache_misses = self.stats['cache_misses']

        cache_hit_rate = (cache_hits / total_operations * 100) if total_operations > 0 else 0
        avg_synthesis_time = (self.stats['total_synthesis_time'] / cache_misses) if cache_misses > 0 else 0
        avg_cached_time = (self.stats['total_cached_time'] / cache_hits) if cache_hits > 0 else 0

        return {
            'total_operations': total_operations,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'average_synthesis_time_seconds': round(avg_synthesis_time, 3),
            'average_cached_time_seconds': round(avg_cached_time, 3),
            'total_synthesis_time_seconds': round(self.stats['total_synthesis_time'], 3),
            'total_cached_time_seconds': round(self.stats['total_cached_time'], 3)
        }

    def print_summary(self) -> None:
        """Print human-readable summary."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("PIPER TTS DEMO SUMMARY")
        print("="*60)
        print(f"Total Operations:     {summary['total_operations']}")
        print(f"Cache Hits:          {summary['cache_hits']}")
        print(f"Cache Misses:        {summary['cache_misses']}")
        print(f"Cache Hit Rate:      {summary['cache_hit_rate_percent']}%")
        print(f"Avg Synthesis Time:  {summary['average_synthesis_time_seconds']}s")
        print(f"Avg Cached Time:     {summary['average_cached_time_seconds']}s")
        print(f"Total Synthesis Time: {summary['total_synthesis_time_seconds']}s")
        print(f"Total Cached Time:    {summary['total_cached_time_seconds']}s")
        print("="*60)

        if self.stats['operations']:
            print("\nRecent Operations:")
            print("-" * 40)
            for i, op in enumerate(self.stats['operations'][-5:]):  # Show last 5
                status = "CACHE" if op['cache_hit'] else "NEW"
                print(f"{i+1}. [{status}] {op['text']} ({op['total_time_seconds']:.3f}s)")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Piper TTS Demo with Caching")
    parser.add_argument(
        'text',
        help='Text to synthesize'
    )
    parser.add_argument(
        '--model-path',
        required=True,
        help='Path to Piper ONNX model file'
    )
    parser.add_argument(
        '--config-path',
        required=True,
        help='Path to Piper config JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output audio file path (optional, uses cache if not specified)'
    )
    parser.add_argument(
        '--cache-dir',
        help='Cache directory path'
    )
    parser.add_argument(
        '--summary-only', '-s',
        action='store_true',
        help='Only print summary, no synthesis'
    )

    args = parser.parse_args()

    # Initialize demo
    demo = PiperDemo(
        model_path=args.model_path,
        config_path=args.config_path,
        cache_dir=args.cache_dir
    )

    if args.summary_only:
        demo.print_summary()
        return

    # Perform synthesis
    try:
        result = await demo.synthesize_with_cache(args.text, args.output)

        if result['success']:
            print(f"✓ Synthesis completed successfully")
            print(f"  Output: {result['output_path']}")
            print(f"  Cache Hit: {result['cache_hit']}")
            print(f"  Processing Time: {result['processing_time_seconds']:.3f}s")

            if 'audio_info' in result and 'duration_seconds' in result['audio_info']:
                info = result['audio_info']
                print(f"  Duration: {info['duration_seconds']:.2f}s")
                print(f"  File Size: {info['file_size_bytes']} bytes")
                print(f"  Sample Rate: {info['sample_rate']} Hz")
        else:
            print("✗ Synthesis failed")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

    # Print summary
    demo.print_summary()


if __name__ == "__main__":
    asyncio.run(main())