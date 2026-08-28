import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def test_harris_probate_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate"
        print(f"Navigating to {url}...")
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # Calculate date range (last 14 days)
        today = datetime.now()
        from_date = (today - timedelta(days=14)).strftime("%m/%d/%Y")
        to_date = today.strftime("%m/%d/%Y")
        print(f"Submitting filing search from {from_date} to {to_date}...")
        
        # Fill date inputs
        await page.fill("input[name*='txtFrom']", from_date)
        await page.fill("input[name*='txtTo']", to_date)
        
        # Click search
        search_btn = await page.query_selector("input[name*='btnSearch']")
        if search_btn:
            await search_btn.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            
        # Inspect results table
        tables = await page.query_selector_all("table")
        print(f"Found {len(tables)} tables after search submission.")
        
        rows = await page.query_selector_all("table tr")
        print(f"Found {len(rows)} table rows.")
        for r in rows[:10]:
            tds = await r.query_selector_all("td, th")
            texts = [await td.inner_text() for td in tds]
            if any(texts):
                print("ROW:", [t.strip() for t in texts if t.strip()])
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_harris_probate_search())
