"""Tests for the Cackle tools system."""

from cackle.tools import get_available_tools
from cackle.tools.builtin import get_time


def test_get_available_tools():
    """Test that we can get the list of available tools."""
    tools = get_available_tools()
    assert len(tools) > 0
    assert any(tool.name == "GetTime" for tool in tools)


def test_get_time_tool():
    """Test the get_time tool function."""
    result = get_time()
    assert isinstance(result, str)
    # Should be in format YYYY-MM-DD HH:MM:SS
    assert len(result) == 19
    assert result[4] == "-"
    assert result[7] == "-"
    assert result[10] == " "
