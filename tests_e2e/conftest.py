"""Playwright E2E test configuration."""

import os
import pytest
from playwright.async_api import async_playwright


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the API."""
    return os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def frontend_url():
    """Frontend URL (Vite dev server)."""
    return os.environ.get("E2E_FRONTEND_URL", "http://127.0.0.1:5173")


@pytest.fixture(scope="session")
def clerk_test_user():
    """Clerk test user credentials."""
    return {
        "email": os.environ.get("E2E_CLERK_EMAIL", "test@example.com"),
        "password": os.environ.get("E2E_CLERK_PASSWORD", "testpassword123"),
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def page(base_url, frontend_url):
    """Create a new page for each test."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            base_url=frontend_url,
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        page.base_url = frontend_url
        page.api_url = base_url
        yield page
        await context.close()
        await browser.close()


@pytest.fixture(scope="function")
async def authenticated_page(page, clerk_test_user):
    """Create a page with authenticated user."""
    # Sign in via Clerk
    await page.goto("/sign-in")
    await page.fill('input[name="emailAddress"]', clerk_test_user["email"])
    await page.fill('input[name="password"]', clerk_test_user["password"])
    await page.click('button[type="submit"]')
    
    # Wait for redirect to dashboard
    await page.wait_for_url("**/p/**", timeout=10000)
    
    yield page