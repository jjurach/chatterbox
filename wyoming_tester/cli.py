#!/usr/bin/env python3
"""Command-line interface for Wyoming Satellite Emulator."""

import argparse
import logging
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Wyoming Satellite Emulator for Push-to-Talk Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wyoming-tester --uri tcp://192.168.1.50:10700 --file hello.wav
  wyoming-tester -u tcp://ha.local:10700 -f question.wav --verbose
  wyoming-tester -u tcp://ha.local:10700 -f follow_up.wav --context abc123
        """
    )

    parser.add_argument(
        "--uri", "-u",
        required=True,
        help="Wyoming endpoint URI (e.g., tcp://192.168.1.50:10700)"
    )

    parser.add_argument(
        "--file", "-f",
        required=True,
        type=Path,
        help="Path to input WAV audio file"
    )

    parser.add_argument(
        "--context", "-c",
        help="Conversation ID for multi-turn testing"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose event logging"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("response.wav"),
        help="Output filename for TTS response (default: response.wav)"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )

    logger = logging.getLogger(__name__)

    # Validate input file exists
    if not args.file.exists():
        logger.error(f"Input file does not exist: {args.file}")
        sys.exit(1)

    # Implement PTT workflow
    from .protocol import WyomingClient
    from .audio import AudioProcessor

    try:
        from wyoming.audio import AudioChunk, AudioStart, AudioStop
        from wyoming.pipeline import RunPipeline, PipelineStage
        from wyoming.asr import Transcript, Transcribe
        from wyoming.tts import Synthesize
    except ImportError as e:
        logger.error(f"Missing required Wyoming library: {e}")
        sys.exit(1)

    try:
        # Initialize components
        client = WyomingClient(args.uri)
        processor = AudioProcessor()

        # Load and convert audio
        logger.info(f"Loading audio file: {args.file}")
        audio = processor.load_and_convert(args.file)

        # Validate format
        if not processor.validate_wyoming_format(audio):
            raise ValueError("Audio conversion failed - format doesn't meet Wyoming requirements")

        logger.info("Wyoming tester starting PTT workflow...")
        logger.info(f"URI: {args.uri}")
        logger.info(f"Input file: {args.file}")
        logger.info(f"Output file: {args.output}")

        if args.context:
            logger.info(f"Conversation context: {args.context}")

        # Connect and run STT workflow
        with client:
            # Send Transcribe event with audio data
            transcribe_event = Transcribe()
            client.send_event(transcribe_event)
            logger.info("Sent transcribe event")

            # Send AudioStart event
            audio_start_event = AudioStart(
                rate=16000,
                width=2,
                channels=1
            )
            client.send_event(audio_start_event)
            logger.info("Sent audio-start event")

            # Send audio chunks
            logger.info("Sending audio data...")
            for chunk in processor.get_pcm_chunks(audio):
                audio_chunk_event = AudioChunk(
                    rate=16000,
                    width=2,
                    channels=1,
                    audio=chunk
                )
                client.send_event(audio_chunk_event)

            # Send AudioStop event
            audio_stop_event = AudioStop()
            client.send_event(audio_stop_event)
            logger.info("Sent audio-stop event")

            # Listen for responses
            logger.info("Waiting for responses...")
            tts_chunks = []
            response_text = ""
            conversation_id = None

            while True:
                event = client.receive_event(timeout=10.0)
                if event is None:
                    break

                if isinstance(event, Transcript):
                    # STT results
                    transcription = event.text
                    confidence = getattr(event, 'confidence', 0.0)

                    print("🎤 Transcription:", transcription)
                    if confidence > 0:
                        print(f"🎯 Confidence: {confidence:.2f}")
                    if hasattr(event, 'conversation_id') and event.conversation_id:
                        print("💬 Conversation ID:", event.conversation_id)

                elif isinstance(event, Synthesize):
                    # LLM response text
                    response_text += event.text

                elif isinstance(event, AudioStart):
                    # TTS audio start
                    logger.info("Receiving TTS audio...")

                elif isinstance(event, AudioChunk):
                    # TTS audio chunks
                    tts_chunks.append(event.audio)

                elif isinstance(event, AudioStop):
                    # TTS audio end
                    logger.info("TTS audio transmission complete")

                    # Save TTS response
                    if tts_chunks:
                        tts_audio = processor.reconstruct_from_chunks(tts_chunks)
                        processor.save_wav(tts_audio, args.output)
                        print(f"🔊 TTS audio saved to: {args.output}")
                    else:
                        logger.warning("No TTS audio chunks received")

                    break

                else:
                    # Handle other event types
                    logger.debug(f"Unhandled event type: {type(event).__name__}")

            # Print final response
            if response_text:
                print("💬 Response:", response_text.strip())

        logger.info("PTT workflow completed successfully")

    except Exception as e:
        logger.error(f"PTT workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()