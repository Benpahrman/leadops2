#!/usr/bin/env python3
"""Audit DNS records for olfmailer.com via Cloudflare API and live DNS resolution."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import dns.resolver
from dotenv import load_dotenv
from scripts.setup_cloudflare_olfmailer import CloudflareManager

load_dotenv()

def audit_cloudflare_dns():
    print("============================================================")
    print("CLOUDFLARE ZONE DNS RECORDS (olfmailer.com)")
    print("============================================================")
    cf = CloudflareManager()
    records = cf.list_dns_records()
    print(f"Total Records Configured: {len(records)}\n")
    for r in sorted(records, key=lambda x: (x['type'], x['name'])):
        t = r.get("type", "")
        name = r.get("name", "")
        content = r.get("content", "")
        prio = r.get("priority")
        prio_str = f" [Priority: {prio}]" if prio is not None else ""
        proxied = " [Proxied via Cloudflare]" if r.get("proxied") else " [DNS Only]"
        print(f"  {t:6} | {name:32} | {content}{prio_str}{proxied}")
    print()

def audit_public_dns():
    print("============================================================", flush=True)
    print("LIVE PUBLIC DNS RESOLUTION VIA CLOUDFLARE DoH (olfmailer.com)", flush=True)
    print("============================================================", flush=True)
    import urllib.request
    import json

    def doh_query(name: str, rtype: str) -> list[str]:
        try:
            req = urllib.request.Request(
                f"https://cloudflare-dns.com/dns-query?name={name}&type={rtype}",
                headers={"Accept": "application/dns-json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return [ans.get("data", "") for ans in data.get("Answer", [])]
        except Exception as e:
            return [f"Error: {e}"]

    # 1. MX Records
    print("\n--- MX Records ---", flush=True)
    for ans in doh_query("olfmailer.com", "MX"):
        print(f"  MX: {ans}", flush=True)

    # 2. TXT / SPF Records
    print("\n--- TXT / SPF Records ---", flush=True)
    for ans in doh_query("olfmailer.com", "TXT"):
        print(f"  TXT: {ans}", flush=True)

    # 3. DMARC Record
    print("\n--- DMARC (_dmarc.olfmailer.com) ---", flush=True)
    for ans in doh_query("_dmarc.olfmailer.com", "TXT"):
        print(f"  DMARC: {ans}", flush=True)

    # 4. DKIM Record
    print("\n--- DKIM (cf2024-1._domainkey.olfmailer.com) ---", flush=True)
    for ans in doh_query("cf2024-1._domainkey.olfmailer.com", "TXT"):
        print(f"  DKIM: {ans}", flush=True)

    # 4. Email Routing / MX
    print("\n--- Cloudflare Email Routing Status ---")
    try:
        cf = CloudflareManager()
        status_res = cf._request(f"/zones/{cf.zone_id}/email/routing")
        status = status_res.get("result", {})
        print(f"  Routing Enabled: {status.get('enabled')}")
        rules_res = cf._request(f"/zones/{cf.zone_id}/email/routing/rules")
        rules = rules_res.get("result", [])
        print(f"  Routing Rules ({len(rules)}):")
        for rule in rules:
            print(f"    - Name: {rule.get('name')} | Status: {'Enabled' if rule.get('enabled') else 'Disabled'} | Action: {rule.get('actions')}")
        dests = cf.list_destinations()
        print(f"  Destinations ({len(dests)}):")
        for d in dests:
            print(f"    - Email: {d.get('email')} | Verified: {d.get('verified')}")
    except Exception as e:
        print(f"  Routing check error: {e}")

if __name__ == "__main__":
    audit_cloudflare_dns()
    audit_public_dns()
