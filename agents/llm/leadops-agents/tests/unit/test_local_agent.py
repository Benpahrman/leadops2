from workers.local_agent import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    create_local_coordinator,
    create_local_intake,
)
from workers.environment import load_local_environment


def test_default_local_model_is_gemma4_12b():
    assert DEFAULT_OLLAMA_MODEL == "gemma4:12b"


def test_environment_loader_is_safe_to_call_repeatedly():
    load_local_environment()
    load_local_environment()


def test_default_endpoint_targets_docker_published_port():
    assert DEFAULT_OLLAMA_BASE_URL == "http://localhost:11435/v1"


def test_local_coordinator_accepts_a_different_model():
    assert create_local_coordinator(model="qwen3b-large:latest") is not None


def test_lightweight_local_intake_accepts_a_different_model():
    assert create_local_intake(model="qwen3b-large:latest") is not None


def test_local_coordinator_is_constructible_with_web_search_enabled():
    assert create_local_coordinator(model="qwen3b-large:latest") is not None


def test_local_coordinator_can_be_created_without_calling_ollama(monkeypatch):
    monkeypatch.setenv("LEADOPS_OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("LEADOPS_OLLAMA_BASE_URL", "http://ollama.test/v1")

    assert create_local_coordinator() is not None