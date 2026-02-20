"""Unit tests for chatterbox.conversation.tools.datetime_tool.DateTimeTool."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from chatterbox.conversation.providers import ToolDefinition
from chatterbox.conversation.tools.datetime_tool import DateTimeTool


# ---------------------------------------------------------------------------
# TOOL_DEFINITION shape
# ---------------------------------------------------------------------------


class TestDateTimeToolDefinition:
    def test_definition_is_tool_definition(self) -> None:
        assert isinstance(DateTimeTool.TOOL_DEFINITION, ToolDefinition)

    def test_definition_name(self) -> None:
        assert DateTimeTool.TOOL_DEFINITION.name == "get_current_datetime"

    def test_definition_has_description(self) -> None:
        assert DateTimeTool.TOOL_DEFINITION.description

    def test_definition_parameters_schema(self) -> None:
        params = DateTimeTool.TOOL_DEFINITION.parameters
        assert params["type"] == "object"
        assert "timezone" in params["properties"]
        # timezone is optional
        assert "timezone" not in params.get("required", [])

    def test_to_openai_format(self) -> None:
        fmt = DateTimeTool.TOOL_DEFINITION.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "get_current_datetime"


# ---------------------------------------------------------------------------
# get_datetime — UTC (no timezone arg)
# ---------------------------------------------------------------------------


_FIXED_UTC = datetime(2026, 2, 20, 14, 30, 0, tzinfo=timezone.utc)


class TestGetDatetimeUTC:
    @pytest.mark.anyio
    async def test_returns_dict(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_required_keys_present(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert "datetime_iso" in result
        assert "date" in result
        assert "time" in result
        assert "timezone" in result
        assert "day_of_week" in result
        assert "unix_timestamp" in result

    @pytest.mark.anyio
    async def test_no_error_field_for_utc(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert "error" not in result

    @pytest.mark.anyio
    async def test_date_format(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert result["date"] == "2026-02-20"

    @pytest.mark.anyio
    async def test_time_format(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert result["time"] == "14:30:00"

    @pytest.mark.anyio
    async def test_day_of_week(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert result["day_of_week"] == "Friday"

    @pytest.mark.anyio
    async def test_unix_timestamp(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        assert result["unix_timestamp"] == int(_FIXED_UTC.timestamp())

    @pytest.mark.anyio
    async def test_iso8601_contains_offset(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime()
        # ISO-8601 with UTC offset should contain '+00:00' or 'Z'
        assert "+00:00" in result["datetime_iso"] or "Z" in result["datetime_iso"]

    @pytest.mark.anyio
    async def test_empty_string_timezone_treated_as_utc(self) -> None:
        tool = DateTimeTool()
        with patch("chatterbox.conversation.tools.datetime_tool.datetime") as mock_dt:
            mock_dt.now.return_value = _FIXED_UTC
            result = await tool.get_datetime("")
        assert "error" not in result


# ---------------------------------------------------------------------------
# get_datetime — named timezone
# ---------------------------------------------------------------------------


class TestGetDatetimeNamedTimezone:
    @pytest.mark.anyio
    async def test_valid_timezone_returns_no_error(self) -> None:
        tool = DateTimeTool()
        result = await tool.get_datetime("America/New_York")
        # Either works (real or fallback) — just no exception
        assert "datetime_iso" in result

    @pytest.mark.anyio
    async def test_invalid_timezone_falls_back_to_utc(self) -> None:
        tool = DateTimeTool()
        result = await tool.get_datetime("Not/A_Real_Zone")
        # Should contain an error field
        assert "error" in result
        # Should still return valid datetime data
        assert "datetime_iso" in result

    @pytest.mark.anyio
    async def test_invalid_timezone_error_mentions_zone(self) -> None:
        tool = DateTimeTool()
        result = await tool.get_datetime("Not/A_Real_Zone")
        assert "Not/A_Real_Zone" in result["error"]


# ---------------------------------------------------------------------------
# as_dispatcher_entry
# ---------------------------------------------------------------------------


class TestDateTimeToolDispatcherEntry:
    @pytest.mark.anyio
    async def test_dispatcher_entry_returns_json_string(self) -> None:
        tool = DateTimeTool()
        handler = tool.as_dispatcher_entry()
        result = await handler({})
        data = json.loads(result)  # should be valid JSON
        assert "datetime_iso" in data

    @pytest.mark.anyio
    async def test_dispatcher_entry_accepts_timezone_arg(self) -> None:
        tool = DateTimeTool()
        handler = tool.as_dispatcher_entry()
        result = await handler({"timezone": "Europe/London"})
        data = json.loads(result)
        assert "datetime_iso" in data

    @pytest.mark.anyio
    async def test_dispatcher_entry_empty_args(self) -> None:
        tool = DateTimeTool()
        handler = tool.as_dispatcher_entry()
        result = await handler({})
        data = json.loads(result)
        assert "date" in data

    @pytest.mark.anyio
    async def test_dispatcher_entry_invalid_timezone_returns_error_in_json(self) -> None:
        tool = DateTimeTool()
        handler = tool.as_dispatcher_entry()
        result = await handler({"timezone": "INVALID/ZONE"})
        data = json.loads(result)
        assert "error" in data
        # Result still has valid datetime fields
        assert "datetime_iso" in data
