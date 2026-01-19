"""Speech-to-Text tool for LangChain agents."""

from langchain.tools import BaseTool
from typing import Optional

from cackle.services import WhisperSTTService


class STTTool(BaseTool):
    """Tool for transcribing audio to text using Whisper."""

    name: str = "transcribe_audio"
    description: str = (
        "Transcribe audio file to text using Whisper. "
        "Input: path to audio file (WAV, MP3, FLAC). "
        "Output: transcribed text and confidence score."
    )
    return_direct: bool = False

    stt_service: Optional[WhisperSTTService] = None

    def __init__(self, *args, **kwargs):
        """Initialization method."""
        kwargs['name'] = "transcribe_audio"
        kwargs['description'] = (
            "Transcribe audio file to text using Whisper. "
            "Input: path to audio file (WAV, MP3, FLAC). "
            "Output: transcribed text and confidence score."
        )
        kwargs['func'] = self._run
        super().__init__(*args, **kwargs)

    def _initialize_service(self) -> None:
        """Initialize the STT service if not already done."""
        if self.stt_service is None:
            self.stt_service = WhisperSTTService()

    def _run(self, file_path: str) -> str:
        """Transcribe audio file (sync wrapper).

        Args:
            file_path: Path to audio file

        Returns:
            Transcription result as string
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(file_path))

    async def _arun(self, file_path: str) -> str:
        """Transcribe audio file asynchronously.

        Args:
            file_path: Path to audio file

        Returns:
            Transcription result as string
        """
        self._initialize_service()

        try:
            result = await self.stt_service.transcribe_file(file_path)
            return (
                f"Transcription: {result['text']}\n"
                f"Language: {result.get('language', 'unknown')}\n"
                f"Confidence: {result.get('confidence', 0.0):.2f}"
            )
        except Exception as e:
            return f"Error transcribing audio: {str(e)}"