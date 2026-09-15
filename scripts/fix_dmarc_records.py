#!/usr/bin/env python3
"""Clean up stale IONOS records and install standard DMARC TXT record for olfmailer.com."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv()

from scripts.setup_cloudflare_olfmailer import CloudflareManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def fix_dns():
    cf = CloudflareManager()
    records = cf.list_dns_records()
    print("Auditing existing DNS records before cleanup...")

    # 1. Remove stale IONOS CNAME records and broken CNAME _dmarc
    for r in records:
        content = r.get("content", "").lower()
        name = r.get("name", "").lower()
        if "ionos" in content or name == "_dmarc.olfmailer.com":
            print(f"  [DELETE] [{r.get('type')}] {r.get('name')} -> {r.get('content')}")
            cf._request(f"/zones/{cf.zone_id}/dns_records/{r.get('id')}", method="DELETE")

    # 2. Add proper standard DMARC TXT record (DNS Only)
    dmarc_content = "v=DMARC1; p=none; sp=none; rua=mailto:dmarc-reports@olfmailer.com; aspf=r; adkim=r"
    res = cf.create_or_update_record(
        record_type="TXT",
        name="_dmarc.olfmailer.com",
        content=dmarc_content,
        ttl=1,
        proxied=False,
    )
    print(f"  [OK] DMARC TXT record installed: {res.get('success')}")

    # 3. Print updated clean list
    updated = cf.list_dns_records()
    print("\nUpdated Cloudflare DNS Table for olfmailer.com:")
    for r in sorted(updated, key=lambda x: (x['type'], x['name'])):
        prio = f" (prio={r.get('priority')})" if r.get('priority') is not None else ""
        proxied = " [Proxied]" if r.get('proxied') else " [DNS Only]"
        print(f"  {r.get('type'):6} | {r.get('name'):32} | {r.get('content')}{prio}{proxied}")

if __name__ == "__main__":
    fix_dns()
