import io
import json

import pytest

from workers.ollama_smoke import chat_with_ollama


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({
            "model": "qwen3b-large:latest",
            "choices": [{"message": {"content": "CONFIRMATION_OK"}}],
        }).encode()


def test_direct_ollama_runner_parses_reply_and_posts_to_chat_endpoint():
    calls = []

    def fake_opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    reply = chat_with_ollama(
        "Reply with exactly CONFIRMATION_OK",
        model="qwen3b-large:latest",
        base_url="http://localhost:11435/v1",
        opener=fake_opener,
    )

    assert reply.content == "CONFIRMATION_OK"
    assert calls[0][0].full_url == "http://localhost:11435/v1/chat/completions"
    assert json.loads(calls[0][0].data)["model"] == "qwen3b-large:latest"


def test_direct_ollama_runner_rejects_empty_prompt():
    with pytest.raises(ValueError):
        chat_with_ollama(" ")