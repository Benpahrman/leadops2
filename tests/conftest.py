import os
import pytest

@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Ensure tests run predictably regardless of the current time of day."""
    monkeypatch.setenv("ENFORCE_OUTREACH_OFFICE_HOURS", "false")
