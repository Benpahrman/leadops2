import json

from workers.web_search import search_web


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'<a class="result__a" href="https://example.gov">Public Portal</a>'


def test_search_web_returns_bounded_source_results():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    result = search_web("Cook County probate", opener=opener)

    assert result["ok"] is True
    assert result["requires_source_verification"] is True
    assert result["results"][0]["url"] == "https://example.gov"
    assert "q=Cook+County+probate" in calls[0][0].full_url


def test_search_web_rejects_invalid_limits():
    assert search_web("probate", limit=0)["ok"] is False
    assert search_web("", limit=5)["ok"] is False