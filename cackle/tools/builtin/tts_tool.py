"""Text-to-Speech tool for LangChain agents."""

from langchain.tools import BaseTool
from typing import Optional
import os

from cackle.services import PiperTTSService


class TTSTool(BaseTool):
    """Tool for synthesizing text to speech using Piper."""

    name: str = "synthesize_speech"
    description: str = (
        "Synthesize text to speech using Piper TTS. "
        "Input: text to synthesize. "
        "Output: confirmation that speech was synthesized."
    )
    return_direct: bool = False

    tts_service: Optional[PiperTTSService] = None

    def __init__(self, *args, **kwargs):
        """Initialization method."""
        kwargs['name'] = "synthesize_speech"
        kwargs['description'] = (
            "Synthesize text to speech using Piper TTS. "
            "Input: text to synthesize. "
            "Output: confirmation that speech was synthesized."
        )
        kwargs['func'] = self._run
        super().__init__(*args, **kwargs)

    def _initialize_service(self) -> None:
        """Initialize the TTS service if not already done."""
        if self.tts_service is None:
            self.tts_service = PiperTTSService()

    def _run(self, text: str) -> str:
        """Synthesize text to speech (sync wrapper).

        Args:
            text: Text to synthesize

        Returns:
            Status message
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(text))

    async def _arun(self, text: str) -> str:
        """Synthesize text to speech asynchronously.

        Args:
            text: Text to synthesize

        Returns:
            Status message
        """
        self._initialize_service()

        try:
            # Generate default output path
            import tempfile

            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"synthesized_speech_{hash(text)}.wav")

            await self.tts_service.synthesize_to_file(text, output_path)
            return f"Speech synthesized successfully for text: '{text[:50]}...'"

        except Exception as e:
            return f"Error synthesizing speech: {str(e)}"