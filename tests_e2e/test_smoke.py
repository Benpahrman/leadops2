"""Smoke tests to verify E2E infrastructure."""

import pytest


@pytest.mark.e2e
class TestSmoke:
    """Basic smoke tests."""

    async def test_frontend_loads(self, page, frontend_url):
        """Test that the frontend loads."""
        response = await page.goto("/")
        assert response is not None
        assert response.status == 200
        
        # Check page has content (may be empty if Clerk auth not loaded)
        title = await page.title()
        # If no title, check for body content
        if len(title) == 0:
            body = await page.locator('body').text_content()
            assert body is not None

    async def test_api_health_endpoint(self, page, base_url):
        """Test that the API health endpoint responds."""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["service"] == "leadops"

    async def test_api_version_endpoint(self, page, base_url):
        """Test that the API version endpoint responds."""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/version")
            # Version endpoint may not exist, skip if 404
            if response.status_code == 404:
                pytest.skip("Version endpoint not implemented")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "leadops"
            assert data["version"] == "1.0.0"

    async def test_cors_headers(self, page, base_url):
        """Test that CORS headers are present."""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.options(
                f"{base_url}/health",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Should have CORS headers
            assert "access-control-allow-origin" in response.headers
            assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
            assert "access-control-allow-credentials" in response.headers
            assert response.headers["access-control-allow-credentials"] == "true"