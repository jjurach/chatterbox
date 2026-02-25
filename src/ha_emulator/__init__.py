"""Home Assistant Emulator — Wyoming protocol test harness.

Drives Chatterbox Wyoming services the same way Home Assistant would in
production, enabling repeatable validation of STT, TTS, and end-to-end
conversation flows without a live Home Assistant instance.
"""

from .corpus import CorpusEntry, CorpusLoader
from .emulator import FullResult, HAEmulator, PTTResult, STTResult, TTSResult
from .runner import EntryReport, TestReport, TestRunner
from .validator import ResultValidator, ValidationResult

__all__ = [
    "HAEmulator",
    "STTResult",
    "TTSResult",
    "FullResult",
    "PTTResult",
    "CorpusLoader",
    "CorpusEntry",
    "ResultValidator",
    "ValidationResult",
    "TestRunner",
    "TestReport",
    "EntryReport",
]
