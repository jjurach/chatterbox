"""Unit tests for chatterbox.conversation.tools.weather.WeatherTool."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from chatterbox.conversation.providers import ToolDefinition
from chatterbox.conversation.tools.weather import WeatherTool, _WMO_CONDITIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Build a mock httpx Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _mock_error_response(status_code: int) -> MagicMock:
    """Build a mock httpx Response that raises on raise_for_status."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"HTTP {status_code}", request=MagicMock(), response=resp
    )
    return resp


def _geo_response(
    name: str = "Kansas City",
    admin1: str = "Missouri",
    country: str = "United States",
    lat: float = 39.0997,
    lon: float = -94.5786,
) -> dict[str, Any]:
    return {
        "results": [
            {
                "name": name,
                "admin1": admin1,
                "country": country,
                "latitude": lat,
                "longitude": lon,
            }
        ]
    }


def _weather_response(
    temp_c: float = 22.5,
    humidity: int = 55,
    weather_code: int = 1,
    wind_kmh: float = 14.4,
) -> dict[str, Any]:
    return {
        "current": {
            "temperature_2m": temp_c,
            "relative_humidity_2m": humidity,
            "weather_code": weather_code,
            "wind_speed_10m": wind_kmh,
        }
    }


def _make_client_mock(
    *responses: MagicMock,
) -> tuple[MagicMock, MagicMock]:
    """Return (patch_target_mock, client_instance_mock) for httpx.AsyncClient.

    The client instance's ``get`` method is an AsyncMock that returns *responses*
    in sequence.
    """
    client_instance = AsyncMock()
    client_instance.get = AsyncMock(side_effect=list(responses))

    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=client_instance)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)

    async_client_cls = MagicMock(return_value=ctx_manager)
    return async_client_cls, client_instance


# ---------------------------------------------------------------------------
# TOOL_DEFINITION tests
# ---------------------------------------------------------------------------


class TestToolDefinition:
    def test_is_tool_definition(self):
        assert isinstance(WeatherTool.TOOL_DEFINITION, ToolDefinition)

    def test_name(self):
        assert WeatherTool.TOOL_DEFINITION.name == "get_weather"

    def test_description_mentions_weather(self):
        desc = WeatherTool.TOOL_DEFINITION.description.lower()
        assert "weather" in desc

    def test_parameters_have_location(self):
        params = WeatherTool.TOOL_DEFINITION.parameters
        assert "location" in params["properties"]
        assert params["required"] == ["location"]

    def test_to_openai_format(self):
        fmt = WeatherTool.TOOL_DEFINITION.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "get_weather"
        assert "parameters" in fmt["function"]


# ---------------------------------------------------------------------------
# get_weather — success path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_weather_returns_expected_keys():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response())
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Kansas City")

    assert set(result.keys()) == {
        "location_name",
        "temperature_c",
        "temperature_f",
        "conditions",
        "humidity_percent",
        "wind_speed_kmh",
        "wind_speed_mph",
    }


@pytest.mark.anyio
async def test_get_weather_location_name_includes_admin_and_country():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response(name="Kansas City", admin1="Missouri", country="United States"))
    wx_resp = _mock_response(_weather_response())
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Kansas City")

    assert "Kansas City" in result["location_name"]
    assert "Missouri" in result["location_name"]
    assert "United States" in result["location_name"]


@pytest.mark.anyio
async def test_get_weather_temperature_conversion():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(temp_c=0.0))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Somewhere")

    assert result["temperature_c"] == 0.0
    assert result["temperature_f"] == 32.0


@pytest.mark.anyio
async def test_get_weather_temperature_conversion_100c():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(temp_c=100.0))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Somewhere")

    assert result["temperature_f"] == 212.0


@pytest.mark.anyio
async def test_get_weather_known_wmo_code():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(weather_code=61))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("London")

    assert result["conditions"] == "Slight rain"


@pytest.mark.anyio
async def test_get_weather_unknown_wmo_code_fallback():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(weather_code=999))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Somewhere")

    assert "999" in result["conditions"]


@pytest.mark.anyio
async def test_get_weather_wind_speed_conversion():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(wind_kmh=16.093))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Somewhere")

    # 16.093 km/h ≈ 10.0 mph
    assert abs(result["wind_speed_mph"] - 10.0) < 0.1


# ---------------------------------------------------------------------------
# get_weather — error paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_weather_location_not_found_raises_value_error():
    tool = WeatherTool()
    geo_resp = _mock_response({"results": []})
    async_client_cls, _ = _make_client_mock(geo_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        with pytest.raises(ValueError, match="Location not found"):
            await tool.get_weather("xyzzy99nonexistent")


@pytest.mark.anyio
async def test_get_weather_null_results_raises_value_error():
    tool = WeatherTool()
    geo_resp = _mock_response({})  # no "results" key
    async_client_cls, _ = _make_client_mock(geo_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        with pytest.raises(ValueError, match="Location not found"):
            await tool.get_weather("???")


@pytest.mark.anyio
async def test_get_weather_geocoding_http_error_propagates():
    tool = WeatherTool()
    geo_resp = _mock_error_response(503)
    async_client_cls, _ = _make_client_mock(geo_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        with pytest.raises(httpx.HTTPStatusError):
            await tool.get_weather("Kansas City")


@pytest.mark.anyio
async def test_get_weather_weather_api_http_error_propagates():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_error_response(500)
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        with pytest.raises(httpx.HTTPStatusError):
            await tool.get_weather("Kansas City")


@pytest.mark.anyio
async def test_get_weather_timeout_propagates():
    tool = WeatherTool()

    client_instance = AsyncMock()
    client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=client_instance)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)
    async_client_cls = MagicMock(return_value=ctx_manager)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        with pytest.raises(httpx.TimeoutException):
            await tool.get_weather("Kansas City")


# ---------------------------------------------------------------------------
# as_dispatcher_entry
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatcher_entry_success():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(temp_c=25.0, weather_code=0))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    handler = tool.as_dispatcher_entry()
    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        raw = await handler({"location": "Kansas City"})

    data = json.loads(raw)
    assert "temperature_c" in data
    assert data["temperature_c"] == 25.0
    assert data["conditions"] == "Clear sky"


@pytest.mark.anyio
async def test_dispatcher_entry_missing_location_arg():
    tool = WeatherTool()
    handler = tool.as_dispatcher_entry()
    raw = await handler({})
    data = json.loads(raw)
    assert "error" in data
    assert "location" in data["error"]


@pytest.mark.anyio
async def test_dispatcher_entry_location_not_found():
    tool = WeatherTool()
    geo_resp = _mock_response({"results": []})
    async_client_cls, _ = _make_client_mock(geo_resp)

    handler = tool.as_dispatcher_entry()
    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        raw = await handler({"location": "nonexistent place xyz"})

    data = json.loads(raw)
    assert "error" in data


@pytest.mark.anyio
async def test_dispatcher_entry_http_error_returns_json_error():
    tool = WeatherTool()
    geo_resp = _mock_error_response(503)
    async_client_cls, _ = _make_client_mock(geo_resp)

    handler = tool.as_dispatcher_entry()
    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        raw = await handler({"location": "Kansas City"})

    data = json.loads(raw)
    assert "error" in data
    assert "503" in data["error"]


@pytest.mark.anyio
async def test_dispatcher_entry_timeout_returns_json_error():
    tool = WeatherTool()

    client_instance = AsyncMock()
    client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=client_instance)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)
    async_client_cls = MagicMock(return_value=ctx_manager)

    handler = tool.as_dispatcher_entry()
    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        raw = await handler({"location": "Kansas City"})

    data = json.loads(raw)
    assert "error" in data
    assert "timed out" in data["error"].lower()


# ---------------------------------------------------------------------------
# WMO condition coverage
# ---------------------------------------------------------------------------


class TestWmoConditions:
    def test_clear_sky(self):
        assert _WMO_CONDITIONS[0] == "Clear sky"

    def test_thunderstorm_with_hail(self):
        assert _WMO_CONDITIONS[99] == "Thunderstorm with heavy hail"

    def test_all_codes_are_strings(self):
        for code, description in _WMO_CONDITIONS.items():
            assert isinstance(description, str), f"WMO code {code} has non-string description"
            assert description, f"WMO code {code} has empty description"


# ---------------------------------------------------------------------------
# Location name edge cases
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_location_name_without_admin():
    """Geocoder may omit admin1 for some locations."""
    tool = WeatherTool()
    geo_data = {
        "results": [
            {
                "name": "London",
                "country": "United Kingdom",
                "latitude": 51.5074,
                "longitude": -0.1278,
                # no "admin1"
            }
        ]
    }
    geo_resp = _mock_response(geo_data)
    wx_resp = _mock_response(_weather_response())
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("London")

    assert "London" in result["location_name"]
    assert "United Kingdom" in result["location_name"]
    # Should not contain a trailing comma from missing admin1
    assert not result["location_name"].startswith(",")
    assert not result["location_name"].endswith(",")


@pytest.mark.anyio
async def test_humidity_cast_to_int():
    tool = WeatherTool()
    geo_resp = _mock_response(_geo_response())
    wx_resp = _mock_response(_weather_response(humidity=72))
    async_client_cls, _ = _make_client_mock(geo_resp, wx_resp)

    with patch("chatterbox.conversation.tools.weather.httpx.AsyncClient", async_client_cls):
        result = await tool.get_weather("Somewhere")

    assert isinstance(result["humidity_percent"], int)
    assert result["humidity_percent"] == 72
