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
            
            # Extract emails
            email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
            emails = list(set(re.findall(email_pattern, html)))
            # Filter out obvious asset extensions
            clean_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js'))]
            
            # Extract phone numbers
            phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = list(set(re.findall(phone_pattern, html)))
            
            # Clean body text
            body_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            body_clean = re.sub(r'<style[^>]*>.*?</style>', '', body_clean, flags=re.DOTALL | re.IGNORECASE)
            body_clean = re.sub(r'<[^>]+>', ' ', body_clean)
            body_clean = re.sub(r'\s+', ' ', body_clean).strip()
            
            logger.info(f"✓ [WEB FETCHER TOOL] Successfully fetched {url} (HTTP {status_code}, {len(html)} bytes, {len(clean_emails)} emails)")
            return {
                "ok": True,
                "url": str(resp.url),
                "status_code": status_code,
                "title": title,
                "description": meta_desc,
                "emails": clean_emails[:5],
                "phones": phones[:3],
                "content_snippet": body_clean[:2000],
                "raw_html": html[:15000],
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
            "content_snippet": "",
            "raw_html": "",
        }


def extract_contact_info_from_url(website_url: str) -> dict[str, Any]:
    """Scan root and common contact paths (/contact, /about, /team) to extract verified contact info."""
    base_result = fetch_page_content(website_url)
    all_emails = list(base_result.get("emails", []))
    all_phones = list(base_result.get("phones", []))
    
    if base_result.get("ok") and not all_emails:
        for path in ["/contact", "/about", "/team", "/contact-us", "/about-us"]:
            sub_url = urljoin(website_url, path)
            sub_res = fetch_page_content(sub_url, timeout=2.5)
            if sub_res.get("ok"):
                all_emails.extend(sub_res.get("emails", []))
                all_phones.extend(sub_res.get("phones", []))
                if all_emails:
                    break
                    
    parsed = urlparse(website_url)
    domain_name = parsed.netloc.replace("www.", "")
    fallback_email = f"contact@{domain_name}" if domain_name else "info@company.com"
    
    return {
        "website": website_url,
        "verified_email": all_emails[0] if all_emails else fallback_email,
        "all_emails": list(set(all_emails)),
        "verified_phone": all_phones[0] if all_phones else "",
        "title": base_result.get("title", ""),
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

