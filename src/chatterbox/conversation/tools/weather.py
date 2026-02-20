"""
Weather tool for the Chatterbox agentic loop.

Uses the Open-Meteo API (https://open-meteo.com/) which is free and requires
no API key.  Two endpoints are used:

1. **Geocoding** — resolves a human-readable location string to coordinates.
   ``https://geocoding-api.open-meteo.com/v1/search``

2. **Forecast** — returns current weather conditions for given coordinates.
   ``https://api.open-meteo.com/v1/forecast``

The ``WeatherTool`` class exposes:

- ``WeatherTool.TOOL_DEFINITION`` — a ``ToolDefinition`` ready to be passed
  to ``AgenticLoop.run()``.
- ``WeatherTool.get_weather(location)`` — async method that performs the
  two-step geocode + weather fetch.
- ``WeatherTool.as_dispatcher_entry()`` — returns an async callable suitable
  for use inside a ``ToolDispatcher``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from chatterbox.conversation.providers import ToolDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# ---------------------------------------------------------------------------
# WMO weather interpretation codes → human-readable conditions
# Source: https://open-meteo.com/en/docs (WMO Weather Code table)
# ---------------------------------------------------------------------------

_WMO_CONDITIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherTool:
    """Fetches current weather conditions using Open-Meteo (no API key required).

    Attributes:
        TOOL_DEFINITION: Ready-to-use ``ToolDefinition`` for ``AgenticLoop``.
        timeout: HTTP request timeout in seconds (default 10).
    """

    TOOL_DEFINITION: ToolDefinition = ToolDefinition(
        name="get_weather",
        description=(
            "Get current weather conditions for a location. "
            "Returns temperature (Celsius and Fahrenheit), sky conditions, "
            "relative humidity, and wind speed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": (
                        "City name, 'City, State', or 'City, Country'. "
                        "Examples: 'Kansas City', 'London', 'Paris, France', "
                        "'Austin, Texas'."
                    ),
                }
            },
            "required": ["location"],
        },
    )

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_weather(self, location: str) -> dict[str, Any]:
        """Fetch current weather for *location*.

        Args:
            location: Human-readable location string such as ``"Kansas City"``,
                ``"London"``, or ``"Paris, France"``.

        Returns:
            A dict with keys:
            - ``location_name`` (str): Resolved place name from geocoder.
            - ``temperature_c`` (float): Temperature in Celsius.
            - ``temperature_f`` (float): Temperature in Fahrenheit.
            - ``conditions`` (str): Sky/weather conditions description.
            - ``humidity_percent`` (int): Relative humidity (0–100).
            - ``wind_speed_kmh`` (float): Wind speed in km/h.
            - ``wind_speed_mph`` (float): Wind speed in mph.

        Raises:
            ValueError: If the location cannot be geocoded.
            httpx.HTTPStatusError: If either API call returns a non-2xx status.
            httpx.TimeoutException: If a request exceeds ``self.timeout``.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            lat, lon, resolved_name = await self._geocode(client, location)
            return await self._fetch_conditions(client, lat, lon, resolved_name)

    def as_dispatcher_entry(self):
        """Return an async callable for use inside a ``ToolDispatcher``.

        Usage::

            weather = WeatherTool()
            handlers = {"get_weather": weather.as_dispatcher_entry()}

            async def dispatcher(name, args):
                handler = handlers.get(name)
                if handler is None:
                    return json.dumps({"error": f"Unknown tool: {name}"})
                return await handler(args)
        """

        async def _call(args: dict[str, Any]) -> str:
            location = args.get("location", "")
            if not location:
                return json.dumps({"error": "Missing required argument: location"})
            try:
                result = await self.get_weather(location)
                return json.dumps(result)
            except ValueError as exc:
                return json.dumps({"error": str(exc)})
            except httpx.HTTPStatusError as exc:
                logger.error("Weather API HTTP error: %s", exc)
                return json.dumps({"error": f"Weather service error: {exc.response.status_code}"})
            except httpx.TimeoutException:
                logger.error("Weather API timed out for location: %r", location)
                return json.dumps({"error": "Weather service timed out"})

        return _call

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _geocode(
        self, client: httpx.AsyncClient, location: str
    ) -> tuple[float, float, str]:
        """Resolve *location* to (lat, lon, resolved_name).

        Args:
            client: An active ``httpx.AsyncClient``.
            location: Human-readable location string.

        Returns:
            Tuple of (latitude, longitude, resolved place name).

        Raises:
            ValueError: If no matching location is found.
            httpx.HTTPStatusError: On non-2xx response.
        """
        logger.debug("Geocoding location: %r", location)
        response = await client.get(
            _GEOCODING_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results")
        if not results:
            raise ValueError(f"Location not found: {location!r}")

        place = results[0]
        lat: float = place["latitude"]
        lon: float = place["longitude"]

        # Build a human-readable name from the geocoder response
        name_parts = [place.get("name", location)]
        admin = place.get("admin1")  # e.g. "Missouri" for Kansas City
        country = place.get("country")
        if admin:
            name_parts.append(admin)
        if country:
            name_parts.append(country)
        resolved_name = ", ".join(name_parts)

        logger.debug("Geocoded %r → %s (%.4f, %.4f)", location, resolved_name, lat, lon)
        return lat, lon, resolved_name

    async def _fetch_conditions(
        self,
        client: httpx.AsyncClient,
        lat: float,
        lon: float,
        resolved_name: str,
    ) -> dict[str, Any]:
        """Fetch current conditions for *lat*/*lon*.

        Args:
            client: An active ``httpx.AsyncClient``.
            lat: Latitude.
            lon: Longitude.
            resolved_name: Human-readable name for the location (from geocoder).

        Returns:
            Weather dict (see ``get_weather`` docstring for shape).

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        logger.debug("Fetching weather for (%.4f, %.4f)", lat, lon)
        response = await client.get(
            _WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "weather_code",
                    "wind_speed_10m",
                ]),
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
            },
        )
        response.raise_for_status()
        data = response.json()

        current = data["current"]
        temp_c: float = current["temperature_2m"]
        temp_f: float = round(temp_c * 9 / 5 + 32, 1)
        humidity: int = int(current["relative_humidity_2m"])
        wind_kmh: float = current["wind_speed_10m"]
        wind_mph: float = round(wind_kmh * 0.621371, 1)
        weather_code: int = int(current["weather_code"])
        conditions: str = _WMO_CONDITIONS.get(weather_code, f"Unknown conditions (code {weather_code})")

        return {
            "location_name": resolved_name,
            "temperature_c": temp_c,
            "temperature_f": temp_f,
            "conditions": conditions,
            "humidity_percent": humidity,
            "wind_speed_kmh": wind_kmh,
            "wind_speed_mph": wind_mph,
        }
