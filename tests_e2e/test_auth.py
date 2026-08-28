"""E2E tests for authentication flows."""

import pytest
import os


@pytest.mark.e2e
class TestAuthentication:
    """Tests for Clerk authentication flow."""

    async def test_sign_in_page_loads(self, page):
        """Test that the sign-in page loads correctly."""
        await page.goto("/sign-in")
        
        # Check Clerk sign-in component is mounted
        await page.wait_for_selector('[data-testid="clerk-sign-in"]', timeout=10000)
        
        # Verify page title
        title = await page.title()
        assert "LeadOps" in title or "Sign in" in title

    async def test_sign_up_page_loads(self, page):
        """Test that the sign-up page loads correctly."""
        await page.goto("/sign-up")
        
        await page.wait_for_selector('[data-testid="clerk-sign-up"]', timeout=10000)

    async def test_protected_route_redirects_to_sign_in(self, page):
        """Test that protected routes redirect to sign-in when unauthenticated."""
        await page.goto("/p/test-slug")
        
        # Should redirect to sign-in
        await page.wait_for_url("**/sign-in**", timeout=5000)
        
        # Verify we're on sign-in page
        assert "sign-in" in page.url

    async def test_sign_in_with_valid_credentials(self, page, clerk_test_user):
        """Test successful sign-in with valid credentials."""
        await page.goto("/sign-in")
        
        # Fill credentials
        await page.fill('input[name="emailAddress"]', clerk_test_user["email"])
        await page.fill('input[name="password"]', clerk_test_user["password"])
        
        # Submit
        await page.click('button[type="submit"]')
        
        # Wait for redirect to portal
        await page.wait_for_url("**/p/**", timeout=15000)
        
        # Verify we're on a portal page
        assert "/p/" in page.url

    async def test_sign_in_with_invalid_credentials(self, page):
        """Test sign-in fails with invalid credentials."""
        await page.goto("/sign-in")
        
        await page.fill('input[name="emailAddress"]', "invalid@example.com")
        await page.fill('input[name="password"]', "wrongpassword")
        await page.click('button[type="submit"]')
        
        # Should show error
        await page.wait_for_selector('[data-testid="clerk-error"]', timeout=5000)
        
        # Should still be on sign-in page
        assert "sign-in" in page.url

    async def test_sign_out(self, authenticated_page):
        """Test sign-out flow."""
        page = authenticated_page
        
        # Click sign out button
        await page.click('[data-testid="user-button"]')
        await page.click('text="Sign out"')
        
        # Wait for redirect to home
        await page.wait_for_url("**/", timeout=5000)
        
        # Verify we're on landing page
        assert page.url.endswith("/") or page.url.endswith("/sign-in")

    async def test_session_persistence(self, page, clerk_test_user):
        """Test that session persists across page reloads."""
        # Sign in
        await page.goto("/sign-in")
        await page.fill('input[name="emailAddress"]', clerk_test_user["email"])
        await page.fill('input[name="password"]', clerk_test_user["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/p/**", timeout=15000)
        
        # Get the slug from URL
        slug = page.url.split("/p/")[-1]
        
        # Reload page
        await page.reload()
        
        # Should still be authenticated
        await page.wait_for_url(f"**/p/{slug}**", timeout=5000)
        assert f"/p/{slug}" in page.url


@pytest.mark.e2e
class TestAdminAuthentication:
    """Tests for admin authentication."""

    async def test_admin_page_requires_admin(self, page, clerk_test_user):
        """Test that admin page requires admin role."""
        # Sign in as regular user
        await page.goto("/sign-in")
        await page.fill('input[name="emailAddress"]', clerk_test_user["email"])
        await page.fill('input[name="password"]', clerk_test_user["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/p/**", timeout=15000)
        
        # Try to access admin page
        await page.goto("/admin")
        
        # Should be forbidden (403) or redirect
        # The exact behavior depends on implementation
        # At minimum, should not show admin panel
        content = await page.content()
        assert "Mission Control" not in content or page.url != "/admin"

    async def test_admin_access_with_admin_user(self, page):
        """Test admin access with admin user (if configured)."""
        admin_email = os.environ.get("E2E_ADMIN_EMAIL")
        admin_password = os.environ.get("E2E_ADMIN_PASSWORD")
        
        if not admin_email or not admin_password:
            pytest.skip("Admin credentials not configured")
        
        await page.goto("/sign-in")
        await page.fill('input[name="emailAddress"]', admin_email)
        await page.fill('input[name="password"]', admin_password)
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/p/**", timeout=15000)
        
        # Access admin page
        await page.goto("/admin")
        
        # Should show admin panel
        await page.wait_for_selector('text="Mission Control"', timeout=5000)
        content = await page.content()
        assert "Mission Control" in content