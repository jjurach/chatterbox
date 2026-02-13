#!/usr/bin/env python3
"""
OCR Validation Tool for Chatterbox Devices

Validates device state by reading the display via /dev/video0 and using OCR
to recognize the displayed letter. Just needs a camera - no network connection needed!

Usage:
    # Validate device display once (no args needed!)
    python ocr_validate.py

    # Run continuous validation loop
    python ocr_validate.py --loop --interval 5

    # Generate validation report
    python ocr_validate.py --loop --duration 60 --report report.json

    # Optionally name the device for logging
    python ocr_validate.py --device "Box3B-Dev" --loop

    # Validate multiple devices with batch file
    python ocr_validate.py --batch devices.json --duration 120
"""

import argparse
import cv2
import json
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import easyocr
except ImportError:
    print("Error: easyocr library not found. Install with: pip install easyocr opencv-python")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Valid device states corresponding to display letters."""
    UNINITIALIZED = 'N'  # Orange
    IDLE = 'H'            # Purple
    LISTENING = 'S'       # Blue
    THINKING = 'A'        # Red
    REPLYING = 'W'        # Yellow
    ERROR = 'P'           # Green

    @classmethod
    def from_letter(cls, letter: str) -> Optional['DeviceState']:
        """Get state from letter."""
        for state in cls:
            if state.value == letter.upper():
                return state
        return None

    @property
    def color(self) -> str:
        """Get color name for state."""
        color_map = {
            'N': 'Orange',
            'H': 'Purple',
            'S': 'Blue',
            'A': 'Red',
            'W': 'Yellow',
            'P': 'Green'
        }
        return color_map.get(self.value, 'Unknown')


@dataclass
class ValidationResult:
    """Result of a single validation attempt."""
    timestamp: str
    device: str
    detected_letter: Optional[str]
    expected_letter: Optional[str]
    confidence: float
    state: Optional[str]
    success: bool
    error: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        """String representation."""
        if self.error:
            return f"[{self.timestamp}] {self.device}: ERROR - {self.error}"

        status = "✅" if self.success else "❌"
        if self.expected_letter:
            return (f"{status} [{self.timestamp}] {self.device}: "
                    f"Expected {self.expected_letter}, Got {self.detected_letter} "
                    f"({self.confidence:.1%} confidence)")
        else:
            return (f"ℹ️  [{self.timestamp}] {self.device}: "
                    f"Detected {self.detected_letter} ({self.confidence:.1%} confidence)")


class OCRValidator:
    """Validates device state using OCR on video feed."""

    # OCR Settings
    OCR_CONFIDENCE_THRESHOLD = 0.3
    VALID_LETTERS = [state.value for state in DeviceState]

    # Image processing settings
    IMAGE_WIDTH = 320
    IMAGE_HEIGHT = 240

    def __init__(self, video_device: str = "/dev/video0", use_gpu: bool = False):
        """
        Initialize OCR validator.

        Args:
            video_device: Path to video device (default: /dev/video0)
            use_gpu: Whether to use GPU acceleration (default: False)

        Raises:
            OCRValidationError: If OCR initialization fails
        """
        self.video_device = video_device
        self.use_gpu = use_gpu
        self.results = []

        try:
            logger.info("Initializing EasyOCR reader...")
            self.reader = easyocr.Reader(
                ['en'],
                gpu=use_gpu,
                verbose=False
            )
            logger.info("✅ EasyOCR initialized successfully")
        except Exception as e:
            raise OCRValidationError(f"Failed to initialize OCR: {e}")

    def _open_video_feed(self) -> Optional[cv2.VideoCapture]:
        """Open video device for reading frames."""
        try:
            cap = cv2.VideoCapture(self.video_device)
            if not cap.isOpened():
                logger.error(f"Failed to open video device: {self.video_device}")
                return None

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.IMAGE_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.IMAGE_HEIGHT)

            logger.info(f"✅ Opened video device: {self.video_device}")
            return cap

        except Exception as e:
            logger.error(f"Error opening video device: {e}")
            return None

    def _preprocess_frame(self, frame: cv2.Mat) -> cv2.Mat:
        """Preprocess frame for better OCR accuracy."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

        return filtered

    def _extract_letter(self, frame: cv2.Mat) -> Tuple[Optional[str], float]:
        """
        Extract and recognize letter from frame using OCR.

        Args:
            frame: Video frame

        Returns:
            Tuple of (detected_letter, confidence_score)
        """
        try:
            # Preprocess frame
            processed = self._preprocess_frame(frame)

            # Run OCR
            results = self.reader.readtext(processed, detail=1)

            if not results:
                logger.debug("No text detected in frame")
                return None, 0.0

            # Extract letters with confidence > threshold
            valid_detections = [
                (text.upper(), confidence)
                for bbox, text, confidence in results
                if confidence > self.OCR_CONFIDENCE_THRESHOLD
            ]

            if not valid_detections:
                logger.debug("No valid OCR detections above confidence threshold")
                return None, 0.0

            # Find single-letter detections
            single_letters = [
                (text, conf)
                for text, conf in valid_detections
                if len(text) == 1 and text in self.VALID_LETTERS
            ]

            if single_letters:
                # Use highest confidence detection
                letter, confidence = max(single_letters, key=lambda x: x[1])
                logger.debug(f"Detected letter: {letter} (confidence: {confidence:.1%})")
                return letter, confidence

            # If no single letters found, check for any valid letter in text
            for text, conf in valid_detections:
                for char in text:
                    if char in self.VALID_LETTERS:
                        logger.debug(f"Detected letter in text: {char} (confidence: {conf:.1%})")
                        return char, conf

            logger.debug(f"No valid letters found. Detections: {valid_detections}")
            return None, 0.0

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None, 0.0

    def validate_device_display(self, samples: int = 5) -> Tuple[Optional[str], float]:
        """
        Validate device display by sampling multiple frames.

        Args:
            samples: Number of frames to sample (default: 5)

        Returns:
            Tuple of (detected_letter, average_confidence)
        """
        cap = self._open_video_feed()
        if not cap:
            return None, 0.0

        try:
            detections = []

            for i in range(samples):
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Failed to read frame {i}")
                    continue

                letter, confidence = self._extract_letter(frame)
                if letter:
                    detections.append((letter, confidence))

                # Small delay between frames
                time.sleep(0.1)

            cap.release()

            if not detections:
                logger.warning("No letters detected in any frame")
                return None, 0.0

            # Return most common letter and average confidence
            letter_counts = defaultdict(list)
            for letter, conf in detections:
                letter_counts[letter].append(conf)

            most_common_letter = max(
                letter_counts.keys(),
                key=lambda x: len(letter_counts[x])
            )
            avg_confidence = sum(letter_counts[most_common_letter]) / len(letter_counts[most_common_letter])

            logger.info(f"Validation complete: {most_common_letter} ({avg_confidence:.1%} confidence)")
            return most_common_letter, avg_confidence

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return None, 0.0
        finally:
            cap.release()

    def validate_state(self, device: str, expected_state: Optional[str] = None) -> ValidationResult:
        """
        Validate device state via OCR.

        Args:
            device: Device identifier (for logging)
            expected_state: Expected state letter (optional)

        Returns:
            ValidationResult with detected state and confidence
        """
        timestamp = datetime.now().isoformat()

        try:
            detected_letter, confidence = self.validate_device_display()

            if not detected_letter:
                result = ValidationResult(
                    timestamp=timestamp,
                    device=device,
                    detected_letter=None,
                    expected_letter=expected_state,
                    confidence=0.0,
                    state=None,
                    success=False,
                    error="No letter detected in video feed"
                )
                self.results.append(result)
                return result

            # Get state from detected letter
            state = DeviceState.from_letter(detected_letter)
            success = (detected_letter == expected_state) if expected_state else True

            result = ValidationResult(
                timestamp=timestamp,
                device=device,
                detected_letter=detected_letter,
                expected_letter=expected_state,
                confidence=confidence,
                state=state.name if state else None,
                success=success,
                error=None
            )

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                timestamp=timestamp,
                device=device,
                detected_letter=None,
                expected_letter=expected_state,
                confidence=0.0,
                state=None,
                success=False,
                error=str(e)
            )
            self.results.append(result)
            return result

    def validate_loop(self, device: str, interval: int = 5,
                     duration: Optional[int] = None) -> List[ValidationResult]:
        """
        Run continuous validation loop.

        Args:
            device: Device identifier
            interval: Seconds between validations (default: 5)
            duration: Total duration in seconds (None = infinite)

        Returns:
            List of validation results
        """
        logger.info(f"Starting validation loop for {device}")
        logger.info(f"Interval: {interval}s, Duration: {duration}s" if duration else f"Interval: {interval}s, Duration: infinite")

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration) if duration else None
        iteration = 0

        print(f"\n{'='*60}")
        print(f"🔄 Starting OCR Validation Loop")
        print(f"Device: {device}")
        print(f"Interval: {interval}s")
        if end_time:
            print(f"Duration: {duration}s")
        print(f"{'='*60}\n")

        try:
            while True:
                iteration += 1

                # Check if we've exceeded duration
                if end_time and datetime.now() >= end_time:
                    logger.info("Duration limit reached, stopping validation loop")
                    break

                print(f"[Iteration {iteration}]")
                result = self.validate_state(device)
                print(result)

                # Wait for next iteration
                remaining = (end_time - datetime.now()).total_seconds() if end_time else interval
                if remaining > 0:
                    time.sleep(min(interval, remaining))
                else:
                    break

        except KeyboardInterrupt:
            logger.info("Validation loop interrupted by user")
            print("\n⚠️  Validation loop stopped by user\n")

        return self.results

    def generate_report(self, output_file: Optional[str] = None) -> Dict:
        """
        Generate validation report from collected results.

        Args:
            output_file: Optional file path to save JSON report

        Returns:
            Report dictionary
        """
        if not self.results:
            logger.warning("No validation results to report")
            return {}

        # Calculate statistics
        successful = sum(1 for r in self.results if r.success)
        total = len(self.results)
        success_rate = (successful / total * 100) if total > 0 else 0

        # Group by state
        by_state = defaultdict(list)
        for result in self.results:
            if result.state:
                by_state[result.state].append(result)

        # Calculate confidence statistics
        confidences = [r.confidence for r in self.results if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        min_confidence = min(confidences) if confidences else 0
        max_confidence = max(confidences) if confidences else 0

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_validations": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": f"{success_rate:.1f}%",
                "confidence_stats": {
                    "average": f"{avg_confidence:.1%}",
                    "minimum": f"{min_confidence:.1%}",
                    "maximum": f"{max_confidence:.1%}"
                }
            },
            "by_state": {
                state: {
                    "count": len(results),
                    "success_rate": f"{(sum(1 for r in results if r.success) / len(results) * 100):.1f}%"
                }
                for state, results in by_state.items()
            },
            "results": [r.to_dict() for r in self.results]
        }

        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Report saved to: {output_file}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")

        return report

    def print_report(self) -> None:
        """Print human-readable validation report."""
        if not self.results:
            print("No validation results to report")
            return

        report = self.generate_report()
        summary = report.get('summary', {})

        print(f"\n{'='*60}")
        print("📊 Validation Report")
        print(f"{'='*60}")
        print(f"Generated: {report['generated_at']}")
        print(f"\nSummary:")
        print(f"  Total validations: {summary['total_validations']}")
        print(f"  Successful: {summary['successful']} ✅")
        print(f"  Failed: {summary['failed']} ❌")
        print(f"  Success rate: {summary['success_rate']}")
        print(f"\nConfidence Statistics:")
        print(f"  Average: {summary['confidence_stats']['average']}")
        print(f"  Minimum: {summary['confidence_stats']['minimum']}")
        print(f"  Maximum: {summary['confidence_stats']['maximum']}")

        by_state = report.get('by_state', {})
        if by_state:
            print(f"\nBy State:")
            for state, stats in by_state.items():
                print(f"  {state}: {stats['count']} ({stats['success_rate']})")

        print(f"\n{'='*60}\n")


class OCRValidationError(Exception):
    """Base exception for OCR validation errors."""
    pass


def load_batch_file(batch_file: str) -> List[Dict[str, str]]:
    """Load device list from JSON file."""
    path = Path(batch_file)

    if not path.exists():
        raise OCRValidationError(f"Batch file not found: {batch_file}")

    try:
        with open(path, 'r') as f:
            devices = json.load(f)
            if not isinstance(devices, list):
                raise OCRValidationError("JSON file must contain a list of devices")
            return devices
    except json.JSONDecodeError as e:
        raise OCRValidationError(f"Invalid JSON: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Device selection (optional - only used for logging/identification)
    device_group = parser.add_mutually_exclusive_group()
    device_group.add_argument('--device', default='local_device',
                             help='Device identifier for logging (default: local_device)')
    device_group.add_argument('--batch',
                             help='Batch file (JSON) with device list')

    # Validation mode
    parser.add_argument('--loop', action='store_true',
                       help='Run continuous validation loop')
    parser.add_argument('--interval', type=int, default=5,
                       help='Seconds between validations (default: 5)')
    parser.add_argument('--duration', type=int,
                       help='Total duration in seconds (default: infinite)')

    # Output options
    parser.add_argument('--report',
                       help='Save validation report to JSON file')
    parser.add_argument('--gpu', action='store_true',
                       help='Use GPU acceleration for OCR')
    parser.add_argument('--video-device', default='/dev/video0',
                       help='Video device path (default: /dev/video0)')

    args = parser.parse_args()

    try:
        # Initialize validator
        validator = OCRValidator(video_device=args.video_device, use_gpu=args.gpu)

        # Single device validation
        if args.device:
            if args.loop:
                # Continuous validation loop
                validator.validate_loop(
                    device=args.device,
                    interval=args.interval,
                    duration=args.duration
                )
            else:
                # Single validation
                result = validator.validate_state(args.device)
                print(f"\n{result}\n")

            # Generate report if requested
            if args.report:
                validator.generate_report(args.report)

            validator.print_report()

        # Batch validation
        elif args.batch:
            devices = load_batch_file(args.batch)
            print(f"\n🔄 Validating {len(devices)} device(s)...\n")

            for device_config in devices:
                host = device_config.get('host')
                if not host:
                    logger.warning("Skipping device with missing 'host' field")
                    continue

                result = validator.validate_state(host)
                print(result)

            if args.report:
                validator.generate_report(args.report)

            validator.print_report()

    except OCRValidationError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        logger.exception("Unexpected error:")
        sys.exit(1)


if __name__ == '__main__':
    main()
