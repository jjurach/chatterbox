"""Unit tests for ha_emulator.corpus."""

import json
import wave
import struct
from pathlib import Path

import pytest

from ha_emulator.corpus import CorpusEntry, CorpusLoader


def _make_wav(path: Path, duration_frames: int = 160) -> None:
    """Write a minimal valid WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * duration_frames)


@pytest.fixture()
def corpus_dir(tmp_path):
    """Minimal corpus with two entries."""
    wav1 = tmp_path / "test_001_lights.wav"
    wav2 = tmp_path / "test_002_weather.wav"
    _make_wav(wav1)
    _make_wav(wav2)

    manifest = [
        {"file": "test_001_lights.wav", "expected": "turn on the lights", "description": "lights"},
        {"file": "test_002_weather.wav", "expected": "what is the weather", "description": "weather"},
    ]
    (tmp_path / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


class TestCorpusLoader:
    def test_load_all_returns_correct_entries(self, corpus_dir):
        loader = CorpusLoader(corpus_dir)
        entries = loader.load_all()

        assert len(entries) == 2
        assert entries[0].expected_text == "turn on the lights"
        assert entries[1].expected_text == "what is the weather"

    def test_load_all_sorted_by_filename(self, corpus_dir):
        loader = CorpusLoader(corpus_dir)
        entries = loader.load_all()
        names = [e.wav_path.name for e in entries]
        assert names == sorted(names)

    def test_load_entry_by_stem(self, corpus_dir):
        loader = CorpusLoader(corpus_dir)
        entry = loader.load_entry("test_001_lights")
        assert entry.expected_text == "turn on the lights"

    def test_load_entry_missing_raises(self, corpus_dir):
        loader = CorpusLoader(corpus_dir)
        with pytest.raises(FileNotFoundError):
            loader.load_entry("nonexistent")

    def test_missing_corpus_dir_raises(self, tmp_path):
        loader = CorpusLoader(tmp_path / "does_not_exist")
        with pytest.raises(FileNotFoundError, match="Corpus directory"):
            loader.load_all()

    def test_missing_manifest_raises(self, tmp_path):
        loader = CorpusLoader(tmp_path)
        with pytest.raises(FileNotFoundError, match="manifest"):
            loader.load_all()

    def test_malformed_manifest_raises(self, tmp_path):
        (tmp_path / "corpus.json").write_text("not valid json", encoding="utf-8")
        loader = CorpusLoader(tmp_path)
        with pytest.raises(ValueError, match="Malformed"):
            loader.load_all()

    def test_missing_wav_file_is_skipped(self, tmp_path):
        manifest = [
            {"file": "missing.wav", "expected": "hello", "description": ""},
        ]
        (tmp_path / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
        loader = CorpusLoader(tmp_path)
        entries = loader.load_all()
        assert entries == []

    def test_entry_has_correct_description(self, corpus_dir):
        loader = CorpusLoader(corpus_dir)
        entry = loader.load_entry("test_001_lights")
        assert entry.description == "lights"
