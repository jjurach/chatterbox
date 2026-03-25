"""STT, TTS, and logging services for Chatterbox.

Available services:
- WhisperSTTService: Speech-to-text using Whisper models
- PiperTTSService: Text-to-speech using Piper models
- SerialLogCapture: Device log capture from ESP32 via serial connection
"""

from .serial_log_capture import LogEntry, LogFileRotator, SerialLogCapture
from .stt import WhisperSTTService
from .tts import PiperTTSService

__all__ = [
    "WhisperSTTService",
    "PiperTTSService",
    "SerialLogCapture",
    "LogEntry",
    "LogFileRotator",
]
