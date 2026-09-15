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
    print("============================================================")
    print("PUBLIC LIVE DNS RESOLUTION (olfmailer.com)")
    print("============================================================")
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]

    # 1. MX Records
    print("\n--- MX Records ---")
    try:
        answers = resolver.resolve("olfmailer.com", "MX")
        for rdata in answers:
            print(f"  MX preference: {rdata.preference} -> {rdata.exchange}")
    except Exception as e:
        print(f"  MX lookup error: {e}")

    # 2. TXT / SPF Records
    print("\n--- TXT / SPF Records ---")
    try:
        answers = resolver.resolve("olfmailer.com", "TXT")
        for rdata in answers:
            txt = "".join([s.decode() if isinstance(s, bytes) else str(s) for s in rdata.strings])
            print(f"  TXT: {txt}")
    except Exception as e:
        print(f"  TXT lookup error: {e}")

    # 3. DMARC Record
    print("\n--- DMARC (_dmarc.olfmailer.com) ---")
    try:
        answers = resolver.resolve("_dmarc.olfmailer.com", "TXT")
        for rdata in answers:
            txt = "".join([s.decode() if isinstance(s, bytes) else str(s) for s in rdata.strings])
            print(f"  DMARC: {txt}")
    except Exception as e:
        print(f"  DMARC lookup error: {e}")

    # 4. Email Routing / MX
    print("\n--- Cloudflare Email Routing Status ---")
    try:
        cf = CloudflareManager()
        status = cf.get_email_routing_status()
        print(f"  Routing Enabled: {status.get('enabled')}")
        rules = cf.get_routing_rules()
        print(f"  Routing Rules ({len(rules)}):")
        for rule in rules:
            print(f"    - Name: {rule.get('name')} | Status: {rule.get('status')} | Match: {rule.get('matchers')} -> Action: {rule.get('actions')}")
        dests = cf.list_destination_addresses()
        print(f"  Destinations ({len(dests)}):")
        for d in dests:
            print(f"    - Email: {d.get('email')} | Verified: {d.get('verified')}")
    except Exception as e:
        print(f"  Routing check error: {e}")

if __name__ == "__main__":
    audit_cloudflare_dns()
    audit_public_dns()
