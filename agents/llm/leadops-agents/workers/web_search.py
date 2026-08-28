"""Small bounded web search tool for local Scout development."""

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class _ResultParser(HTMLParser):
    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit
        self.results: list[SearchResult] = []
        self._title = ""
        self._snippet = ""
        self._url = ""
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        if tag == "a" and "result__a" in classes:
            self._url = attributes.get("href", "") or ""
            self._in_title = True
        elif "result__snippet" in classes:
            self._in_snippet = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title += data
        if self._in_snippet:
            self._snippet += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title:
            if self._url and self._title and len(self.results) < self.limit:
                self.results.append(SearchResult(
                    self._title.strip(), self._url, self._snippet.strip()
                ))
            self._title = ""
            self._url = ""
            self._in_title = False
        if self._in_snippet:
            self._in_snippet = False


def search_web(
    query: str,
    limit: int = 5,
    timeout_seconds: float = 10.0,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Search public web results; return URLs for Scout to verify separately."""
    if not query.strip():
        return {"ok": False, "error": "query is required"}
    if not 1 <= limit <= 10:
        return {"ok": False, "error": "limit must be between 1 and 10"}
    if timeout_seconds <= 0:
        return {"ok": False, "error": "timeout_seconds must be positive"}
    request = Request(
        f"https://html.duckduckgo.com/html/?q={quote_plus(query.strip())}",
        headers={"User-Agent": "LeadOps-Scout/0.1"},
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            parser = _ResultParser(limit)
            body = response.read().decode("utf-8", errors="replace")
            if "challenge" in body.lower():
                return {"ok": False, "error": "search provider returned a challenge"}
            parser.feed(body)
    except Exception as error:
        return {"ok": False, "error": f"search request failed: {error}"}
    if not parser.results:
        return {"ok": False, "error": "search returned no parseable results"}
    return {
        "ok": True,
        "query": query.strip(),
        "results": [result.__dict__ for result in parser.results],
        "requires_source_verification": True,
    }