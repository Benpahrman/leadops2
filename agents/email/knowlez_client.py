#!/usr/bin/env python3
"""Knowlez Deliverability Suite API client with smart 14-day SQLite caching and provider fingerprinting.

Docs: https://api-deliverability-suite.knowlez.com/docs
Endpoints:
- POST /v1/email/verify: Syntax, MX records, disposable domain, role-based checks, deliverability score
- POST /v1/email/verify-batch: Batch validation of multiple email addresses
- POST /v1/domain/validate: Domain MX / format / disposable checks
- POST /v1/url/check: URL safety, redirects, reachability
- POST /v1/ip/classify: IP geo, ASN, proxy/VPN classification
- GET  /v1/usage: API-key quota used / limit / remaining

Key Optimizations:
1. Smart Zero-Waste Caching: 14-day TTL in SQLite + memory cache prevents burning API quota on re-checks.
2. Email Provider Fingerprinting: Categorizes recipient mail systems as 'google', 'microsoft', or 'other'
   via DNS MX inspection to enable peer-to-peer delivery alignment (e.g. Outlook-to-Outlook).
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("leadops.email.knowlez")

DEFAULT_KNOWLEZ_URL = "https://api-deliverability-suite.knowlez.com"
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "leadops_email_engine.db"
DEFAULT_CACHE_TTL_DAYS = 14


def detect_email_provider(mx_hosts: list[str] | None, email: str = "") -> str:
    """Detect whether recipient uses Google Workspace/Gmail, Microsoft 365/Outlook, or other.

    Returns: 'google', 'microsoft', or 'other'
    """
    clean_email = (email or "").lower().strip()
    domain = clean_email.split("@")[-1] if "@" in clean_email else ""

    # 1. Direct domain check
    if domain in ("gmail.com", "googlemail.com"):
        return "google"
    if domain in ("outlook.com", "hotmail.com", "live.com", "msn.com", "office365.com"):
        return "microsoft"

    # 2. MX hostname inspection
    hosts = mx_hosts or []
    for mx in hosts:
        mx_lower = str(mx).lower().strip()
        if any(g in mx_lower for g in [
            "google.com", "googlemail.com", "aspmx.l.google.com",
            "aspmx2.googlemail.com", "aspmx3.googlemail.com", "smtp.google.com"
        ]):
            return "google"
        if any(m in mx_lower for m in [
            "outlook.com", "office365.com", "protection.outlook.com",
            "mail.protection.outlook.com", "pphosted.com", "microsoft.com"
        ]):
            return "microsoft"

    return "other"


class KnowlezDeliverabilityClient:
    """Production client for Knowlez Email Deliverability Suite with zero-waste caching."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 12.0,
        db_path: str | Path | None = None,
        cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
    ) -> None:
        raw_key = api_key if api_key is not None else os.environ.get("KNOWLEZ_API_KEY", "")
        self.api_key = (raw_key or "").strip().strip('"\'')
        self.base_url = (base_url or os.environ.get("KNOWLEZ_BASE_URL") or DEFAULT_KNOWLEZ_URL).strip().rstrip("/")
        self.timeout = timeout
        self.cache_ttl_days = cache_ttl_days
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._local = threading.local()
        self._mem_cache: dict[str, dict[str, Any]] = {}
        self._init_cache_db()

    @property
    def is_configured(self) -> bool:
        """Return True if an API key is configured."""
        return bool(self.api_key)

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn

    def _init_cache_db(self) -> None:
        """Initialize SQLite deliverability cache table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS email_deliverability_cache (
                        email TEXT PRIMARY KEY,
                        score INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        valid INTEGER NOT NULL,
                        mx_ok INTEGER NOT NULL,
                        disposable INTEGER NOT NULL,
                        role_based INTEGER NOT NULL,
                        provider TEXT NOT NULL,
                        mx_hosts_json TEXT NOT NULL,
                        reason TEXT DEFAULT '',
                        raw_response_json TEXT NOT NULL,
                        checked_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS ix_email_deliv_checked 
                    ON email_deliverability_cache (checked_at DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS domain_validation_cache (
                        domain TEXT PRIMARY KEY,
                        valid INTEGER NOT NULL,
                        tld TEXT DEFAULT '',
                        normalized TEXT DEFAULT '',
                        raw_response_json TEXT NOT NULL,
                        checked_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS ix_domain_val_checked
                    ON domain_validation_cache (checked_at DESC)
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.warning(f"Could not initialize deliverability cache DB at {self.db_path}: {exc}")

    def get_cached_verification(self, email: str, max_age_days: int | None = None) -> dict[str, Any] | None:
        """Return cached verification result if valid and within TTL; otherwise None."""
        clean = (email or "").strip().lower()
        if not clean:
            return None

        ttl = max_age_days if max_age_days is not None else self.cache_ttl_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl)

        # 1. Fast memory cache check
        if clean in self._mem_cache:
            item = self._mem_cache[clean]
            checked_at_dt = item.get("_checked_at_dt")
            if checked_at_dt and checked_at_dt >= cutoff:
                cached_copy = {k: v for k, v in item.items() if not k.startswith("_")}
                cached_copy["cached"] = True
                return cached_copy

        # 2. SQLite cache check
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM email_deliverability_cache WHERE email = ?",
                    (clean,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                checked_at_str = row["checked_at"]
                try:
                    checked_at_dt = datetime.fromisoformat(checked_at_str)
                    if checked_at_dt.tzinfo is None:
                        checked_at_dt = checked_at_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    checked_at_dt = datetime.now(timezone.utc)

                if checked_at_dt < cutoff:
                    return None  # Expired cache

                mx_hosts = []
                try:
                    mx_hosts = json.loads(row["mx_hosts_json"])
                except Exception:
                    pass

                result = {
                    "email": clean,
                    "score": int(row["score"]),
                    "status": row["status"],
                    "valid": bool(row["valid"]),
                    "mx_ok": bool(row["mx_ok"]),
                    "disposable": bool(row["disposable"]),
                    "role_based": bool(row["role_based"]),
                    "provider": row["provider"] or detect_email_provider(mx_hosts, clean),
                    "mx_hosts": mx_hosts,
                    "reason": row["reason"] or None,
                    "checked_at": checked_at_str,
                    "cached": True,
                }
                # Populate memory cache with datetime object for TTL comparison
                mem_item = dict(result)
                mem_item["_checked_at_dt"] = checked_at_dt
                self._mem_cache[clean] = mem_item
                return result
        except Exception as exc:
            logger.debug(f"Deliverability cache lookup exception for {clean}: {exc}")
            return None

    def save_cached_verification(self, email: str, data: dict[str, Any]) -> None:
        """Store verification record into SQLite and memory cache."""
        clean = (email or "").strip().lower()
        if not clean:
            return

        now_str = datetime.now(timezone.utc).isoformat()
        now_dt = datetime.now(timezone.utc)

        score = int(data.get("score", 0))
        valid = bool(data.get("valid", False))
        status = data.get("status") or ("DELIVERABLE" if (valid and score >= 60) else "UNDELIVERABLE" if not valid else "RISKY")
        mx_ok = bool(data.get("mx_ok", True))
        disposable = bool(data.get("disposable", False))
        role_based = bool(data.get("role_based", False))
        reason = data.get("reason") or ""
        mx_hosts = data.get("mx_hosts", [])
        provider = data.get("provider") or detect_email_provider(mx_hosts, clean)

        # Update in-memory
        mem_item = dict(data)
        mem_item["provider"] = provider
        mem_item["status"] = status
        mem_item["checked_at"] = now_str
        mem_item["_checked_at_dt"] = now_dt
        self._mem_cache[clean] = mem_item

        # Persist to SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO email_deliverability_cache (
                        email, score, status, valid, mx_ok, disposable,
                        role_based, provider, mx_hosts_json, reason, raw_response_json, checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        score=excluded.score,
                        status=excluded.status,
                        valid=excluded.valid,
                        mx_ok=excluded.mx_ok,
                        disposable=excluded.disposable,
                        role_based=excluded.role_based,
                        provider=excluded.provider,
                        mx_hosts_json=excluded.mx_hosts_json,
                        reason=excluded.reason,
                        raw_response_json=excluded.raw_response_json,
                        checked_at=excluded.checked_at
                    """,
                    (
                        clean,
                        score,
                        status,
                        1 if valid else 0,
                        1 if mx_ok else 0,
                        1 if disposable else 0,
                        1 if role_based else 0,
                        provider,
                        json.dumps(mx_hosts),
                        str(reason),
                        json.dumps(data),
                        now_str,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.debug(f"Deliverability cache write exception for {clean}: {exc}")

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "LeadOps-EmailEngine/1.0",
        }

    def get_usage(self) -> dict[str, Any]:
        """Check API key credit usage, limit, and trial status."""
        if not self.is_configured:
            return {"error": "Knowlez API key not configured"}

        url = f"{self.base_url}/v1/usage"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Knowlez usage check returned HTTP {resp.status_code}: {resp.text}")
                return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except Exception as exc:
            logger.warning(f"Knowlez usage check network error: {exc}")
            return {"error": str(exc)}

    def verify_email(self, email: str, force: bool = False) -> dict[str, Any]:
        """Perform comprehensive pre-send verification with zero-waste caching and provider detection.

        If already checked within cache TTL, returns cached response immediately without calling API.
        """
        clean_email = (email or "").strip().lower()
        if not clean_email:
            return {
                "email": email,
                "valid": False,
                "syntax_ok": False,
                "mx_ok": False,
                "disposable": False,
                "role_based": False,
                "score": 0,
                "provider": "other",
                "reason": "empty_email",
                "cached": False,
            }

        # 1. Check Cache First (Conserve Knowlez credits)
        if not force:
            cached = self.get_cached_verification(clean_email)
            if cached:
                logger.info(
                    f"⚡ [KNOWLEZ CACHE HIT] '{clean_email}' -> Valid: {cached.get('valid')} | "
                    f"Score: {cached.get('score')} | Provider: {cached.get('provider')} | (0 API Credits Burned)"
                )
                return cached

        # 2. Check API Key
        if not self.is_configured:
            logger.debug("Knowlez API key not configured; skipping remote verification.")
            fallback_provider = detect_email_provider([], clean_email)
            return {
                "email": clean_email,
                "valid": True,
                "syntax_ok": True,
                "score": 80,
                "provider": fallback_provider,
                "unverified_fallback": True,
                "cached": False,
            }

        # 3. Call Remote API
        url = f"{self.base_url}/v1/email/verify"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_headers(), json={"email": clean_email})
                if resp.status_code in (200, 201):
                    data = resp.json()
                    is_valid = bool(data.get("valid", False))
                    score = int(data.get("score", 0))
                    disposable = bool(data.get("disposable", False))
                    mx_ok = bool(data.get("mx_ok", True))
                    reason = data.get("reason")
                    mx_hosts = data.get("mx_hosts", [])
                    provider = detect_email_provider(mx_hosts, clean_email)

                    data["provider"] = provider
                    data["cached"] = False
                    data["status"] = "DELIVERABLE" if (is_valid and score >= 60) else ("UNDELIVERABLE" if not is_valid else "RISKY")

                    # Store in Cache for 14 days
                    self.save_cached_verification(clean_email, data)

                    logger.info(
                        f"🛡️ [KNOWLEZ VERIFY] '{clean_email}' -> Valid: {is_valid} | Score: {score} | "
                        f"Provider: {provider} | MX: {mx_ok} | Disposable: {disposable} | Reason: {reason}"
                    )
                    return data

                logger.warning(f"Knowlez email verify returned HTTP {resp.status_code}: {resp.text}")
                return {
                    "email": clean_email,
                    "valid": False,
                    "error": f"HTTP {resp.status_code}",
                    "provider": detect_email_provider([], clean_email),
                    "detail": resp.text,
                    "cached": False,
                }
        except Exception as exc:
            logger.warning(f"Knowlez email verify exception for '{clean_email}': {exc}")
            # Fallback defensively so transient external outages don't hard crash the worker
            return {
                "email": clean_email,
                "valid": True,
                "score": 75,
                "provider": detect_email_provider([], clean_email),
                "unverified_fallback": True,
                "error": str(exc),
                "cached": False,
            }

    def verify_batch(self, emails: list[str], force: bool = False) -> list[dict[str, Any]]:
        """Verify multiple email addresses in batch, using cache for any previously checked."""
        clean_emails = [e.strip().lower() for e in emails if e and e.strip()]
        if not clean_emails:
            return []

        results_by_email: dict[str, dict[str, Any]] = {}
        uncached_emails: list[str] = []

        # 1. Partition into cached vs. uncached
        if not force:
            for email in clean_emails:
                cached = self.get_cached_verification(email)
                if cached:
                    results_by_email[email] = cached
                else:
                    uncached_emails.append(email)
        else:
            uncached_emails = list(clean_emails)

        logger.info(
            f"📦 [DELIVERABILITY BATCH] Total: {len(clean_emails)} | "
            f"Cached: {len(results_by_email)} | Need Verification: {len(uncached_emails)}"
        )

        # If all cached, return immediately with zero API calls!
        if not uncached_emails:
            return [results_by_email[e] for e in clean_emails if e in results_by_email]

        if not self.is_configured:
            for e in uncached_emails:
                results_by_email[e] = {
                    "email": e,
                    "valid": True,
                    "score": 80,
                    "provider": detect_email_provider([], e),
                    "unverified_fallback": True,
                    "cached": False,
                }
            return [results_by_email.get(e, {}) for e in clean_emails]

        # 2. Call Knowlez Batch Endpoint for uncached addresses
        url = f"{self.base_url}/v1/email/verify-batch"
        try:
            with httpx.Client(timeout=self.timeout * 2) as client:
                resp = client.post(url, headers=self._get_headers(), json={"emails": uncached_emails})
                if resp.status_code in (200, 201):
                    raw_res = resp.json()
                    items = raw_res.get("results", raw_res) if isinstance(raw_res, dict) else raw_res
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "email" in item:
                                em = item["email"].lower().strip()
                                prov = detect_email_provider(item.get("mx_hosts", []), em)
                                item["provider"] = prov
                                item["cached"] = False
                                self.save_cached_verification(em, item)
                                results_by_email[em] = item
                else:
                    logger.warning(f"Knowlez batch verify returned HTTP {resp.status_code}: {resp.text}")
        except Exception as exc:
            logger.warning(f"Knowlez batch verify error: {exc}")

        # 3. Fallback for any remaining unverified emails via individual calls
        for e in uncached_emails:
            if e not in results_by_email:
                res = self.verify_email(e, force=force)
                results_by_email[e] = res

        return [results_by_email.get(e, {"email": e, "valid": False, "cached": False}) for e in clean_emails]

    def get_cached_domain(self, domain: str, max_age_days: int = 30) -> dict[str, Any] | None:
        """Return cached domain validation result if within TTL; otherwise None."""
        clean = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        if not clean:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM domain_validation_cache WHERE domain = ?",
                    (clean,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                checked_at_str = row["checked_at"]
                try:
                    checked_at_dt = datetime.fromisoformat(checked_at_str)
                    if checked_at_dt.tzinfo is None:
                        checked_at_dt = checked_at_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    checked_at_dt = datetime.now(timezone.utc)

                if checked_at_dt < cutoff:
                    return None

                raw_data = {}
                try:
                    raw_data = json.loads(row["raw_response_json"])
                except Exception:
                    pass

                result = {
                    "domain": clean,
                    "valid": bool(row["valid"]),
                    "tld": row["tld"] or "",
                    "normalized": row["normalized"] or clean,
                    "checked_at": checked_at_str,
                    "cached": True,
                    **{k: v for k, v in raw_data.items() if k not in ("domain", "valid", "cached")},
                }
                return result
        except Exception as exc:
            logger.debug(f"Domain validation cache lookup exception for {clean}: {exc}")
            return None

    def save_cached_domain(self, domain: str, data: dict[str, Any]) -> None:
        """Store domain validation result into SQLite cache."""
        clean = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        if not clean:
            return

        now_str = datetime.now(timezone.utc).isoformat()
        valid = bool(data.get("valid", False))
        tld = str(data.get("tld") or "")
        normalized = str(data.get("normalized") or clean)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO domain_validation_cache (
                        domain, valid, tld, normalized, raw_response_json, checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(domain) DO UPDATE SET
                        valid=excluded.valid,
                        tld=excluded.tld,
                        normalized=excluded.normalized,
                        raw_response_json=excluded.raw_response_json,
                        checked_at=excluded.checked_at
                    """,
                    (clean, 1 if valid else 0, tld, normalized, json.dumps(data), now_str),
                )
                conn.commit()
        except Exception as exc:
            logger.debug(f"Domain validation cache write exception for {clean}: {exc}")

    def validate_domain(self, domain: str, force: bool = False) -> dict[str, Any]:
        """Validate sending or target domain MX, syntax, and disposable status."""
        clean_domain = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        if not clean_domain:
            return {"domain": domain, "valid": False, "reason": "empty_domain"}

        # 1. Check Cache First (Conserve Knowlez credits)
        if not force:
            cached = self.get_cached_domain(clean_domain)
            if cached:
                logger.info(f"⚡ [KNOWLEZ DOMAIN CACHE HIT] '{clean_domain}' -> Valid: {cached.get('valid')} (0 API Credits Burned)")
                return cached

        if not self.is_configured:
            return {"domain": clean_domain, "valid": True, "unverified_fallback": True}

        url = f"{self.base_url}/v1/domain/validate"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_headers(), json={"domain": clean_domain})
                if resp.status_code in (200, 201):
                    data = resp.json()
                    data["cached"] = False
                    self.save_cached_domain(clean_domain, data)
                    logger.info(f"🌐 [KNOWLEZ DOMAIN] '{clean_domain}' -> Valid: {data.get('valid')} | TLD: {data.get('tld')}")
                    return data
                logger.warning(f"Knowlez domain validate returned HTTP {resp.status_code}: {resp.text}")
                return {"domain": clean_domain, "valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.warning(f"Knowlez domain validate exception for '{clean_domain}': {exc}")
            return {"domain": clean_domain, "valid": False, "error": str(exc)}

    def check_url(self, target_url: str) -> dict[str, Any]:
        """Inspect a prospect URL for reachability, safety, and redirect health."""
        if not self.is_configured:
            return {"url": target_url, "checked": False}

        url = f"{self.base_url}/v1/url/check"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_headers(), json={"url": target_url})
                if resp.status_code in (200, 201):
                    return resp.json()
        except Exception as exc:
            logger.warning(f"Knowlez URL check exception: {exc}")
        return {"url": target_url, "error": "check_failed"}

    def classify_ip(self, ip_address: str) -> dict[str, Any]:
        """Classify IP geo, ASN, and proxy/VPN status."""
        if not self.is_configured:
            return {"ip": ip_address, "checked": False}

        url = f"{self.base_url}/v1/ip/classify"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_headers(), json={"ip": ip_address})
                if resp.status_code in (200, 201):
                    return resp.json()
        except Exception as exc:
            logger.warning(f"Knowlez IP classify exception: {exc}")
        return {"ip": ip_address, "error": "classify_failed"}


# Global singleton instance
_knowlez_client: KnowlezDeliverabilityClient | None = None


def get_knowlez_client() -> KnowlezDeliverabilityClient:
    """Return or initialize the singleton KnowlezDeliverabilityClient instance."""
    global _knowlez_client
    if _knowlez_client is None:
        _knowlez_client = KnowlezDeliverabilityClient()
    return _knowlez_client
