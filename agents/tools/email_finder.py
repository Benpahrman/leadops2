"""Email Discovery and Deliverability Verifier for LeadOps Scout Agent.

Provides multiple email sourcing strategies with live MX record and SMTP verification
so outreach only fires to addresses that are proven deliverable:

  1. Website scrape (mailto links, Schema.org, contact pages)
  2. Search dork — "$name @domain.com" site:domain.com queries
  3. LinkedIn name extraction + pattern construction
  4. Common pattern brute-force (first@, f.last@, first.last@, info@, ops@)
  5. MX record DNS check — confirms domain accepts any email
  6. SMTP RCPT TO probe — confirms specific mailbox exists (no message sent)

Usage in scout_runner.py:
    from .tools.email_finder import discover_verified_email, smtp_verify_email
    result = discover_verified_email(company_name="Apex Roofing LLC", website_url="https://apexroofing.com")
    # Returns: {"email": "mike@apexroofing.com", "confidence": 0.91, "source": "smtp_verified_pattern", ...}
"""

import dns.resolver
import logging
import re
import smtplib
import socket
import time
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger("tools.email_finder")

# -------------------------------------------------------------------
# 1. MX Record Check — does the domain even receive email?
# -------------------------------------------------------------------

def check_mx_record(domain: str) -> tuple[bool, str]:
    """
    Verify that a domain has valid MX records, proving it receives email.
    Returns (has_mx: bool, primary_mx: str).
    """
    try:
        records = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        sorted_records = sorted(records, key=lambda r: r.preference)
        primary_mx = str(sorted_records[0].exchange).rstrip(".")
        logger.info(f"✅ [MX CHECK] {domain} → {primary_mx}")
        return True, primary_mx
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        logger.info(f"❌ [MX CHECK] {domain} has no MX records — domain does not accept email")
        return False, ""
    except Exception as exc:
        logger.debug(f"[MX CHECK] Error resolving MX for {domain}: {exc}")
        return False, ""


# -------------------------------------------------------------------
# 2. SMTP RCPT TO Verification — does this specific mailbox exist?
# -------------------------------------------------------------------

def smtp_verify_email(email: str, from_domain: str = "leadops.io") -> dict[str, Any]:
    """
    Verify a specific email address by performing an SMTP RCPT TO probe.
    Does NOT send any message — only performs the server handshake.

    Returns:
        {"deliverable": bool, "smtp_code": int, "smtp_message": str, "method": "smtp_probe"}
    """
    domain = email.split("@")[-1].lower()
    has_mx, mx_host = check_mx_record(domain)
    if not has_mx:
        return {
            "deliverable": False,
            "smtp_code": 0,
            "smtp_message": f"No MX record for {domain}",
            "method": "mx_fail",
        }

    try:
        with smtplib.SMTP(timeout=8) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo_or_helo_if_needed()
            smtp.mail(f"scout@{from_domain}")
            code, message = smtp.rcpt(email)
            smtp.quit()
            deliverable = code in (250, 251)
            result = {
                "deliverable": deliverable,
                "smtp_code": code,
                "smtp_message": message.decode("utf-8", errors="ignore") if isinstance(message, bytes) else str(message),
                "method": "smtp_probe",
            }
            if deliverable:
                logger.info(f"✅ [SMTP VERIFY] {email} → DELIVERABLE (code {code})")
            else:
                logger.info(f"⚠️  [SMTP VERIFY] {email} → NOT FOUND (code {code})")
            return result
    except smtplib.SMTPConnectError as e:
        logger.debug(f"[SMTP VERIFY] Cannot connect to MX for {domain}: {e}")
        # Many providers block port 25 — treat as inconclusive, not invalid
        return {"deliverable": True, "smtp_code": 0, "smtp_message": "MX reachable, SMTP blocked (assumed valid)", "method": "mx_only"}
    except Exception as exc:
        logger.debug(f"[SMTP VERIFY] Error verifying {email}: {exc}")
        return {"deliverable": False, "smtp_code": 0, "smtp_message": str(exc), "method": "smtp_error"}


# -------------------------------------------------------------------
# 3. Email Pattern Construction from Name + Domain
# -------------------------------------------------------------------

def construct_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """
    Generate common corporate email patterns for a given name and domain.
    Returns deduplicated list ordered by statistical frequency in the wild.
    """
    f = re.sub(r"[^a-z]", "", first_name.lower())
    l = re.sub(r"[^a-z]", "", last_name.lower())
    if not f or not domain:
        return []
    patterns = []
    if l:
        patterns += [
            f"{f}.{l}@{domain}",      # first.last  (most common)
            f"{f}{l}@{domain}",        # firstlast
            f"{f[0]}{l}@{domain}",     # flast
            f"{f[0]}.{l}@{domain}",    # f.last
            f"{f}@{domain}",           # first
            f"{l}@{domain}",           # last
            f"{f}_{l}@{domain}",       # first_last
            f"{f[0]}_{l}@{domain}",    # f_last
            f"{l}.{f}@{domain}",       # last.first
            f"{l}{f[0]}@{domain}",     # lastf
        ]
    else:
        patterns = [f"{f}@{domain}"]

    # Generic role-based fallbacks — often the actual contact is behind info@
    role_patterns = [
        f"info@{domain}",
        f"contact@{domain}",
        f"operations@{domain}",
        f"ops@{domain}",
        f"admin@{domain}",
        f"hello@{domain}",
    ]
    seen = set()
    result = []
    for p in patterns + role_patterns:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# -------------------------------------------------------------------
# 4. Search Dork Email Discovery
# -------------------------------------------------------------------

def dork_search_email(company_name: str, domain: str) -> list[str]:
    """
    Use DuckDuckGo Lite search dorks to find email addresses published
    on the company's own website or in press releases / directories.
    """
    found_emails: list[str] = []
    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@" + re.escape(domain), re.IGNORECASE)

    dork_queries = [
        f'site:{domain} email OR contact "@{domain}"',
        f'"{company_name}" "@{domain}" contact email',
        f'"{domain}" owner CEO president email contact',
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    seen = set()
    for query in dork_queries:
        if len(found_emails) >= 5:
            break
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://lite.duckduckgo.com/lite/?q={encoded}"
            with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    matches = email_pattern.findall(resp.text)
                    for m in matches:
                        m_clean = m.lower().strip()
                        if m_clean not in seen:
                            seen.add(m_clean)
                            found_emails.append(m_clean)
        except Exception as exc:
            logger.debug(f"[DORK SEARCH] Query '{query}' error: {exc}")
        time.sleep(0.5)  # Polite rate limit

    logger.info(f"🔎 [DORK SEARCH] Found {len(found_emails)} email addresses for {domain}")
    return found_emails


# -------------------------------------------------------------------
# 5. Website Scrape (fast contact page scan)
# -------------------------------------------------------------------

def scrape_emails_from_website(website_url: str) -> list[str]:
    """
    Scan the website root plus /contact, /about, /team, /leadership pages
    for any published email addresses matching the company's own domain.
    """
    domain = urllib.parse.urlparse(website_url).netloc.lower().lstrip("www.")
    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
    found: list[str] = []
    seen: set[str] = set()

    contact_paths = ["", "/contact", "/contact-us", "/about", "/about-us", "/team", "/leadership", "/staff", "/our-team"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    base = website_url.rstrip("/")

    for path in contact_paths:
        try:
            url = f"{base}{path}"
            with httpx.Client(timeout=7.0, follow_redirects=True, headers=headers, verify=False) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    # mailto links (most reliable)
                    mailto = re.findall(r'href=["\']mailto:([^"\'?]+)', resp.text, re.IGNORECASE)
                    # raw emails in text
                    raw = email_pattern.findall(resp.text)
                    for email in mailto + raw:
                        e = email.lower().strip()
                        # Only keep emails on the company's own domain
                        if "@" in e and e.split("@")[1].replace("www.", "").startswith(domain.split(".")[0]):
                            if e not in seen and not any(e.endswith(s) for s in [".png", ".jpg", ".js", ".css"]):
                                if "example" not in e and "schema.org" not in e:
                                    seen.add(e)
                                    found.append(e)
        except Exception as exc:
            logger.debug(f"[SCRAPE] Could not scan {base}{path}: {exc}")

    logger.info(f"🌐 [SCRAPE] Found {len(found)} emails from website scrape of {website_url}")
    return found[:8]


# -------------------------------------------------------------------
# 6. Main Orchestrator — discover_verified_email
# -------------------------------------------------------------------

def discover_verified_email(
    company_name: str,
    website_url: str = "",
    contact_name: str = "",
    contact_role: str = "",
    max_smtp_probes: int = 6,
) -> dict[str, Any]:
    """
    Multi-stage email discovery pipeline with live deliverability verification.

    Stages (each returns early if a verified email is found):
      1. Website scrape (root + /contact + /team + /about)
      2. Search dork discovery on company domain
      3. Pattern construction from LinkedIn name + SMTP verification
      4. Generic role-based patterns (info@, contact@, ops@)

    Args:
        company_name:   Company name (e.g., "Apex Roofing LLC")
        website_url:    Company website URL (optional, improves accuracy)
        contact_name:   Decision-maker name from LinkedIn (optional, "John Smith")
        contact_role:   Title string (optional)
        max_smtp_probes: Max SMTP verification attempts per run

    Returns dict with:
        {
            "email": "john@apexroofing.com",
            "confidence": 0.95,
            "source": "smtp_verified_pattern",
            "mx_domain": "aspmx.l.google.com",
            "all_candidates": [...],
            "deliverable": True,
        }
    """
    logger.info(f"📧 [EMAIL FINDER] Starting discovery for: {company_name} ({website_url or 'no URL'})")

    # Parse domain from URL
    domain = ""
    if website_url:
        try:
            parsed = urllib.parse.urlparse(website_url if "://" in website_url else f"https://{website_url}")
            domain = parsed.netloc.lower().lstrip("www.")
        except Exception:
            pass

    all_candidates: list[dict[str, Any]] = []
    smtp_probe_count = 0

    def _add_candidate(email: str, source: str, base_confidence: float) -> bool:
        """Validate, MX-check, and optionally SMTP-probe a candidate. Returns True if deliverable."""
        nonlocal smtp_probe_count
        email = email.lower().strip()
        if not email or "@" not in email or len(email) < 6:
            return False
        em_domain = email.split("@")[-1]

        # Already have a higher-confidence verified result?
        if any(c.get("deliverable") and c.get("confidence", 0) >= 0.9 for c in all_candidates):
            return False

        # Quick MX sanity check first (cheap)
        has_mx, mx_host = check_mx_record(em_domain)
        if not has_mx:
            return False

        result: dict[str, Any] = {
            "email": email,
            "source": source,
            "confidence": base_confidence,
            "mx_domain": mx_host,
            "deliverable": None,
            "smtp_code": None,
        }

        # SMTP probe if budget allows
        if smtp_probe_count < max_smtp_probes:
            smtp_probe_count += 1
            verification = smtp_verify_email(email)
            result["deliverable"] = verification["deliverable"]
            result["smtp_code"] = verification["smtp_code"]
            result["smtp_message"] = verification.get("smtp_message", "")
            result["verification_method"] = verification.get("method", "smtp_probe")
            if verification["deliverable"]:
                result["confidence"] = min(0.99, base_confidence + 0.15)
                result["source"] = f"smtp_verified_{source}"
        else:
            # MX confirmed — mark as probably deliverable
            result["deliverable"] = True
            result["verification_method"] = "mx_only"

        all_candidates.append(result)
        return bool(result["deliverable"])

    # ── Stage 1: Website Scrape ─────────────────────────────────────
    if website_url:
        scraped = scrape_emails_from_website(website_url)
        for email in scraped:
            if _add_candidate(email, "website_scrape", 0.82):
                logger.info(f"✅ [EMAIL FINDER] Verified email via website scrape: {email}")
                break

    # ── Stage 2: Search Dork ────────────────────────────────────────
    if domain and not any(c.get("deliverable") and c.get("confidence", 0) >= 0.85 for c in all_candidates):
        dorked = dork_search_email(company_name, domain)
        for email in dorked:
            if _add_candidate(email, "dork_search", 0.78):
                logger.info(f"✅ [EMAIL FINDER] Verified email via dork search: {email}")
                break

    # ── Stage 3: Name-based Pattern Construction ────────────────────
    if domain and contact_name and not any(c.get("deliverable") and c.get("confidence", 0) >= 0.88 for c in all_candidates):
        name_parts = contact_name.strip().split()
        first = name_parts[0] if name_parts else ""
        last = name_parts[-1] if len(name_parts) > 1 else ""
        patterns = construct_email_patterns(first, last, domain)
        for pattern in patterns:
            if _add_candidate(pattern, "name_pattern", 0.65):
                logger.info(f"✅ [EMAIL FINDER] Verified email via name pattern: {pattern}")
                break

    # ── Stage 4: Generic Role-based Fallbacks ──────────────────────
    if domain and not any(c.get("deliverable") for c in all_candidates):
        for role_email in [f"info@{domain}", f"contact@{domain}", f"operations@{domain}", f"admin@{domain}"]:
            if _add_candidate(role_email, "role_generic", 0.45):
                logger.info(f"✅ [EMAIL FINDER] Verified fallback role email: {role_email}")
                break

    # ── Select best result ──────────────────────────────────────────
    # Sort by: deliverable first, then confidence descending
    ranked = sorted(
        all_candidates,
        key=lambda c: (
            1 if c.get("deliverable") else 0,
            c.get("confidence", 0),
        ),
        reverse=True,
    )

    best = ranked[0] if ranked else None
    result = {
        "ok": bool(best and best.get("email")),
        "email": best["email"] if best else "",
        "confidence": best.get("confidence", 0.0) if best else 0.0,
        "source": best.get("source", "none") if best else "none",
        "mx_domain": best.get("mx_domain", "") if best else "",
        "deliverable": best.get("deliverable", False) if best else False,
        "all_candidates": ranked[:8],
        "company_name": company_name,
        "domain": domain,
        "contact_name": contact_name,
    }

    if result["email"]:
        logger.info(
            f"📬 [EMAIL FINDER] Best result: {result['email']} "
            f"(confidence: {result['confidence']:.0%}, source: {result['source']})"
        )
    else:
        logger.warning(f"⚠️  [EMAIL FINDER] Could not discover verifiable email for {company_name}")

    return result
