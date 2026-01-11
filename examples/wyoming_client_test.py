#!/usr/bin/env python3
"""
Example: Testing Wyoming Server with Client

This example shows how to use the Wyoming client to send test queries
to a running Wyoming server. Useful for testing and development.

Prerequisites:
    - Wyoming server running (examples/wyoming_server.py)

Usage:
    python examples/wyoming_client_test.py "What time is it?"
    python examples/wyoming_client_test.py "Hello" --host 192.168.1.100
"""

import argparse
import asyncio
import logging
import sys

from cackle.adapters.wyoming.client import test_backend


def main():
    """Run the Wyoming client test."""
    parser = argparse.ArgumentParser(
        description="Test the Wyoming voice assistant server"
    )
    parser.add_argument(
        "text",
        help="Text to send to the server"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=10700,
        help="Server port"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    # Run the test
    asyncio.run(test_backend(args.text, args.host, args.port))


if __name__ == "__main__":
    main()
