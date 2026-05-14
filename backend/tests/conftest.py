"""Shared test fixtures.

Provides:
- Async test database (SQLite in-memory for speed)
- Mock Redis client
- Mock LLM responses
- Test elder/configurator factory
"""
import pytest


@pytest.fixture
def test_elder_id():
    """A fixed elder ID for testing."""
    return "00000000-0000-0000-0000-000000000001"
