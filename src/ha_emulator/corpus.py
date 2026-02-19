"""Corpus loader — reads test wave files and expected transcriptions."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class CorpusEntry:
    """A single test corpus entry."""

    wav_path: Path
    expected_text: str
    description: str


class CorpusLoader:
    """Loads wave files and expected transcriptions from a corpus directory.

    The corpus directory must contain a ``corpus.json`` file with the
    following format::

        [
          {
            "file": "test_001_turn_on_lights.wav",
            "expected": "turn on the lights",
            "description": "Simple home control command"
          },
          ...
        ]
    """

    MANIFEST_NAME = "corpus.json"

    def __init__(self, corpus_dir: Path) -> None:
        self.corpus_dir = Path(corpus_dir)
        self._manifest_path = self.corpus_dir / self.MANIFEST_NAME

    def load_all(self) -> List[CorpusEntry]:
        """Return all corpus entries sorted by filename.

        Raises:
            FileNotFoundError: If the corpus directory or manifest is missing.
            ValueError: If the manifest JSON is malformed.
        """
        if not self.corpus_dir.is_dir():
            raise FileNotFoundError(f"Corpus directory not found: {self.corpus_dir}")
        if not self._manifest_path.exists():
            raise FileNotFoundError(f"Corpus manifest not found: {self._manifest_path}")

        try:
            raw = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed corpus manifest: {self._manifest_path}: {exc}") from exc

        entries: List[CorpusEntry] = []
        for item in raw:
            wav_path = self.corpus_dir / item["file"]
            if not wav_path.exists():
                logger.warning("Corpus file missing, skipping: %s", wav_path)
                continue
            entries.append(
                CorpusEntry(
                    wav_path=wav_path,
                    expected_text=item["expected"],
                    description=item.get("description", ""),
                )
            )

        entries.sort(key=lambda e: e.wav_path.name)
        logger.info("Loaded %d corpus entries from %s", len(entries), self.corpus_dir)
        return entries

    def load_entry(self, name: str) -> CorpusEntry:
        """Load a single entry by filename stem (e.g. ``test_001_turn_on_lights``).

        Raises:
            FileNotFoundError: If no matching entry exists.
        """
        for entry in self.load_all():
            if entry.wav_path.stem == name:
                return entry
        raise FileNotFoundError(f"Corpus entry not found: {name}")
