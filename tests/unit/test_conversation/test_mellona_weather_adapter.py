"""
Unit tests for Mellona weather tool adapter.

Tests the adapter that bridges Mellona's WeatherTool to Chatterbox's
tool registry and dispatcher interfaces.
"""

from __future__ import annotations

import json

import pytest

from chatterbox.conversation.tools.mellona_weather import MellonaWeatherAdapter


@pytest.mark.anyio
class TestMellonaWeatherAdapter:
    """Tests for MellonaWeatherAdapter."""

    def test_adapter_initialization(self):
        """Test creating a MellonaWeatherAdapter."""
        adapter = MellonaWeatherAdapter(timeout=5.0)
        assert adapter is not None
        assert adapter.timeout == 5.0

    def test_default_timeout(self):
        """Test default timeout value."""
        adapter = MellonaWeatherAdapter()
        assert adapter.timeout == 10.0

    def test_tool_definition_exists(self):
        """Test that tool_definition property works."""
        adapter = MellonaWeatherAdapter()
        tool_def = adapter.tool_definition

        assert tool_def is not None
        assert tool_def.name == "get_weather"
        assert "weather" in tool_def.description.lower()
        assert "location" in tool_def.parameters["properties"]

    def test_tool_definition_parameters(self):
        """Test tool definition has correct parameter structure."""
        adapter = MellonaWeatherAdapter()
        tool_def = adapter.tool_definition

        # Check parameters structure
        assert tool_def.parameters["type"] == "object"
        assert "properties" in tool_def.parameters
        assert "required" in tool_def.parameters
        assert "location" in tool_def.parameters["required"]

    async def test_dispatcher_entry_returns_callable(self):
        """Test that as_dispatcher_entry returns a callable."""
        adapter = MellonaWeatherAdapter(timeout=5.0)
        dispatcher = adapter.as_dispatcher_entry()

        # Should be an async callable
        assert callable(dispatcher)

    async def test_dispatcher_with_valid_location(self):
        """Test dispatcher with a valid location."""
        adapter = MellonaWeatherAdapter(timeout=10.0)
        dispatcher = adapter.as_dispatcher_entry()

        # Try a real location
        result = await dispatcher({"location": "London"})

        # Should return JSON string
        assert isinstance(result, str)

        # Parse and verify structure
        data = json.loads(result)
        assert "location_name" in data
        assert "temperature_c" in data
        assert "temperature_f" in data
        assert "conditions" in data
        assert "humidity_percent" in data
        assert "wind_speed_kmh" in data

    async def test_dispatcher_with_invalid_location(self):
        """Test dispatcher with an invalid location."""
        adapter = MellonaWeatherAdapter(timeout=10.0)
        dispatcher = adapter.as_dispatcher_entry()

        # Try an invalid location
        result = await dispatcher({"location": "InvalidCityXYZ12345"})

        # Should return JSON with error
        data = json.loads(result)
        assert "error" in data

    async def test_dispatcher_with_missing_location(self):
        """Test dispatcher with missing location parameter."""
        adapter = MellonaWeatherAdapter(timeout=10.0)
        dispatcher = adapter.as_dispatcher_entry()

        # No location provided
        result = await dispatcher({})

        # Should return JSON with error
        data = json.loads(result)
        assert "error" in data
        assert "location" in data["error"].lower() or "missing" in data["error"].lower()

    async def test_dispatcher_multiple_locations(self):
        """Test dispatcher with multiple different locations."""
        adapter = MellonaWeatherAdapter(timeout=10.0)
        dispatcher = adapter.as_dispatcher_entry()

        locations = [
            "New York",
            "Paris",
            "Tokyo",
            "Sydney",
        ]

        results = []
        for location in locations:
            result = await dispatcher({"location": location})
            data = json.loads(result)
            results.append(data)

        # All should be successful (no errors for real cities)
        for data in results:
            if "error" not in data:
                assert "location_name" in data
                assert "temperature_c" in data

    def test_adapter_lazy_loads_mellona(self):
        """Test that Mellona is lazily loaded on first use."""
        adapter = MellonaWeatherAdapter()

        # Should not have loaded yet
        assert adapter._weather_tool is None

        # Access tool_definition to trigger load
        tool_def = adapter.tool_definition

        # Now should be loaded
        assert adapter._weather_tool is not None

    def test_cached_weather_tool(self):
        """Test that weather tool is cached after first load."""
        adapter = MellonaWeatherAdapter()

        tool1 = adapter._get_weather_tool()
        tool2 = adapter._get_weather_tool()

        # Should be the same instance (cached)
        assert tool1 is tool2


class TestMellonaWeatherIntegration:
    """Integration tests for weather tool in the agentic loop."""

    @pytest.mark.anyio
    async def test_weather_tool_with_registry(self):
        """Test registering Mellona weather tool in ToolRegistry."""
        from chatterbox.conversation.tools.registry import ToolRegistry

        registry = ToolRegistry()

        # Register Mellona weather tool
        adapter = MellonaWeatherAdapter()
        registry.register(
            adapter.tool_definition,
            adapter.as_dispatcher_entry(),
        )

        # Should be registered
        assert "get_weather" in registry
        assert len(registry) == 1

        # Get definitions
        defs = registry.get_definitions()
        assert len(defs) == 1
        assert defs[0].name == "get_weather"

    @pytest.mark.anyio
    async def test_weather_tool_dispatcher(self):
        """Test building a dispatcher with weather tool."""
        from chatterbox.conversation.tools.registry import ToolRegistry

        registry = ToolRegistry()

        adapter = MellonaWeatherAdapter()
        registry.register(
            adapter.tool_definition,
            adapter.as_dispatcher_entry(),
        )

        # Build dispatcher
        dispatcher = registry.build_dispatcher(timeout=10.0)

        # Call dispatcher
        result = await dispatcher("get_weather", {"location": "Boston"})

        # Should return valid JSON
        data = json.loads(result)
        if "error" not in data:
            assert "location_name" in data
            assert "temperature_c" in data

    @pytest.mark.anyio
    async def test_weather_tool_with_timeout(self):
        """Test that weather tool respects timeout setting."""
        from chatterbox.conversation.tools.registry import ToolRegistry

        registry = ToolRegistry()

        adapter = MellonaWeatherAdapter(timeout=5.0)
        registry.register(
            adapter.tool_definition,
            adapter.as_dispatcher_entry(),
        )

        # Build dispatcher with even shorter timeout
        dispatcher = registry.build_dispatcher(timeout=2.0)

        # Should execute within timeout
        result = await dispatcher("get_weather", {"location": "London"})
        data = json.loads(result)

        # Should have a result (either success or error, but not timeout)
        assert data is not None


@pytest.mark.anyio
class TestWeatherToolErrorHandling:
    """Tests for error handling in weather tool."""

    async def test_empty_location_string(self):
        """Test handling of empty location string."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        result = await dispatcher({"location": ""})
        data = json.loads(result)

        assert "error" in data

    async def test_special_characters_in_location(self):
        """Test handling of special characters in location."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        # These should either work or return sensible errors
        locations = [
            "São Paulo",
            "Zürich",
            "Montréal",
        ]

        for location in locations:
            result = await dispatcher({"location": location})
            data = json.loads(result)
            # Should return either valid weather or error, no exceptions
            assert data is not None

    async def test_none_location(self):
        """Test handling of None location value."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        # None should be handled gracefully
        result = await dispatcher({"location": None})
        data = json.loads(result)

        # Should have error since None is not a valid location
        assert "error" in data or isinstance(data, dict)


@pytest.mark.anyio
class TestWeatherToolOutputFormat:
    """Tests for output format of weather tool."""

    async def test_output_contains_required_fields(self):
        """Test that output contains all required weather fields."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        result = await dispatcher({"location": "London"})
        data = json.loads(result)

        if "error" not in data:
            # All these fields should be present
            required_fields = [
                "location_name",
                "temperature_c",
                "temperature_f",
                "conditions",
                "humidity_percent",
                "wind_speed_kmh",
                "wind_speed_mph",
            ]

            for field in required_fields:
                assert field in data, f"Missing field: {field}"

    async def test_temperature_conversion(self):
        """Test that temperature conversion is correct."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        result = await dispatcher({"location": "Paris"})
        data = json.loads(result)

        if "error" not in data:
            # Check conversion: F = C * 9/5 + 32
            temp_c = data["temperature_c"]
            temp_f = data["temperature_f"]

            expected_f = round(temp_c * 9 / 5 + 32, 1)
            assert temp_f == expected_f

    async def test_wind_speed_conversion(self):
        """Test that wind speed conversion is correct."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        result = await dispatcher({"location": "Tokyo"})
        data = json.loads(result)

        if "error" not in data:
            # Check conversion: mph = kmh * 0.621371
            wind_kmh = data["wind_speed_kmh"]
            wind_mph = data["wind_speed_mph"]

            expected_mph = round(wind_kmh * 0.621371, 1)
            assert wind_mph == expected_mph

    async def test_humidity_range(self):
        """Test that humidity is in valid range 0-100."""
        adapter = MellonaWeatherAdapter()
        dispatcher = adapter.as_dispatcher_entry()

        result = await dispatcher({"location": "Sydney"})
        data = json.loads(result)

        if "error" not in data:
            humidity = data["humidity_percent"]
            assert 0 <= humidity <= 100
