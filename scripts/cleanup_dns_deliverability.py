#!/usr/bin/env python3
"""Cleanup and align Cloudflare DNS records for 100% email deliverability."""

import json
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from scripts.setup_cloudflare_olfmailer import CloudflareManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("leadops.deliverability")

TARGET_SPF = "v=spf1 include:_spf.google.com include:_spf.mx.cloudflare.net include:spfa.protection.outlook.com ~all"
TARGET_DMARC = "v=DMARC1; p=quarantine; sp=quarantine; rua=mailto:dmarc@olfmailer.com,mailto:admin@olfmailer.com; aspf=r; adkim=r"
TARGET_DESTINATION = "omnileadfeeder.tech@gmail.com"

def enforce_clean_deliverability():
    cf = CloudflareManager()
    records = cf.list_dns_records()
    logger.info(f"Loaded {len(records)} total DNS records from Cloudflare zone.")

    # 1. Clean up duplicate or malformed SPF records
    spf_records = [r for r in records if r["type"] == "TXT" and "v=spf1" in r.get("content", "")]
    logger.info(f"Found {len(spf_records)} SPF record(s)")

    for r in spf_records:
        cleaned_content = r["content"].strip("\"'")
        if cleaned_content != TARGET_SPF:
            logger.info(f"Deleting stale/duplicate SPF record ID {r['id']}: {cleaned_content}")
            cf._request(f"/zones/{cf.zone_id}/dns_records/{r['id']}", method="DELETE")

    # Ensure the single target SPF record exists
    cf.create_or_update_record(
        record_type="TXT",
        name="olfmailer.com",
        content=TARGET_SPF,
    )

    # 2. Enforce clean DMARC record
    dmarc_records = [r for r in records if r["type"] == "TXT" and r["name"].startswith("_dmarc")]
    for r in dmarc_records:
        cleaned_content = r["content"].strip("\"'")
        if "christopher.ben.pahrman" in cleaned_content:
            logger.info(f"Deleting stale DMARC record ID {r['id']} containing burnt address")
            cf._request(f"/zones/{cf.zone_id}/dns_records/{r['id']}", method="DELETE")

    cf.create_or_update_record(
        record_type="TXT",
        name="_dmarc.olfmailer.com",
        content=TARGET_DMARC,
    )

    # 3. Ensure Cloudflare Email Routing Catch-all rule is set to active destination
    cf.set_explicit_forwarding(destination_email=TARGET_DESTINATION)

    # 4. Final verification of active records
    updated_records = cf.list_dns_records()
    print("\n============================================================")
    print("FINAL CLOUDFLARE DNS STATUS FOR olfmailer.com")
    print("============================================================")
    for r in sorted(updated_records, key=lambda x: (x["type"], x["name"])):
        prio = f" [Priority: {r.get('priority')}]" if r.get("priority") is not None else ""
        print(f"  {r['type']:6} | {r['name']:32} | {r['content']}{prio}")

if __name__ == "__main__":
    enforce_clean_deliverability()
