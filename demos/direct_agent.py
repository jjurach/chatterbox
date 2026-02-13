#!/usr/bin/env python3
"""
Example: Using the Chatterbox Agent Directly

This example shows how to use the core agent without any protocol adapter.
This is useful when integrating the agent into your own application or when
you want to test agent logic directly.

Prerequisites:
    - Ollama running with llama3.1:8b model

Usage:
    python examples/direct_agent.py
"""

import asyncio
import logging

from chatterbox.agent import VoiceAssistantAgent


async def main():
    """Demonstrate direct agent usage."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    # Create the agent
    print("Initializing agent...")
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b",
        ollama_temperature=0.7,
        conversation_window_size=3,
        debug=False,
    )

    # Test queries
    queries = [
        "What time is it?",
        "What day of the week is it?",
        "Remember that for me.",
    ]

    print("\n" + "="*60)
    for query in queries:
        print(f"\nUser: {query}")
        response = await agent.process_input(query)
        print(f"Agent: {response}")
        print("-"*60)

    # Show memory
    print("\nConversation Memory:")
    print(agent.get_memory_summary())


if __name__ == "__main__":
    asyncio.run(main())
