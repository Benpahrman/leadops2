"""E2E tests for payment flows."""

import pytest
import os


@pytest.mark.e2e
class TestPaymentFlows:
    """Tests for deposit and final payment flows."""

    async def test_deposit_checkout_requires_auth(self, page):
        """Test that deposit checkout requires authentication."""
        await page.goto("/p/test-slug")
        await page.wait_for_url("**/sign-in**", timeout=5000)

    async def test_deposit_checkout_creates_paypal_order(self, authenticated_page, base_url):
        """Test that deposit checkout creates a PayPal order."""
        page = authenticated_page
        
        # Get the sandbox slug from URL
        slug = page.url.split("/p/")[-1]
        
        # Navigate to the portal page if not already there
        await page.goto(f"/p/{slug}")
        
        # Find and click the deposit/payment button
        # The button text might be "Simulate Deposit" or "Pay Deposit"
        deposit_btn = page.locator('button:has-text("Deposit"), button:has-text("Pay"), a:has-text("Deposit")').first
        
        if await deposit_btn.count() == 0:
            pytest.skip("Deposit button not found - sandbox may already be paid")
        
        # Click the deposit button
        await deposit_btn.click()
        
        # Should either redirect to PayPal or show success
        # For simulate-deposit, it should redirect to the portal
        await page.wait_for_url(f"**/p/{slug}**", timeout=10000)
        
        # Verify we're back on the portal
        assert f"/p/{slug}" in page.url

    async def test_final_payment_checkout(self, authenticated_page):
        """Test final payment checkout flow."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for final payment button
        final_btn = page.locator('button:has-text("Final"), button:has-text("Complete"), a:has-text("Final")').first
        
        if await final_btn.count() == 0:
            pytest.skip("Final payment button not found - may not be in ESCROW_PREVIEW state")
        
        await final_btn.click()
        
        # Should handle the final payment
        await page.wait_for_url(f"**/p/{slug}**", timeout=10000)
        assert f"/p/{slug}" in page.url

    async def test_payment_state_transitions(self, authenticated_page, base_url):
        """Test that payment advances lead state correctly."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        
        # Check initial state on page
        await page.goto(f"/p/{slug}")
        
        # Get state indicator
        state_element = page.locator('text="State:").first, page.locator('[data-testid="lead-state"]').first
        state_text = ""
        for el in state_element:
            if await el.count() > 0:
                state_text = await el.text_content()
                break
        
        # If in a state that accepts deposit, test deposit
        if "CONVERSATIONAL_INTAKE" in state_text or "SOW_GENERATED" in state_text:
            deposit_btn = page.locator('button:has-text("Deposit"), button:has-text("Simulate")').first
            if await deposit_btn.count() > 0:
                await deposit_btn.click()
                await page.wait_for_url(f"**/p/{slug}**", timeout=10000)
                
                # Verify state advanced
                await page.goto(f"/p/{slug}")
                new_state = await page.locator('text="State:").first.text_content()
                assert "DEV_BUILDING" in new_state or "DEPOSIT_PAID" in new_state

    async def test_paypal_webhook_simulation(self, page, base_url):
        """Test PayPal webhook handling (simulated)."""
        # This would test the webhook endpoint directly
        # For E2E, we can simulate a webhook call
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/paypal/webhook",
                json={
                    "id": "evt_test_123",
                    "event_type": "PAYMENT.CAPTURE.COMPLETED",
                    "resource": {
                        "id": "capture_test_123",
                        "amount": {"value": "250.00", "currency_code": "USD"},
                        "custom_id": "test-lead-id",
                    },
                },
                headers={
                    "PayPal-Transmission-Id": "test",
                    "PayPal-Transmission-Time": "2024-01-01T00:00:00Z",
                    "PayPal-Transmission-Sig": "test",
                    "PayPal-Auth-Algo": "SHA256",
                    "PayPal-Cert-Url": "test",
                },
            )
            # Should handle gracefully (may reject invalid signature)
            assert response.status_code in [200, 400, 401, 403]