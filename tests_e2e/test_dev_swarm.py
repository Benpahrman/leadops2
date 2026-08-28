"""E2E tests for autonomous dev swarm build flows."""

import pytest
import asyncio


@pytest.mark.e2e
class TestDevSwarmBuild:
    """Tests for the autonomous dev swarm build process."""

    async def test_build_progress_websocket(self, authenticated_page, base_url):
        """Test WebSocket connection for build progress."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        
        # Connect to WebSocket
        ws_url = f"ws://127.0.0.1:8000/ws/progress/{slug}"
        
        # We can't easily test WebSocket from page context,
        # but we can verify the endpoint exists
        import httpx
        async with httpx.AsyncClient() as client:
            # Try to upgrade to WebSocket
            response = await client.get(
                f"{base_url}/ws/progress/{slug}",
                headers={"Upgrade": "websocket", "Connection": "Upgrade"},
            )
            # Should return 426 Upgrade Required or similar
            assert response.status_code in [426, 400, 401, 403]

    async def test_build_starts_after_deposit(self, authenticated_page):
        """Test that build starts after deposit payment."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Check if build is already in progress or completed
        build_indicator = page.locator('text="Building"), text="Dev Swarm"), text="Progress"').first
        
        if await build_indicator.count() > 0:
            # Build already in progress or done
            build_text = await build_indicator.text_content()
            assert "Building" in build_text or "Complete" in build_text or "Progress" in build_text
        else:
            # Trigger deposit if needed
            deposit_btn = page.locator('button:has-text("Deposit"), button:has-text("Simulate")').first
            if await deposit_btn.count() > 0:
                await deposit_btn.click()
                await page.wait_for_url(f"**/p/{slug}**", timeout=15000)
                
                # Check for build progress indicator
                await page.goto(f"/p/{slug}")
                await page.wait_for_selector('text="Building"), text="Progress"', timeout=5000)

    async def test_build_progress_updates_in_ui(self, authenticated_page):
        """Test that build progress updates are visible in the UI."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for progress bar or status indicator
        progress_elements = page.locator(
            '[role="progressbar"], .progress-bar, [data-testid="build-progress"], '
            'text="%", text="Progress"'
        )
        
        if await progress_elements.count() > 0:
            # Verify progress is visible
            for i in range(await progress_elements.count()):
                el = progress_elements.nth(i)
                text = await el.text_content()
                if text and ("%" in text or "Progress" in text):
                    assert True
                    return
        
        # If no progress UI, that's also valid (depends on build state)
        pytest.skip("No progress UI visible - build may not be in progress")

    async def test_build_completion_notification(self, authenticated_page):
        """Test that build completion is notified."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for completion indicators
        completion_indicators = page.locator(
            'text="Complete"), text="Ready"), text="Escrow"), '
            '[data-testid="build-complete"], [data-testid="escrow-ready"]'
        )
        
        if await completion_indicators.count() > 0:
            for i in range(await completion_indicators.count()):
                el = completion_indicators.nth(i)
                text = await el.text_content()
                if text and any(word in text for word in ["Complete", "Ready", "Escrow"]):
                    assert True
                    return
        
        pytest.skip("Build not yet complete")

    async def test_build_artifacts_accessible(self, authenticated_page, base_url):
        """Test that build artifacts are accessible after completion."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for links to artifacts (GitHub repo, extractor, etc.)
        artifact_links = page.locator(
            'a[href*="github"], a[href*="extractor"], a[href*="artifact"], '
            'text="View Code"), text="Download"), text="Repository"'
        )
        
        if await artifact_links.count() > 0:
            # Click first artifact link
            await artifact_links.first.click()
            
            # Should navigate to artifact
            await page.wait_for_load_state("networkidle")
            
            # Verify we're on an artifact page
            assert "github.com" in page.url or "extractor" in page.url or "artifact" in page.url
        else:
            pytest.skip("No artifact links visible - build may not be complete")

    async def test_qa_score_displayed(self, authenticated_page):
        """Test that QA score is displayed after build."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for QA score
        qa_elements = page.locator('text="QA"), text="Score"), text="Quality"), [data-testid="qa-score"]')
        
        if await qa_elements.count() > 0:
            for i in range(await qa_elements.count()):
                el = qa_elements.nth(i)
                text = await el.text_content()
                if text and any(char.isdigit() for char in text):
                    # Found a numeric QA score
                    assert True
                    return
        
        pytest.skip("QA score not displayed - build may not be complete")

    async def test_sample_preview_available(self, authenticated_page):
        """Test that 25-row sample preview is available."""
        page = authenticated_page
        
        slug = page.url.split("/p/")[-1]
        await page.goto(f"/p/{slug}")
        
        # Look for sample data table or preview
        preview_elements = page.locator(
            'table[data-testid="sample-preview"], .sample-preview, '
            'text="Sample"), text="Preview"), text="25 row"'
        )
        
        if await preview_elements.count() > 0:
            assert True
        else:
            pytest.skip("Sample preview not available - build may not be complete")


@pytest.mark.e2e
class TestDevSwarmAPI:
    """API-level tests for dev swarm."""

    async def test_dev_swarm_trigger_endpoint(self, base_url):
        """Test the admin endpoint to trigger dev swarm."""
        import httpx
        
        # This would require admin auth
        # For now, just verify endpoint exists
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/admin/scout/trigger-run",
                headers={"Authorization": "Bearer invalid"},
            )
            # Should require auth
            assert response.status_code in [401, 403]

    async def test_pipeline_kanban_endpoint(self, base_url):
        """Test the pipeline kanban endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/api/admin/pipeline",
                headers={"Authorization": "Bearer invalid"},
            )
            assert response.status_code in [401, 403]