"""Built-in tools for the Cackle agent.

This module provides the time tool for the agent.
"""

from datetime import datetime


def get_time() -> str:
    """Get the current time and date.

    Returns:
        A formatted string with the current date and time (YYYY-MM-DD HH:MM:SS)
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
