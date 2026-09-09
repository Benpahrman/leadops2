import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def set_env():
    os.environ.setdefault("LEADOPS_CORS_ORIGINS", "http://localhost:8000")
    os.environ.setdefault("LEADOPS_API_TOKEN", "test-token")
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("ALLOW_DEV_ADMIN", "true")

@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Ensure tests run predictably regardless of the current time of day."""
    monkeypatch.setenv("ENFORCE_OUTREACH_OFFICE_HOURS", "false")
    monkeypatch.setenv("LEADOPS_API_TOKEN", "test-token")
