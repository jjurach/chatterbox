"""Text-to-Speech tool for LangChain agents."""

from langchain.tools import BaseTool
from typing import Optional
import os

from cackle.services import PiperTTSService


class TTSTool(BaseTool):
    """Tool for synthesizing text to speech using Piper."""

    name = "synthesize_speech"
    description = (
        "Synthesize text to speech using Piper TTS. "
        "Input: text to synthesize. "
        "Output: path to generated WAV file."
    )
    return_direct = False

    tts_service: Optional[PiperTTSService] = None

    def _initialize_service(self) -> None:
        """Initialize the TTS service if not already done."""
        if self.tts_service is None:
            self.tts_service = PiperTTSService()

    def _run(self, text: str, output_path: Optional[str] = None) -> str:
        """Synthesize text to speech (sync wrapper).

        Args:
            text: Text to synthesize
            output_path: Optional path to save audio file

        Returns:
            Path to generated audio file or status message
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(text, output_path))

    async def _arun(
        self, text: str, output_path: Optional[str] = None
    ) -> str:
        """Synthesize text to speech asynchronously.

        Args:
            text: Text to synthesize
            output_path: Optional path to save audio file. If None, uses temp file.

        Returns:
            Path to generated audio file
        """
        self._initialize_service()

        try:
            # Generate default output path if not provided
            if output_path is None:
                import tempfile

                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, "synthesized_speech.wav")

            await self.tts_service.synthesize_to_file(text, output_path)
            return f"Speech synthesized successfully. Saved to: {output_path}"

        except Exception as e:
            return f"Error synthesizing speech: {str(e)}"
