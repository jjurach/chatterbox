"""
Pytest configuration for the chatterbox test suite.

This module configures pytest behavior and filters deprecation warnings.
"""

import warnings
import sys
import pytest

# Configure warnings immediately when conftest is loaded
# This needs to happen before any imports that might trigger warnings

try:
    from langchain_core._api import LangChainDeprecationWarning
except ImportError:
    # Fallback if module structure changes
    LangChainDeprecationWarning = Warning

# Suppress Wyoming's audioop deprecation warning (not our code to fix)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*'audioop' is deprecated.*",
)

# Suppress LangChain deprecated agent warnings (using langchain-classic intentionally)
warnings.filterwarnings(
    "ignore",
    category=LangChainDeprecationWarning,
    message=".*LangChain agents will continue to be supported.*",
)

# Suppress LangChain memory migration warnings
warnings.filterwarnings(
    "ignore",
    category=LangChainDeprecationWarning,
    message=".*migration guide.*",
)


def pytest_configure(config):
    """Configure pytest additional settings."""
    # Register warnings as expected and should not fail tests
    config.addinivalue_line(
        "filterwarnings",
        "ignore:.*LangChain agents will continue to be supported.*",
    )
