"""Fast direct Ollama smoke testing without Antigravity session overhead."""

import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from .local_agent import DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL


@dataclass(frozen=True)
class OllamaReply:
    model: str
    content: str
    elapsed_seconds: float | None = None


def chat_with_ollama(
    prompt: str,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 60.0,
    opener: Callable[..., Any] = urlopen,
) -> OllamaReply:
    """Send one prompt to Ollama's OpenAI-compatible endpoint."""
    if not prompt.strip():
        raise ValueError("prompt is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    selected_model = model or os.getenv("LEADOPS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    selected_base_url = base_url or os.getenv(
        "LEADOPS_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL
    )
    payload = json.dumps({
        "model": selected_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode("utf-8")
    request = Request(
        f"{selected_base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            result = json.load(response)
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Ollama request failed: {error}") from error
    content = result.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama response did not contain message content")
    return OllamaReply(result.get("model", selected_model), content.strip())