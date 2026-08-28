# Lone Star Asset Recovery - Autonomous Data Extractor
> Target Registry: [https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate](https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate)  
> Extraction Tier: Daily Sync ($500/mo)

## Features
- **Standalone Execution**: Zero cloud vendor lock-in. Runs locally or on GitHub Actions.
- **Built-in Delivery**: Automatically exports to `output/latest.json`, `output/latest.csv`, timestamped runs in `runs/`, and dispatches to HTTP Webhooks.
- **Stealth & Anti-Bot**: Masked `navigator.webdriver`, spoofed WebGL signatures, and rotating proxy pool support.
- **Automated Form Handling**: Automatic date-range queries against target registry databases.

## Local Execution
```bash
pip install -r requirements.txt
playwright install chromium
python extractor.py
```

## GitHub Actions Deployment
1. Push this folder to your GitHub repository.
2. Add your secrets under **Settings > Secrets and variables > Actions**:
   - `SCRAPER_PROXY_URL` (optional proxy pool URL)
   - `WEBHOOK_URL` (optional HTTP webhook endpoint)
   - `WEBHOOK_SECRET` (optional HMAC header secret)
3. The workflow `.github/workflows/daily_sync.yml` will automatically execute on schedule!
