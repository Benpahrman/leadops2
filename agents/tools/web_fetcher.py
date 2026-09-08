"""Live Web Page Fetcher and Contact Extraction Tool for LeadOps AI Agents.

Extracts text, metadata, email addresses, telephone numbers, and tables
from corporate websites and target data portals.
"""

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse
import httpx

from .waf_prober import generate_browser_headers

logger = logging.getLogger("tools.web_fetcher")


def fetch_page_content(url: str, timeout: float = 6.0) -> dict[str, Any]:
    """Fetch raw HTML content with browser headers and extract structured metadata."""
    logger.info(f"🌐 [WEB FETCHER TOOL] Fetching live URL: {url}")
    headers = generate_browser_headers(url)
    
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            status_code = resp.status_code
            html = resp.text
            
            # Extract basic metadata
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            
            # Extract meta description
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
            meta_desc = desc_match.group(1).strip() if desc_match else ""
            
            # Extract mailto links
            mailto_matches = re.findall(r'href=["\']mailto:([^"\'?]+)', html, re.IGNORECASE)
            # Extract emails from text and mailto links
            email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
            all_raw_emails = list(set(re.findall(email_pattern, html) + mailto_matches))
            clean_emails = [
                e.strip().lower() for e in all_raw_emails
                if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff', '.woff2'))
                and "example" not in e.lower() and "w3.org" not in e.lower() and "schema.org" not in e.lower()
            ]

            # Extract tel links and phone patterns
            tel_matches = re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.IGNORECASE)
            clean_tels = [re.sub(r'[^0-9+()\-.\s]', '', t).strip() for t in tel_matches if len(t.strip()) >= 10]
            phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = list(set(clean_tels + re.findall(phone_pattern, html)))

            # Extract Schema.org JSON-LD LocalBusiness metadata
            schema_meta = {}
            for json_str in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE):
                try:
                    import json
                    parsed_json = json.loads(json_str.strip())
                    items = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                    for item in items:
                        if isinstance(item, dict):
                            if "@graph" in item and isinstance(item["@graph"], list):
                                items.extend(item["@graph"])
                            t = str(item.get("@type", "")).lower()
                            if any(k in t for k in ["business", "service", "contractor", "legal", "organization", "corporation"]):
                                if item.get("telephone"):
                                    phones.insert(0, str(item["telephone"]))
                                if item.get("email"):
                                    clean_emails.insert(0, str(item["email"]).lower())
                                if item.get("name"):
                                    schema_meta["business_name"] = str(item["name"])
                                if item.get("address") and isinstance(item["address"], dict):
                                    schema_meta["address"] = f"{item['address'].get('addressLocality', '')}, {item['address'].get('addressRegion', '')}".strip(", ")
                except Exception:
                    pass

            # Clean body text
            body_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            body_clean = re.sub(r'<style[^>]*>.*?</style>', '', body_clean, flags=re.DOTALL | re.IGNORECASE)
            body_clean = re.sub(r'<[^>]+>', ' ', body_clean)
            body_clean = re.sub(r'\s+', ' ', body_clean).strip()

            logger.info(f"✓ [WEB FETCHER TOOL] Successfully fetched {url} (HTTP {status_code}, {len(clean_emails)} emails, {len(phones)} phones)")
            return {
                "ok": True,
                "url": str(resp.url),
                "status_code": status_code,
                "title": title,
                "description": meta_desc,
                "emails": clean_emails[:8],
                "phones": phones[:4],
                "schema_meta": schema_meta,
                "content_snippet": body_clean[:3000],
                "raw_html": html[:25000],
            }
    except Exception as e:
        logger.warning(f"Web fetcher failed on {url}: {e}")
        return {
            "ok": False,
            "url": url,
            "status_code": 500,
            "error": str(e),
            "title": "",
            "description": "",
            "emails": [],
            "phones": [],
            "schema_meta": {},
            "content_snippet": "",
            "raw_html": "",
        }


def extract_contact_info_from_url(website_url: str) -> dict[str, Any]:
    """Deep scan root, contact paths, and team/leadership pages to extract verified SMB contacts & decision makers."""
    base_result = fetch_page_content(website_url)
    all_emails = list(base_result.get("emails", []))
    all_phones = list(base_result.get("phones", []))
    schema_meta = dict(base_result.get("schema_meta", {}))
    decision_makers: list[dict[str, str]] = []

    subpaths = [
        "/contact", "/contact-us", "/about", "/about-us",
        "/our-team", "/team", "/leadership", "/attorneys",
        "/partners", "/staff", "/people", "/get-in-touch"
    ]

    for path in subpaths:
        if len(all_emails) >= 2 and len(decision_makers) >= 1:
            break
        sub_url = urljoin(website_url, path)
        sub_res = fetch_page_content(sub_url, timeout=3.5)
        if sub_res.get("ok"):
            all_emails.extend(sub_res.get("emails", []))
            all_phones.extend(sub_res.get("phones", []))
            if sub_res.get("schema_meta"):
                schema_meta.update(sub_res["schema_meta"])

            # Scan page snippet for executive decision maker names & titles
            snippet = sub_res.get("content_snippet", "")
            roles = [
                "Managing Partner", "President", "Founder", "Co-Founder",
                "Principal", "Owner", "Chief Executive Officer", "CEO",
                "Director of Operations", "Operations Director", "Vice President",
                "General Counsel", "Managing Director"
            ]
            for role in roles:
                # Match pattern: "John Smith - President" or "President: John Smith"
                pattern1 = rf'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,2}})\s*[-:—,\|]\s*(?:{role})'
                pattern2 = rf'(?:{role})\s*[-:—,\|]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,2}})'
                for m in re.finditer(pattern1, snippet):
                    name = m.group(1).strip()
                    if name and not any(d["name"] == name for d in decision_makers) and len(name.split()) <= 3:
                        decision_makers.append({"name": name, "role": role})
                for m in re.finditer(pattern2, snippet):
                    name = m.group(1).strip()
                    if name and not any(d["name"] == name for d in decision_makers) and len(name.split()) <= 3:
                        decision_makers.append({"name": name, "role": role})

    parsed = urlparse(website_url)
    domain_name = parsed.netloc.replace("www.", "")
    
    # Filter emails matching company domain as highest priority
    company_domain_emails = [e for e in all_emails if domain_name and domain_name in e]
    general_clean_emails = [e for e in all_emails if "noreply" not in e and "privacy" not in e and "support" not in e]
    
    verified_email = (
        company_domain_emails[0]
        if company_domain_emails
        else (general_clean_emails[0] if general_clean_emails else (all_emails[0] if all_emails else ""))
    )

    return {
        "website": website_url,
        "verified_email": verified_email,
        "all_emails": list(dict.fromkeys(company_domain_emails + general_clean_emails + all_emails)),
        "verified_phone": all_phones[0] if all_phones else "",
        "all_phones": list(dict.fromkeys(all_phones)),
        "title": base_result.get("title", ""),
        "business_name": schema_meta.get("business_name", ""),
        "address": schema_meta.get("address", ""),
        "decision_makers": decision_makers[:3],
    }


def extract_portal_sample_data(url: str, max_records: int = 25) -> dict[str, Any]:
    """Fetch live data portal URL and parse structured sample records directly from live HTML tables or JSON endpoints."""
    import json
    from .dom_pruner import prune_dom
    
    logger.info(f"📊 [PORTAL SAMPLER TOOL] Extracting real sample data from: {url}")
    result = fetch_page_content(url, timeout=8.0)
    if not result.get("ok"):
        return {"ok": False, "records": [], "fields": [], "source_url": url, "error": result.get("error")}
    
    html = result.get("raw_html", "")
    
    # 1. Check if response is raw JSON (e.g., Open Data Socrata/CKAN APIs)
    try:
        data = json.loads(html)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            records = data[:max_records]
            fields = list(records[0].keys())
            return {"ok": True, "records": records, "fields": fields, "source_url": url, "record_count": len(records)}
    except Exception as exc:
        logger.debug(f"Response is not direct JSON payload: {exc}")
        
    # 2. Parse HTML tables via DOM pruner
    parsed = prune_dom(html)
    tables = parsed.get("tables", [])
    if tables and tables[0].get("rows"):
        primary_table = tables[0]
        records = primary_table["rows"][:max_records]
        fields = primary_table.get("headers", [])
        return {"ok": True, "records": records, "fields": fields, "source_url": url, "record_count": len(records)}
    
    return {
        "ok": True,
        "records": [],
        "fields": [],
        "source_url": url,
        "content_snippet": parsed.get("clean_text", "")[:1000],
    }

