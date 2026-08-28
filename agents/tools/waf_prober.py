"""WAF prober and anti-bot header generator for compliant, resilient requests."""

import random
from typing import Any
from urllib.parse import urlparse


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def generate_browser_headers(target_url: str | None = None) -> dict[str, str]:
    """Generate realistic browser headers including sec-ch-ua and referer."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    if "Chrome" in ua:
        headers["sec-ch-ua"] = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'
        headers["sec-ch-ua-mobile"] = "?0"
        headers["sec-ch-ua-platform"] = '"Windows"' if "Windows" in ua else '"macOS"'

    if target_url:
        parsed = urlparse(target_url)
        headers["Host"] = parsed.netloc
        headers["Sec-Fetch-Site"] = "same-origin"

    return headers


def probe_waf_signatures(headers: dict[str, str], body_text: str, status_code: int = 200) -> dict[str, Any]:
    """Analyze response headers and body to detect WAF / anti-bot mechanisms.
    
    Detects Cloudflare, Akamai, Datadome, PerimeterX, AWS WAF, Imperva, etc.
    """
    normalized_headers = {k.lower(): v.lower() for k, v in headers.items()}
    lower_body = body_text.lower()
    
    detected_waf = None
    waf_confidence = "none"
    blocked = False
    
    if "cf-ray" in normalized_headers or "cloudflare" in normalized_headers.get("server", ""):
        detected_waf = "Cloudflare"
        waf_confidence = "high"
    elif "x-amz-cf-id" in normalized_headers or "cloudfront" in normalized_headers.get("via", ""):
        detected_waf = "AWS CloudFront / AWS WAF"
        waf_confidence = "high"
    elif "x-akamai-transformed" in normalized_headers or "akamai" in normalized_headers.get("server", ""):
        detected_waf = "Akamai"
        waf_confidence = "high"
    elif "x-datadome" in normalized_headers or "datadome" in lower_body:
        detected_waf = "DataDome"
        waf_confidence = "high"
    elif "x-px-" in "".join(normalized_headers.keys()) or "perimeterx" in lower_body:
        detected_waf = "PerimeterX"
        waf_confidence = "high"
    elif "x-iinfo" in normalized_headers or "incap_ses" in normalized_headers.get("set-cookie", ""):
        detected_waf = "Imperva / Incapsula"
    # Check if request was blocked or challenged
    if status_code in {403, 429, 503}:
        if any(keyword in lower_body for keyword in ["captcha", "challenge", "cf-browser-verification", "access denied", "blocked"]):
            blocked = True

    return {
        "detected_waf": detected_waf,
        "confidence": waf_confidence,
        "blocked_or_challenged": blocked,
        "status_code": status_code,
        "is_safe_to_scrape": not blocked and (status_code == 200),
    }


class AntiBotBlockException(RuntimeError):
    """Raised when a target site triggers a bot barrier, CAPTCHA, or WAF challenge.
    
    Per LeadOps strict passivity rules, the system halts without attempting evasion.
    """
    def __init__(self, waf_type: str | None, status_code: int, details: str = "") -> None:
        super().__init__(f"Target source blocked access via {waf_type or 'anti-bot gate'} (HTTP {status_code}): {details}")
        self.waf_type = waf_type
        self.status_code = status_code
        self.details = details
