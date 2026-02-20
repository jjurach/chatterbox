"""
Date/time tool for the Chatterbox agentic loop.

Returns the current date and time, optionally adjusted for a named timezone.
This tool requires no external API and serves as a lightweight reference
implementation alongside :class:`WeatherTool`.

The ``DateTimeTool`` class exposes:

- ``DateTimeTool.TOOL_DEFINITION`` — a ``ToolDefinition`` ready to be passed
  to ``AgenticLoop.run()``.
- ``DateTimeTool.get_datetime(timezone)`` — async method that returns the
  current date and time.
- ``DateTimeTool.as_dispatcher_entry()`` — returns an async callable suitable
  for registration with ``ToolRegistry``.

Timezone support uses the stdlib ``zoneinfo`` module (Python 3.9+).  If an
unrecognised timezone key is supplied the result falls back to UTC and
includes an ``"error"`` field describing the problem.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # Python 3.9+
    _ZONEINFO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ZONEINFO_AVAILABLE = False

from chatterbox.conversation.providers import ToolDefinition

logger = logging.getLogger(__name__)


class DateTimeTool:
    """Returns the current date and time, with optional timezone support.

    Attributes:
        TOOL_DEFINITION: Ready-to-use ``ToolDefinition`` for ``AgenticLoop``.
    """

    TOOL_DEFINITION: ToolDefinition = ToolDefinition(
        name="get_current_datetime",
        description=(
            "Get the current date and time. "
            "Returns the date, time, day of the week, and Unix timestamp. "
            "Optionally accepts an IANA timezone name such as "
            "'America/New_York' or 'Europe/London'; defaults to UTC."
        ),
        parameters={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "IANA timezone name, e.g. 'America/Chicago', "
                        "'Europe/Paris', 'Asia/Tokyo'. "
                        "Omit or leave empty for UTC."
                    ),
                }
            },
            "required": [],
        },
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_datetime(self, timezone_name: str | None = None) -> dict[str, Any]:
        """Return the current date and time.

        Args:
            timezone_name: IANA timezone name (e.g. ``"America/New_York"``).
                ``None`` or an empty string defaults to UTC.

        Returns:
            A dict with keys:

            - ``datetime_iso`` (str): ISO-8601 timestamp with offset, e.g.
              ``"2026-02-20T14:30:00+00:00"``.
            - ``date`` (str): Date in ``YYYY-MM-DD`` format.
            - ``time`` (str): Time in ``HH:MM:SS`` format.
            - ``timezone`` (str): Resolved timezone name.
            - ``day_of_week`` (str): Full weekday name, e.g. ``"Friday"``.
            - ``unix_timestamp`` (int): Seconds since Unix epoch (UTC).
            - ``error`` (str, optional): Present only if the requested
              timezone was invalid; result falls back to UTC.
        """
        tz, tz_error = self._resolve_timezone(timezone_name)
        now = datetime.now(tz=tz)

        result: dict[str, Any] = {
            "datetime_iso": now.isoformat(timespec="seconds"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": str(tz),
            "day_of_week": now.strftime("%A"),
            "unix_timestamp": int(now.timestamp()),
        }
        if tz_error:
            result["error"] = tz_error
        return result

    def as_dispatcher_entry(self):
        """Return an async callable for use with ``ToolRegistry``.

        Usage::

            dt = DateTimeTool()
            registry.register(DateTimeTool.TOOL_DEFINITION, dt.as_dispatcher_entry())
        """

        async def _call(args: dict[str, Any]) -> str:
            tz_name = args.get("timezone") or None
            result = await self.get_datetime(tz_name)
            return json.dumps(result)

        return _call

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_timezone(
        self, timezone_name: str | None
    ) -> tuple[Any, str | None]:
        """Resolve *timezone_name* to a timezone object.

        Returns:
            ``(tz_object, error_message_or_None)``
        """
        if not timezone_name:
            return timezone.utc, None

        if not _ZONEINFO_AVAILABLE:
            logger.warning(
                "zoneinfo not available (Python < 3.9); ignoring timezone %r",
                timezone_name,
            )
            return timezone.utc, (
                f"Timezone {timezone_name!r} ignored: zoneinfo not available. "
                "Showing UTC."
            )

        try:
            return ZoneInfo(timezone_name), None
        except ZoneInfoNotFoundError:
            logger.warning("Unknown timezone: %r; falling back to UTC", timezone_name)
            return timezone.utc, (
                f"Unknown timezone {timezone_name!r}; showing UTC instead."
            )
