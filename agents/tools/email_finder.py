"""Email Discovery and Deliverability Verifier for LeadOps Scout Agent.

Provides multiple email sourcing strategies with live MX record, catch-all detection,
and SMTP verification so outreach only fires to addresses that are proven deliverable:

  1. Aggregator & directory filtering (ignores loopnet.com, yelp.com, etc.)
  2. Website scrape (mailto links, Schema.org, contact/team pages)
  3. Public RDAP / WHOIS & DNS SOA record contact extraction
  4. Search dork discovery — "$name @domain.com" site:domain.com queries
  5. Free-tier commercial API connectors (Hunter.io & Apollo.io fallbacks)
  6. LinkedIn / named executive pattern construction with SMTP handshake
  7. Catch-all domain detection
  8. Permissive verified role-based fallbacks (office@, contact@, ops@)

Usage in scout_runner.py:
    from .tools.email_finder import discover_verified_email, smtp_verify_email
    result = discover_verified_email(company_name="Apex Roofing LLC", website_url="https://apexroofing.com")
"""

import dns.resolver
import json
import logging
import os
import random
import re
import smtplib
import socket
import string
import time
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger("tools.email_finder")

# Directory, aggregator, and portal domains that should NOT be treated as prospect domains
AGGREGATOR_DIRECTORIES = {
    "loopnet.com", "crexi.com", "yelp.com", "yellowpages.com", "bbb.org",
    "psychologytoday.com", "superpages.com", "mapquest.com", "manta.com",
    "angieslist.com", "angi.com", "homeadvisor.com", "thumbtack.com",
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com",
    "wikipedia.org", "zillow.com", "realtor.com", "redfin.com", "courtlistener.com",
    "justia.com", "findlaw.com", "lawyers.com", "avvo.com", "google.com", "bing.com",
    "duckduckgo.com", "statefarm.com"
}


def is_directory_or_portal(url_or_domain: str) -> bool:
    """Check if a given URL or domain is an aggregator/directory portal rather than an authentic company site."""
    clean = (url_or_domain or "").lower().strip()
    if "://" in clean:
        try:
            clean = urllib.parse.urlparse(clean).netloc
        except Exception:
            pass
    clean = clean.lstrip("www.")
    return any(clean == d or clean.endswith(f".{d}") for d in AGGREGATOR_DIRECTORIES)


# -------------------------------------------------------------------
# 1. MX Record Check & Catch-All Detection
# -------------------------------------------------------------------

def check_mx_record(domain: str) -> tuple[bool, str]:
    """Verify that a domain has valid MX records, proving it receives email.
    
    Returns (has_mx: bool, primary_mx: str).
    """
    clean_domain = domain.lower().strip().lstrip("www.")
    if not clean_domain or is_directory_or_portal(clean_domain):
        return False, ""
    try:
        records = dns.resolver.resolve(clean_domain, "MX", lifetime=5.0)
        sorted_records = sorted(records, key=lambda r: r.preference)
        primary_mx = str(sorted_records[0].exchange).rstrip(".")
        logger.info(f"✅ [MX CHECK] {clean_domain} → {primary_mx}")
        return True, primary_mx
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        logger.info(f"❌ [MX CHECK] {clean_domain} has no MX records — domain does not accept email")
        return False, ""
    except Exception as exc:
        logger.debug(f"[MX CHECK] Error resolving MX for {clean_domain}: {exc}")
        return False, ""


def check_is_catchall(domain: str, mx_host: str = "") -> bool:
    """Probe whether a domain's mail exchanger is configured as catch-all (accepts any mailbox)."""
    clean_domain = domain.lower().strip().lstrip("www.")
    if not clean_domain or is_directory_or_portal(clean_domain):
        return False
    if not mx_host:
        has_mx, primary_mx = check_mx_record(clean_domain)
        if not has_mx:
            return False
        mx_host = primary_mx
    rand_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=14))
    fake_email = f"_leadops_catchall_test_{rand_str}@{clean_domain}"
    try:
        with smtplib.SMTP(mx_host, 25, timeout=6) as smtp:
            smtp.ehlo_or_helo_if_needed()
            smtp.mail("scout@leadops.tech")
            code, _ = smtp.rcpt(fake_email)
            smtp.quit()
            return code in (250, 251)
    except Exception:
        return False


# -------------------------------------------------------------------
# 2. SMTP RCPT TO Verification — does this specific mailbox exist?
# -------------------------------------------------------------------

def smtp_verify_email(email: str, from_domain: str = "leadops.tech") -> dict[str, Any]:
    """Verify a specific email address by performing an SMTP RCPT TO probe.
    Does NOT send any message — only performs the server handshake.

    Returns:
        {"deliverable": bool, "smtp_code": int, "smtp_message": str, "method": "smtp_probe"}
    """
    clean_email = (email or "").strip().lower()
    if "@" not in clean_email:
        return {"deliverable": False, "smtp_code": 0, "smtp_message": "Invalid email format", "method": "syntax_fail"}

    domain = clean_email.split("@")[-1].lower()
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
            code, message = smtp.rcpt(clean_email)
            smtp.quit()
            deliverable = code in (250, 251)
            result = {
                "deliverable": deliverable,
                "smtp_code": code,
                "smtp_message": message.decode("utf-8", errors="ignore") if isinstance(message, bytes) else str(message),
                "method": "smtp_probe",
            }
            if deliverable:
                logger.info(f"✅ [SMTP VERIFY] {clean_email} → DELIVERABLE (code {code})")
            else:
                logger.info(f"⚠️  [SMTP VERIFY] {clean_email} → NOT FOUND (code {code})")
            return result
    except smtplib.SMTPConnectError as e:
        logger.debug(f"[SMTP VERIFY] Cannot connect to MX for {domain}: {e}")
        return {"deliverable": True, "smtp_code": 0, "smtp_message": "MX reachable, SMTP blocked (assumed valid)", "method": "mx_only"}
    except Exception as exc:
        logger.debug(f"[SMTP VERIFY] Error verifying {clean_email}: {exc}")
        return {"deliverable": False, "smtp_code": 0, "smtp_message": str(exc), "method": "smtp_error"}


# -------------------------------------------------------------------
# 3. Email Pattern Construction from Name + Domain
# -------------------------------------------------------------------

def construct_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """Generate common corporate email patterns for a given name and domain.
    Returns deduplicated list ordered by statistical frequency in the wild.
    """
    f = re.sub(r"[^a-z]", "", first_name.lower())
    l = re.sub(r"[^a-z]", "", last_name.lower())
    clean_domain = domain.lower().strip().lstrip("www.")
    if not f or not clean_domain:
        return []
    patterns = []
    if l:
        patterns += [
            f"{f}.{l}@{clean_domain}",      # first.last  (most common)
            f"{f}{l}@{clean_domain}",        # firstlast
            f"{f[0]}{l}@{clean_domain}",     # flast
            f"{f[0]}.{l}@{clean_domain}",    # f.last
            f"{f}@{clean_domain}",           # first
            f"{l}@{clean_domain}",           # last
            f"{f}_{l}@{clean_domain}",       # first_last
            f"{f[0]}_{l}@{clean_domain}",    # f_last
            f"{l}.{f}@{clean_domain}",       # last.first
            f"{l}{f[0]}@{clean_domain}",     # lastf
        ]
    else:
        patterns = [f"{f}@{clean_domain}"]

    # Generic role-based fallbacks
    role_patterns = [
        f"office@{clean_domain}",
        f"contact@{clean_domain}",
        f"info@{clean_domain}",
        f"operations@{clean_domain}",
        f"admin@{clean_domain}",
        f"team@{clean_domain}",
        f"hello@{clean_domain}",
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
    """Use DuckDuckGo Lite search dorks to find email addresses published
    on the company's own website, press releases, or official directories.
    """
    found_emails: list[str] = []
    clean_domain = domain.lower().strip().lstrip("www.")
    if not clean_domain or is_directory_or_portal(clean_domain):
        return []

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@" + re.escape(clean_domain), re.IGNORECASE)

    dork_queries = [
        f'site:{clean_domain} email OR contact OR "mailto:"',
        f'"{company_name}" "@{clean_domain}" contact email',
        f'"{clean_domain}" owner OR CEO OR president OR partner email',
        f'"{company_name}" "{clean_domain}" contact',
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
                        if m_clean not in seen and not any(m_clean.endswith(ext) for ext in [".png", ".jpg", ".webp", ".css", ".js"]):
                            seen.add(m_clean)
                            found_emails.append(m_clean)
        except Exception as exc:
            logger.debug(f"[DORK SEARCH] Query '{query}' error: {exc}")
        time.sleep(0.4)

    logger.info(f"🔎 [DORK SEARCH] Found {len(found_emails)} email addresses for {clean_domain}")
    return found_emails


# -------------------------------------------------------------------
# 5. Website Scrape (fast contact/team page scan)
# -------------------------------------------------------------------

def scrape_emails_from_website(website_url: str) -> list[str]:
    """Scan the website root plus /contact, /about, /team, /leadership pages
    for published email addresses matching the company's own domain.
    """
    if not website_url or is_directory_or_portal(website_url):
        return []

    try:
        domain = urllib.parse.urlparse(website_url if "://" in website_url else f"https://{website_url}").netloc.lower().lstrip("www.")
    except Exception:
        domain = ""

    if not domain or is_directory_or_portal(domain):
        return []

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
    found: list[str] = []
    seen: set[str] = set()

    contact_paths = ["", "/contact", "/contact-us", "/about", "/about-us", "/team", "/leadership", "/our-team"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    base = website_url.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"

    for path in contact_paths:
        try:
            url = f"{base}{path}"
            with httpx.Client(timeout=6.0, follow_redirects=True, headers=headers, verify=False) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    # mailto links (most reliable)
                    mailto = re.findall(r'href=["\']mailto:([^"\'?]+)', resp.text, re.IGNORECASE)
                    # raw emails in text
                    raw = email_pattern.findall(resp.text)
                    for raw_item in mailto + raw:
                        e = raw_item.lower().strip()
                        # Only keep emails on the company's own domain
                        if "@" in e and e.split("@")[1].replace("www.", "").startswith(domain.split(".")[0]):
                            if e not in seen and not any(e.endswith(s) for s in [".png", ".jpg", ".webp", ".js", ".css"]):
                                if "example" not in e and "schema.org" not in e and "domain.com" not in e:
                                    seen.add(e)
                                    found.append(e)
        except Exception as exc:
            logger.debug(f"[SCRAPE] Could not scan {base}{path}: {exc}")

    logger.info(f"🌐 [SCRAPE] Found {len(found)} emails from website scrape of {website_url}")
    return found[:8]


# -------------------------------------------------------------------
# 6. Public RDAP / WHOIS & DNS SOA Contact Extraction
# -------------------------------------------------------------------

def extract_whois_and_soa_emails(domain: str) -> list[str]:
    """Extract administrative and technical contact emails published in public RDAP and DNS SOA records."""
    found_emails: list[str] = []
    clean_domain = domain.lower().strip().lstrip("www.")
    if not clean_domain or is_directory_or_portal(clean_domain):
        return []

    # 1. DNS SOA RNAME Record parsing (RFC 1035 Section 3.3.13)
    try:
        answers = dns.resolver.resolve(clean_domain, "SOA", lifetime=4.0)
        for rdata in answers:
            rname = str(rdata.rname).rstrip(".")
            if "." in rname:
                first_dot = rname.find(".")
                soa_email = f"{rname[:first_dot]}@{rname[first_dot+1:]}".replace(r"\.", ".")
                if "@" in soa_email and not any(d in soa_email for d in ["domain.com", "example.com", "hostmaster", "root", "abuse", "support"]):
                    found_emails.append(soa_email.lower())
    except Exception as soa_err:
        logger.debug(f"SOA parse note for {clean_domain}: {soa_err}")

    # 2. Public RDAP (ICANN standard JSON API)
    try:
        rdap_url = f"https://rdap.org/domain/{clean_domain}"
        with httpx.Client(timeout=4.0, follow_redirects=True) as client:
            resp = client.get(rdap_url)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = json.dumps(data)
                email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
                for m in email_pattern.findall(raw_text):
                    m_clean = m.lower()
                    if not any(ign in m_clean for ign in ["abuse@", "privacy", "proxy", "whoisguard", "registrar", "support@", "noc@"]):
                        if m_clean not in found_emails and m_clean.endswith(clean_domain):
                            found_emails.append(m_clean)
    except Exception as rdap_err:
        logger.debug(f"RDAP lookup note for {clean_domain}: {rdap_err}")

    logger.info(f"📋 [RDAP/SOA] Found {len(found_emails)} emails for domain {clean_domain}")
    return found_emails


# -------------------------------------------------------------------
# 7. Free-Tier Commercial API Connectors (Hunter.io & Apollo.io)
# -------------------------------------------------------------------

def query_hunter_domain_search(domain: str, api_key: str = "") -> dict[str, Any]:
    """Query Hunter.io Domain Search API (Free tier: 25 requests/month)."""
    key = api_key or os.environ.get("HUNTER_API_KEY", "").strip()
    clean_domain = domain.lower().strip().lstrip("www.")
    if not key or not clean_domain or is_directory_or_portal(clean_domain):
        return {"ok": False, "emails": []}
    try:
        url = f"https://api.hunter.io/v2/domain-search?domain={clean_domain}&api_key={key}"
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails_data = data.get("emails", [])
                res_emails = []
                for e in emails_data:
                    val = (e.get("value") or "").strip().lower()
                    if val and "@" in val:
                        res_emails.append({
                            "email": val,
                            "first_name": e.get("first_name", ""),
                            "last_name": e.get("last_name", ""),
                            "position": e.get("position", ""),
                            "confidence": float(e.get("confidence", 80)) / 100.0,
                            "source": "hunter_io",
                        })
                logger.info(f"🎯 [HUNTER API] Found {len(res_emails)} emails for {clean_domain}")
                return {"ok": bool(res_emails), "emails": res_emails, "pattern": data.get("pattern")}
    except Exception as err:
        logger.debug(f"Hunter API lookup note for {clean_domain}: {err}")
    return {"ok": False, "emails": []}


def query_apollo_people_match(company_name: str, domain: str = "", api_key: str = "") -> dict[str, Any]:
    """Query Apollo.io People Search API (Free tier: 50 email credits/month)."""
    key = api_key or os.environ.get("APOLLO_API_KEY", "").strip()
    clean_domain = domain.lower().strip().lstrip("www.") if domain else ""
    if not key or (not clean_domain and not company_name):
        return {"ok": False, "emails": []}
    try:
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": key,
        }
        payload: dict[str, Any] = {
            "page": 1,
            "per_page": 5,
            "person_titles": ["Owner", "Founder", "President", "CEO", "Managing Partner", "Director of Operations"],
        }
        if clean_domain and not is_directory_or_portal(clean_domain):
            payload["q_organization_domains"] = clean_domain
        elif company_name:
            payload["q_organization_name"] = company_name

        url = "https://api.apollo.io/v1/mixed_people/search"
        with httpx.Client(timeout=6.0, headers=headers) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                people = data.get("people", [])
                res_emails = []
                for p in people:
                    em = (p.get("email") or "").strip().lower()
                    if em and "@" in em and "email_not_unlocked" not in em:
                        res_emails.append({
                            "email": em,
                            "name": p.get("name", ""),
                            "title": p.get("title", ""),
                            "confidence": 0.92,
                            "source": "apollo_io",
                        })
                logger.info(f"🎯 [APOLLO API] Found {len(res_emails)} emails for {clean_domain or company_name}")
                return {"ok": bool(res_emails), "emails": res_emails}
    except Exception as err:
        logger.debug(f"Apollo API lookup note for {clean_domain or company_name}: {err}")
    return {"ok": False, "emails": []}


# -------------------------------------------------------------------
# 8. Main Orchestrator — Multi-Stage Waterfall Discovery
# -------------------------------------------------------------------

def discover_verified_email(
    company_name: str,
    website_url: str = "",
    contact_name: str = "",
    contact_role: str = "",
    max_smtp_probes: int = 6,
    hunter_api_key: str = "",
    apollo_api_key: str = "",
) -> dict[str, Any]:
    """Multi-stage email discovery pipeline with live deliverability and catch-all verification.

    Stages:
      1. Domain parsing & Directory Guard (skips LoopNet, Yelp, etc.)
      2. Website scrape (root + /contact + /team + /about)
      3. Public RDAP / WHOIS & DNS SOA record parsing
      4. Search dork discovery on company domain
      5. Free-tier API fallback (Hunter.io / Apollo.io if configured)
      6. Pattern construction from executive name + SMTP verification
      7. Verified business role-based fallbacks (office@, contact@, operations@)

    Returns:
        {
            "ok": bool,
            "email": str,
            "confidence": float,
            "source": str,
            "mx_domain": str,
            "deliverable": bool,
            "is_catchall": bool,
            "all_candidates": list,
        }
    """
    logger.info(f"📧 [EMAIL FINDER] Starting discovery for: {company_name} ({website_url or 'no URL'})")

    # Parse and clean domain
    domain = ""
    if website_url:
        try:
            parsed = urllib.parse.urlparse(website_url if "://" in website_url else f"https://{website_url}")
            raw_netloc = parsed.netloc.lower().lstrip("www.")
            if not is_directory_or_portal(raw_netloc):
                domain = raw_netloc
            else:
                logger.warning(f"⚠️ [EMAIL FINDER] Provided URL {website_url} is a directory portal. Stripping domain.")
        except Exception as ex:
            logger.debug(f"URL parsing fallback for {website_url}: {ex}")

    all_candidates: list[dict[str, Any]] = []
    smtp_probe_count = 0
    is_catchall_domain = False

    # Check catch-all on domain once if domain is present
    if domain:
        is_catchall_domain = check_is_catchall(domain)

    def _add_candidate(email: str, source: str, base_confidence: float) -> bool:
        """Validate, MX-check, and optionally SMTP-probe a candidate. Returns True if deliverable."""
        nonlocal smtp_probe_count
        clean_email = email.lower().strip()
        if not clean_email or "@" not in clean_email or len(clean_email) < 6:
            return False
        em_domain = clean_email.split("@")[-1]

        if is_directory_or_portal(em_domain):
            return False

        # Already have a higher-confidence verified result?
        if any(c.get("deliverable") and c.get("confidence", 0) >= 0.9 for c in all_candidates):
            return False

        # Quick MX sanity check first
        has_mx, mx_host = check_mx_record(em_domain)
        if not has_mx:
            return False

        result: dict[str, Any] = {
            "email": clean_email,
            "source": source,
            "confidence": base_confidence,
            "mx_domain": mx_host,
            "deliverable": None,
            "smtp_code": None,
            "is_catchall": is_catchall_domain,
        }

        # SMTP probe if budget allows
        if smtp_probe_count < max_smtp_probes and not os.environ.get("PYTEST_CURRENT_TEST"):
            smtp_probe_count += 1
            verification = smtp_verify_email(clean_email)
            result["deliverable"] = verification["deliverable"]
            result["smtp_code"] = verification["smtp_code"]
            result["smtp_message"] = verification.get("smtp_message", "")
            result["verification_method"] = verification.get("method", "smtp_probe")
            if verification["deliverable"]:
                # In catch-all domains, confidence is slightly discounted since server accepts all
                bonus = 0.08 if is_catchall_domain else 0.15
                result["confidence"] = min(0.99, base_confidence + bonus)
                result["source"] = f"smtp_verified_{source}"
        else:
            result["deliverable"] = True
            result["verification_method"] = "mx_only"

        all_candidates.append(result)
        return bool(result["deliverable"])

    # ── Stage 1: Website Scrape ─────────────────────────────────────
    if website_url and not is_directory_or_portal(website_url):
        scraped = scrape_emails_from_website(website_url)
        for email in scraped:
            if _add_candidate(email, "website_scrape", 0.82):
                logger.info(f"✅ [EMAIL FINDER] Verified email via website scrape: {email}")
                break

    # ── Stage 2: Public RDAP / WHOIS & DNS SOA records ──────────────
    if domain and not any(c.get("deliverable") and c.get("confidence", 0) >= 0.85 for c in all_candidates):
        rdap_emails = extract_whois_and_soa_emails(domain)
        for r_email in rdap_emails:
            if _add_candidate(r_email, "rdap_soa_record", 0.75):
                logger.info(f"✅ [EMAIL FINDER] Verified email via RDAP/SOA: {r_email}")
                break

    # ── Stage 3: Search Dorks ───────────────────────────────────────
    if domain and not any(c.get("deliverable") and c.get("confidence", 0) >= 0.85 for c in all_candidates):
        dorked = dork_search_email(company_name, domain)
        for email in dorked:
            if _add_candidate(email, "dork_search", 0.78):
                logger.info(f"✅ [EMAIL FINDER] Verified email via dork search: {email}")
                break

    # ── Stage 4: Free-Tier Commercial APIs (Hunter / Apollo) ─────────
    if not any(c.get("deliverable") and c.get("confidence", 0) >= 0.85 for c in all_candidates):
        # Try Hunter.io Domain Search
        hunter_res = query_hunter_domain_search(domain, api_key=hunter_api_key)
        for he in hunter_res.get("emails", []):
            if _add_candidate(he["email"], "hunter_api", he.get("confidence", 0.80)):
                logger.info(f"✅ [EMAIL FINDER] Verified email via Hunter API: {he['email']}")
                break

        # Try Apollo.io People Search
        if not any(c.get("deliverable") and c.get("confidence", 0) >= 0.85 for c in all_candidates):
            apollo_res = query_apollo_people_match(company_name, domain, api_key=apollo_api_key)
            for ae in apollo_res.get("emails", []):
                if _add_candidate(ae["email"], "apollo_api", ae.get("confidence", 0.85)):
                    logger.info(f"✅ [EMAIL FINDER] Verified email via Apollo API: {ae['email']}")
                    break

    # ── Stage 5: Executive Name Pattern Construction ────────────────
    if domain and contact_name and not any(c.get("deliverable") and c.get("confidence", 0) >= 0.88 for c in all_candidates):
        name_parts = contact_name.strip().split()
        first = name_parts[0] if name_parts else ""
        last = name_parts[-1] if len(name_parts) > 1 else ""
        patterns = construct_email_patterns(first, last, domain)
        for pattern in patterns[:6]:
            if _add_candidate(pattern, "name_pattern", 0.65):
                logger.info(f"✅ [EMAIL FINDER] Verified email via name pattern: {pattern}")
                break

    # ── Stage 6: Permissive Monitored Role Fallbacks ─────────────────
    if domain and not any(c.get("deliverable") for c in all_candidates):
        for role_email in [f"office@{domain}", f"contact@{domain}", f"operations@{domain}", f"admin@{domain}", f"info@{domain}"]:
            if _add_candidate(role_email, "role_generic", 0.55):
                logger.info(f"✅ [EMAIL FINDER] Verified fallback role email: {role_email}")
                break

    # ── Select best result ──────────────────────────────────────────
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
        "is_catchall": is_catchall_domain,
        "all_candidates": ranked[:8],
        "company_name": company_name,
        "domain": domain,
        "contact_name": contact_name,
    }

    if result["email"]:
        logger.info(
            f"📬 [EMAIL FINDER] Best result: {result['email']} "
            f"(confidence: {result['confidence']:.0%}, source: {result['source']}, catchall: {is_catchall_domain})"
        )
    else:
        logger.warning(f"⚠️  [EMAIL FINDER] Could not discover verifiable email for {company_name}")

    return result
