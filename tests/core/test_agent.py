"""Tests for the core Chatterbox agent."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from chatterbox.agent import VoiceAssistantAgent


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
    """Test that agent can process basic input with mocked LLM."""
    with patch("chatterbox.agent.initialize_agent") as mock_init_agent:
        # Mock the agent executor
        mock_agent = AsyncMock()
        mock_agent.run = MagicMock(return_value="Mocked response")
        mock_init_agent.return_value = mock_agent

        agent = VoiceAssistantAgent(
            ollama_base_url="http://localhost:11434/v1",
            ollama_model="llama3.1:8b",
        )

        response = await agent.process_input("Hello")
        assert isinstance(response, str)
        assert response == "Mocked response"


def test_agent_memory_reset():
    """Test that agent memory can be reset."""
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b",
    )
    agent.reset_memory()
    # If no exception is raised, the reset was successful
    assert agent.memory is not None


def test_agent_memory_summary():
    """Test that agent can provide memory summary."""
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b",
    )
    summary = agent.get_memory_summary()
    # Memory summary can be string or list depending on LangChain version
    assert summary is not None
