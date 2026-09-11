"""Automated Cloudflare Edge Proxy Worker Deployer.

Deploys infra/cloudflare/proxy_worker.js to Cloudflare Workers using the REST API.
"""

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
SCRIPT_NAME = "leadops-edge-proxy"


def deploy_worker() -> str | None:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        print("[ERROR] Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN in .env")
        return None

    worker_file = Path(__file__).resolve().parent.parent / "infra" / "cloudflare" / "proxy_worker.js"
    if not worker_file.exists():
        print(f"[ERROR] Worker file not found at {worker_file}")
        return None

    script_content = worker_file.read_text(encoding="utf-8")

    # Cloudflare Workers API endpoint
    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{SCRIPT_NAME}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/javascript",
    }

    print(f"Deploying {SCRIPT_NAME} to Cloudflare Account {CLOUDFLARE_ACCOUNT_ID}...")
    resp = requests.put(endpoint, headers=headers, data=script_content.encode("utf-8"))
    
    if resp.status_code in (200, 201):
        data = resp.json()
        print("[SUCCESS] Cloudflare Worker deployed successfully!")
        # Enable workers.dev subdomain route
        subdomain_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{SCRIPT_NAME}/subdomain"
        requests.post(subdomain_endpoint, headers=headers, json={"enabled": True})
        return SCRIPT_NAME
    else:
        print(f"[NOTE] API Upload status HTTP {resp.status_code}: {resp.text}")
        print("\n=== Easy 1-Minute Alternative: Cloudflare Dashboard ===")
        print("1. Log into https://dash.cloudflare.com/")
        print("2. Navigate to 'Workers & Pages' -> 'Create application' -> 'Create Worker'")
        print(f"3. Name it '{SCRIPT_NAME}' and paste infra/cloudflare/proxy_worker.js")
        print("4. Click 'Deploy' and copy your worker URL to CLOUDFLARE_EDGE_PROXY_URL in .env")
        return None


if __name__ == "__main__":
    deploy_worker()
