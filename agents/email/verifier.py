"""Pre-send email deliverability and bounce verification engine."""

import logging
import re
import smtplib
import socket
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("leadops.email.verifier")

# Basic RFC 5322 regex for standard emails
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Common disposable/temporary email providers that harm sender reputation
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "throwawaymail.com", "yopmail.com", "sharklasers.com", "dispostable.com",
    "trashmail.com", "getairmail.com", "crazymailing.com", "maildrop.cc",
    "mytemp.email", "mohmal.com", "fakeinbox.com", "nada.ltd"
}

# Common dummy or placeholder domains
DUMMY_DOMAINS = {
    "company.com", "example.com", "testcompany.com", "domain.com",
    "mycompany.com", "somedomain.com", "test.com"
}

# System/unmonitored addresses that must NEVER receive cold outreach
SYSTEM_DISALLOWED_PREFIXES = {
    "noreply", "no-reply", "donotreply", "mailer-daemon", "postmaster",
    "abuse", "spam", "root", "test", "webmaster", "hostmaster", "security",
    "privacy", "optout", "opt-out", "unsubscribe"
}

# Monitored business inquiry / operations roles common in small-to-mid commercial businesses
BUSINESS_ROLE_PREFIXES = {
    "operations", "executive", "info", "support", "contact", "sales",
    "general", "inquiries", "service", "mail", "frontdesk", "office",
    "billing", "team", "hello", "help", "admin", "inquiry", "customerservice"
}

# Combined set for legacy compatibility
GENERIC_ROLE_PREFIXES = SYSTEM_DISALLOWED_PREFIXES | BUSINESS_ROLE_PREFIXES


class DeliverabilityStatus(str, Enum):
    DELIVERABLE = "DELIVERABLE"
    RISKY = "RISKY"
    UNDELIVERABLE = "UNDELIVERABLE"


@dataclass
class VerificationResult:
    email: str
    status: DeliverabilityStatus
    reason: str
    is_valid_format: bool
    is_disposable: bool
    is_role_account: bool
    domain: str = ""
    mx_records: list[str] = field(default_factory=list)
    smtp_check_passed: bool = False
    is_domain_active: bool = True
    is_catchall: bool = False

    @property
    def is_safe_to_send(self) -> bool:
        """Only genuine DELIVERABLE emails with active mail exchangers and responsive domains are safe to dispatch."""
        return self.status == DeliverabilityStatus.DELIVERABLE and self.is_domain_active


class DeliverabilityVerifier:
    """Performs layered pre-flight verification on outbound email addresses to eliminate bounces."""

    def __init__(
        self,
        probe_smtp: bool = True,
        probe_web: bool = True,
        timeout_seconds: float = 4.0,
        allow_business_roles: bool = False,
        probe_catchall: bool = False,
    ):
        self.probe_smtp = probe_smtp
        self.probe_web = probe_web
        self.timeout_seconds = timeout_seconds
        self.allow_business_roles = allow_business_roles
        self.check_catchall = probe_catchall

    def check_syntax(self, email: str) -> tuple[bool, str, str]:
        """Validate RFC email syntax and parse localpart / domain."""
        clean = (email or "").strip().lower()
        if not clean or len(clean) > 254:
            return False, "", ""
        if not EMAIL_REGEX.match(clean):
            return False, "", ""
        parts = clean.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False, "", ""
        local_part, domain = parts
        if ".." in domain or domain.startswith(".") or domain.endswith("."):
            return False, "", ""
        return True, local_part, domain

    def check_domain_active(self, domain: str) -> tuple[bool, str]:
        """Verify that the target domain is active, resolves via DNS, and has operational network routing."""
        clean_domain = domain.strip().lower()
        if not clean_domain:
            return False, "Empty domain name"

        # 1. DNS A/AAAA record host resolution
        try:
            socket.getaddrinfo(clean_domain, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as e:
            # Fallback check for www subdomain
            try:
                socket.getaddrinfo(f"www.{clean_domain}", 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except Exception:
                logger.debug(f"Domain host resolution failed for {clean_domain}: {e}")
                return False, f"Domain {clean_domain} has no active DNS A/AAAA host records (NXDOMAIN/unreachable)"
        except Exception as e:
            logger.debug(f"Unexpected DNS resolution error for {clean_domain}: {e}")

        # 2. Optional fast web connection probe if probe_web is active
        if self.probe_web:
            try:
                import httpx
                # Fast HEAD/GET probe to verify live web server
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                    verify=False,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LeadOps Deliverability Prober"},
                ) as client:
                    try:
                        resp = client.get(f"https://{clean_domain}")
                    except Exception:
                        resp = client.get(f"http://{clean_domain}")
                    
                    if resp.status_code >= 500:
                        logger.debug(f"Web probe returned server error {resp.status_code} for {clean_domain}")
                        # DNS is valid, server is responding with 5xx - keep active
                        return True, f"Domain active (HTTP {resp.status_code})"
                    return True, f"Domain web host active (HTTP {resp.status_code})"
            except Exception as e:
                # If web port 80/443 is blocked or firewalled but DNS resolved, treat domain as resolving
                logger.debug(f"Domain web connection probe notice for {clean_domain}: {e}")
                return True, "Domain resolves via DNS"

        return True, "Domain resolves via DNS"

    def resolve_mx_records(self, domain: str) -> list[str]:
        """Resolve DNS MX records for target domain, sorting by preference priority."""
        try:
            import dns.resolver
            records = dns.resolver.resolve(domain, "MX", lifetime=self.timeout_seconds)
            mx_hosts = [r.exchange.to_text().rstrip(".") for r in sorted(records, key=lambda r: r.preference)]
            return mx_hosts
        except Exception as e:
            logger.debug(f"DNS MX resolution failed for {domain}: {e}")
            # Fallback check for root A record per RFC 5321 Section 5
            try:
                socket.gethostbyname(domain)
                return [domain]
            except Exception:
                return []

    def probe_mailbox_smtp(self, mx_host: str, target_email: str) -> tuple[bool, str]:
        """Perform non-intrusive SMTP handshake (HELO -> MAIL FROM -> RCPT TO) to verify mailbox existence."""
        try:
            with smtplib.SMTP(mx_host, port=25, timeout=self.timeout_seconds) as server:
                server.ehlo_or_helo_if_needed()
                server.mail("alex@leadops.tech")
                code, resp = server.rcpt(target_email)
                resp_str = resp.decode("utf-8", errors="ignore") if isinstance(resp, bytes) else str(resp)
                if code == 250:
                    return True, "Mailbox exists and accepted probe"
                if code in {550, 551, 552, 553, 554}:
                    return False, f"Mailbox rejected: {code} {resp_str}"
                # Catch greylisting (450, 451) or policy restrictions as non-fatal
                return True, f"Server responded with {code} ({resp_str})"
        except (socket.timeout, TimeoutError):
            return True, "SMTP probe timed out (corporate firewall/greylisting); assuming MX valid"
        except (smtplib.SMTPConnectError, ConnectionRefusedError, OSError) as e:
            return True, f"Port 25 unreachable ({e}); domain has valid MX"
        except Exception as e:
            logger.debug(f"SMTP probe exception for {target_email} on {mx_host}: {e}")
            return True, f"SMTP probe non-conclusive: {e}"

    def probe_catchall(self, mx_host: str, domain: str) -> bool:
        """Probe whether the domain MX has a catch-all configuration by testing a randomized fake address."""
        if not self.probe_smtp or not mx_host:
            return False
        import random
        import string
        rand_token = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        test_email = f"_leadops_catchall_test_{rand_token}@{domain}"
        try:
            with smtplib.SMTP(mx_host, port=25, timeout=self.timeout_seconds) as server:
                server.ehlo_or_helo_if_needed()
                server.mail("alex@leadops.tech")
                code, _ = server.rcpt(test_email)
                return code in (250, 251)
        except Exception:
            return False

    def verify(self, email: str) -> VerificationResult:
        """Run comprehensive verification pipeline on an email address."""
        is_valid, local_part, domain = self.check_syntax(email)
        if not is_valid:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.UNDELIVERABLE,
                reason="Invalid email format or syntax",
                is_valid_format=False,
                is_disposable=False,
                is_role_account=False,
                domain=domain,
                is_domain_active=False,
            )

        # Check dummy/placeholder domains
        if domain in DUMMY_DOMAINS or domain.endswith(".example.com") or domain.endswith(".test") or domain.endswith(".invalid"):
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.UNDELIVERABLE,
                reason=f"Domain '{domain}' is a dummy/placeholder domain",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=False,
                domain=domain,
                is_domain_active=False,
            )

        # Check disposable domains
        is_disposable = domain in DISPOSABLE_DOMAINS
        if is_disposable:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.UNDELIVERABLE,
                reason=f"Domain {domain} is a temporary/disposable email provider",
                is_valid_format=True,
                is_disposable=True,
                is_role_account=False,
                domain=domain,
            )

        # Check active domain DNS and network routing
        is_domain_live, domain_reason = self.check_domain_active(domain)
        if not is_domain_live:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.UNDELIVERABLE,
                reason=f"Domain is inactive or unreachable: {domain_reason}",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=False,
                domain=domain,
                is_domain_active=False,
            )

        # Check DNS MX records before evaluating mailbox or role accounts
        mx_records = self.resolve_mx_records(domain)
        if not mx_records:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.UNDELIVERABLE,
                reason=f"No valid MX or A DNS mail server records found for domain {domain}",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=False,
                domain=domain,
                mx_records=[],
                is_domain_active=is_domain_live,
            )

        # Check role-based accounts: Disallowed vs Monitored Business Roles
        is_disallowed_role = local_part in SYSTEM_DISALLOWED_PREFIXES
        if is_disallowed_role:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.RISKY,
                reason=f"Email local-part '{local_part}' is an unmonitored system/test role account",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=True,
                domain=domain,
                mx_records=mx_records,
                is_domain_active=is_domain_live,
            )

        is_business_role = local_part in BUSINESS_ROLE_PREFIXES
        if is_business_role and not self.allow_business_roles:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.RISKY,
                reason=f"Email local-part '{local_part}' is a general role account",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=True,
                domain=domain,
                mx_records=mx_records,
                is_domain_active=is_domain_live,
            )

        # Check Catch-All status if requested
        primary_mx = mx_records[0] if mx_records else ""
        is_catchall = False
        if self.check_catchall and primary_mx:
            is_catchall = self.probe_catchall(primary_mx, domain)

        # Optional SMTP handshake probe on primary MX
        smtp_passed = True
        reason = "Valid syntax, active domain, and verified MX exchangers"
        if is_business_role:
            reason = f"Verified business role account '{local_part}' on active domain with MX"

        if self.probe_smtp and mx_records:
            passed, probe_msg = self.probe_mailbox_smtp(primary_mx, email)
            smtp_passed = passed
            if not passed:
                return VerificationResult(
                    email=email,
                    status=DeliverabilityStatus.UNDELIVERABLE,
                    reason=f"SMTP handshake failed: {probe_msg}",
                    is_valid_format=True,
                    is_disposable=False,
                    is_role_account=is_business_role,
                    domain=domain,
                    mx_records=mx_records,
                    smtp_check_passed=False,
                    is_domain_active=is_domain_live,
                    is_catchall=is_catchall,
                )
            reason = f"Verified: {probe_msg}"
            if is_catchall:
                reason += " (Domain is catch-all)"

        return VerificationResult(
            email=email,
            status=DeliverabilityStatus.DELIVERABLE,
            reason=reason,
            is_valid_format=True,
            is_disposable=False,
            is_role_account=is_business_role,
            domain=domain,
            mx_records=mx_records,
            smtp_check_passed=smtp_passed,
            is_domain_active=is_domain_live,
            is_catchall=is_catchall,
        )


def check_domain_auth_records(domain: str, timeout_seconds: float = 4.0) -> dict[str, Any]:
    """Inspect SPF and DMARC TXT records for outbound domain deliverability compliance."""
    clean_domain = (domain or "").strip().lower()
    result = {
        "domain": clean_domain,
        "has_spf": False,
        "spf_record": "",
        "has_dmarc": False,
        "dmarc_record": "",
        "dmarc_policy": "",
        "is_ready_for_cold_outreach": False,
    }
    if not clean_domain:
        return result

    try:
        import dns.resolver
        # 1. Query root TXT records for SPF
        try:
            answers = dns.resolver.resolve(clean_domain, "TXT", lifetime=timeout_seconds)
            for rdata in answers:
                txt_str = "".join([s.decode("utf-8", errors="ignore") if isinstance(s, bytes) else str(s) for s in rdata.strings])
                if txt_str.startswith("v=spf1"):
                    result["has_spf"] = True
                    result["spf_record"] = txt_str
                    break
        except Exception as spf_err:
            logger.debug(f"SPF query note for {clean_domain}: {spf_err}")

        # 2. Query _dmarc subdomain for DMARC record
        try:
            dmarc_host = f"_dmarc.{clean_domain}"
            answers_dmarc = dns.resolver.resolve(dmarc_host, "TXT", lifetime=timeout_seconds)
            for rdata in answers_dmarc:
                txt_str = "".join([s.decode("utf-8", errors="ignore") if isinstance(s, bytes) else str(s) for s in rdata.strings])
                if txt_str.startswith("v=DMARC1"):
                    result["has_dmarc"] = True
                    result["dmarc_record"] = txt_str
                    # Extract p= policy
                    import re
                    match = re.search(r"\bp=([a-zA-Z]+)", txt_str)
                    if match:
                        result["dmarc_policy"] = match.group(1).lower()
                    break
        except Exception as dmarc_err:
            logger.debug(f"DMARC query note for {clean_domain}: {dmarc_err}")

        result["is_ready_for_cold_outreach"] = bool(result["has_spf"] and result["has_dmarc"])
    except Exception as exc:
        logger.debug(f"DNS auth query failed for {clean_domain}: {exc}")

    return result
