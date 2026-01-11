"""Tests for the core Cackle agent."""

import pytest
from cackle.agent import VoiceAssistantAgent


def test_agent_initialization():
    """Test that agent can be initialized with default settings."""
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b",
    )
    assert agent is not None
    assert agent.ollama_model == "llama3.1:8b"


@pytest.mark.asyncio
async def test_agent_process_input():
    """Test that agent can process basic input."""
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b",
    )

    # Note: This test requires Ollama to be running
    # In real CI, we'd mock the LLM calls
    response = await agent.process_input("Hello")
    assert isinstance(response, str)
    assert len(response) > 0
