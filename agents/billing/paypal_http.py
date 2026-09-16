"""HTTP transports for PayPal adapters with both async (httpx) and sync support."""

import json as json_module
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class PayPalHttpResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class PayPalHttpClient:
    """Synchronous POST JSON or form data without logging headers or credential values."""

    def __init__(self, opener: Callable[..., Any] = urlopen, timeout_seconds: float = 30.0):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.opener = opener
        self.timeout_seconds = timeout_seconds

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> PayPalHttpResponse:
        if data is not None and json is not None:
            raise ValueError("Use either form data or JSON, not both")
        body = (
            urlencode(data).encode()
            if data is not None
            else json_module.dumps(json or {}).encode()
        )
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                payload = json_module_load(response)
                return PayPalHttpResponse(response.status, payload)
        except HTTPError as err:
            try:
                payload = json_module.loads(err.read().decode("utf-8"))
            except Exception:
                payload = {"error": str(err), "status": err.code}
            return PayPalHttpResponse(err.code, payload)


class AsyncPayPalHttpClient:
    """Asynchronous HTTP client using httpx.AsyncClient to avoid blocking worker threads."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> PayPalHttpResponse:
        if data is not None and json is not None:
            raise ValueError("Use either form data or JSON, not both")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if data is not None:
                    resp = await client.post(url, headers=headers, data=data)
                else:
                    resp = await client.post(url, headers=headers, json=json)
                return PayPalHttpResponse(resp.status_code, resp.json())
        except ImportError:
            # Fallback to sync client in non-async environment
            sync_client = PayPalHttpClient(timeout_seconds=self.timeout_seconds)
            return sync_client.post(url, headers=headers, data=data, json=json)


def json_module_load(response: Any) -> dict[str, Any]:
    """Parse a response body while keeping transport details out of adapters."""
    return json_module.loads(response.read().decode("utf-8"))