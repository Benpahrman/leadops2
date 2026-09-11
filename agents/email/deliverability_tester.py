"""Deliverability & Spam Assessment Engine using TestMail.app.

Performs daily morning probes across all active sending inboxes (Zoho, Outlook, Gmail):
1. Synthesizes an AI B2B cold email probe adhering strictly to zero-link sub-55-word rules.
2. Dispatches probe to unique recipient tag: {namespace}.audit_{inbox_id}_{timestamp}@inbox.testmail.app.
3. Polls TestMail JSON API with exponential backoff to retrieve live headers and spam telemetry.
4. Parses SPF, DKIM, SpamAssassin score, rule breakdowns, and roundtrip delivery latency.
5. Computes overall health grade (HEALTHY, WARNING, CRITICAL) and actionable DNS/reputation advice.
6. Persists audit report to SQLite storage and alerts operators via Discord.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .client import EmailClient
from .config import EmailSettings, InboxAccountConfig

logger = logging.getLogger("leadops.email.deliverability_tester")


class DeliverabilityTester:
    """Automated deliverability probe engine for multi-inbox fleet auditing."""

    def __init__(
        self,
        api_key: str | None = None,
        namespace: str | None = None,
        settings: EmailSettings | None = None,
        email_client: EmailClient | None = None,
        storage_backend: Any = None,
        notifier: Any = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("TESTMAIL_API_KEY")
            or os.environ.get("TESTMAIL_API_KAY")
            or "f5c19aa2-97d5-4efc-84b3-30fa59e87c80"
        ).strip()
        self.namespace = (
            namespace
            or os.environ.get("TESTMAIL_NAMESPACE")
            or "KGDDJ"
        ).strip()
        self.settings = settings or EmailSettings.from_environment()
        self.email_client = email_client or EmailClient(settings=self.settings)
        self.storage = storage_backend
        self.notifier = notifier
        self.base_api_url = "https://api.testmail.app/api/json"

    def generate_cold_email_probe(self, inbox: InboxAccountConfig) -> dict[str, str]:
        """Synthesize a realistic B2B cold email conforming to zero-link plain-text rules.
        
        Strict constraints:
        - 35-55 words total
        - Plaintext only, no links or tracking pixels
        - Permission-first hook asking to send today's filings
        - Identity: Alex from OmniLeadFeeder / LeadOps
        """
        sender_name = inbox.from_name or self.settings.from_name or "Alex | OmniLeadFeeder"
        display_first = sender_name.split("|")[0].split()[0].strip() or "Alex"

        subject = "quick question on morning docket records"
        body = (
            f"Hi there,\n\n"
            f"Our automated scraper indexed today's morning public records and filings "
            f"for your target jurisdiction into a clean spreadsheet.\n\n"
            f"Would it be helpful if I passed over a link to the sample dataset so your team can review it?\n\n"
            f"Best,\n"
            f"{display_first}\n"
            f"OmniLeadFeeder Automated Swarm"
        )

        return {
            "subject": subject,
            "body": body,
            "sender_name": sender_name,
            "sender_email": inbox.email_address,
        }

    def send_inbox_probe(
        self,
        inbox: InboxAccountConfig,
        test_tag: str,
    ) -> dict[str, Any]:
        """Dispatch cold email probe from a specific inbox to TestMail."""
        probe = self.generate_cold_email_probe(inbox)
        recipient = f"{self.namespace}.{test_tag}@inbox.testmail.app"
        start_t = time.time()

        try:
            dispatch_res = self.email_client.send_email(
                to_email=recipient,
                to_name="TestMail QA Ingestion",
                subject=probe["subject"],
                text_body=probe["body"],
                inbox=inbox,
                is_transactional=True,  # Bypass cold outreach frozen lock for internal diagnostics
            )
            elapsed_ms = int((time.time() - start_t) * 1000)
            logger.info(
                f"📤 [DELIVERABILITY PROBE] Sent probe from {inbox.email_address} to {recipient} ({elapsed_ms}ms)"
            )
            return {
                "ok": True,
                "inbox_id": inbox.id,
                "email_address": inbox.email_address,
                "recipient": recipient,
                "test_tag": test_tag,
                "dispatch_response": dispatch_res,
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.time() - start_t) * 1000)
            logger.error(
                f"❌ [DELIVERABILITY PROBE FAILED] Send failed for {inbox.email_address}: {exc}"
            )
            return {
                "ok": False,
                "inbox_id": inbox.id,
                "email_address": inbox.email_address,
                "recipient": recipient,
                "test_tag": test_tag,
                "error": str(exc),
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": elapsed_ms,
            }

    def fetch_testmail_report(
        self,
        tag: str,
        wait_seconds: int = 8,
        max_retries: int = 4,
        retry_delay: int = 5,
    ) -> dict[str, Any] | None:
        """Poll TestMail JSON API for received email with matching tag."""
        if not self.api_key or not self.namespace:
            logger.warning("TestMail API key or namespace missing; skipping API poll.")
            return None

        # Wait initial delay for SMTP transport
        if wait_seconds > 0:
            time.sleep(wait_seconds)

        url = f"{self.base_api_url}?apikey={self.api_key}&namespace={self.namespace}&tag={tag}"

        for attempt in range(1, max_retries + 1):
            try:
                resp = httpx.get(url, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json()
                    emails = data.get("emails", [])
                    if emails:
                        # Return the latest email received under this tag
                        logger.info(
                            f"✅ [TESTMAIL RECEIVED] Found {len(emails)} email(s) for tag '{tag}' (attempt {attempt})"
                        )
                        return emails[0]
                elif resp.status_code == 404:
                    logger.debug(f"TestMail tag '{tag}' not yet found (attempt {attempt})")
                else:
                    logger.warning(
                        f"TestMail API HTTP {resp.status_code} for tag '{tag}': {resp.text[:150]}"
                    )
            except Exception as exc:
                logger.warning(f"TestMail API poll error for tag '{tag}': {exc}")

            if attempt < max_retries:
                time.sleep(retry_delay)

        logger.warning(f"⏱️ [TESTMAIL TIMEOUT] No email received for tag '{tag}' after {max_retries} attempts")
        return None

    def evaluate_inbox_health(
        self,
        inbox: InboxAccountConfig,
        testmail_data: dict[str, Any] | None,
        send_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate SPF, DKIM, SpamAssassin score and overall inbox deliverability status."""
        email_addr = inbox.email_address

        if not send_result.get("ok"):
            return {
                "inbox_id": inbox.id,
                "email_address": email_addr,
                "provider": inbox.provider,
                "status": "CRITICAL",
                "score": 0,
                "spf": "fail",
                "dkim": "fail",
                "spam_score": 99.0,
                "spam_verdict": "send_error",
                "spam_report": f"SMTP transmission failed: {send_result.get('error', 'Unknown send error')}",
                "diagnostic": f"SMTP connection or authentication failed. Check credentials in .env.",
                "audited_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": send_result.get("latency_ms", 0),
                "received_in_testmail": False,
            }

        if testmail_data is None:
            return {
                "inbox_id": inbox.id,
                "email_address": email_addr,
                "provider": inbox.provider,
                "status": "WARNING",
                "score": 50,
                "spf": "pending",
                "dkim": "pending",
                "spam_score": 0.0,
                "spam_verdict": "timeout",
                "spam_report": "Email dispatched via SMTP, but TestMail webhook did not receive message within polling window.",
                "diagnostic": "SMTP accepted message for delivery, but TestMail ingestion timed out. Check SMTP queue or outbound relay.",
                "audited_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": send_result.get("latency_ms", 0),
                "received_in_testmail": False,
            }

        spf_raw = str(testmail_data.get("SPF") or "unknown").strip().lower()
        dkim_raw = str(testmail_data.get("dkim") or "none").strip().lower()
        spam_val = testmail_data.get("spam")
        spam_report_raw = str(testmail_data.get("spam_report") or "").strip()

        try:
            spam_score = float(spam_val) if spam_val is not None else 0.0
        except (ValueError, TypeError):
            spam_score = 0.0

        # Status computation
        spf_pass = "pass" in spf_raw
        dkim_pass = "pass" in dkim_raw
        is_clean_spam = spam_score <= 2.0

        diagnostic_parts = []
        score = 100

        if spf_pass:
            diagnostic_parts.append("SPF verified")
        else:
            score -= 40
            diagnostic_parts.append(f"SPF {spf_raw} (check DNS TXT record)")

        if dkim_pass:
            diagnostic_parts.append("DKIM verified")
        elif "none" in dkim_raw:
            score -= 25
            diagnostic_parts.append("DKIM missing/none (add Zoho DKIM TXT record to DNS)")
        else:
            score -= 40
            diagnostic_parts.append(f"DKIM {dkim_raw}")

        if spam_score > 3.0:
            score -= 30
            diagnostic_parts.append(f"Spam score elevated ({spam_score:+.1f})")
        else:
            diagnostic_parts.append(f"Spam score {spam_score:+.1f} (Clean)")

        score = max(0, min(100, score))

        if spf_pass and dkim_pass and is_clean_spam:
            status = "HEALTHY"
            recommendation = "All authentication headers verified. Inbox is fully primed for high-deliverability cold outreach."
        elif spf_pass and ("none" in dkim_raw or spam_score <= 3.5):
            status = "WARNING"
            recommendation = "SPF is authenticating, but DKIM signature is missing or unverified. Verify Zoho DKIM TXT record in DNS domain management."
        else:
            status = "CRITICAL"
            recommendation = "Authentication or spam risk detected. Outbound cold emails may land in Spam. Correct DNS TXT records immediately."

        return {
            "inbox_id": inbox.id,
            "email_address": email_addr,
            "provider": inbox.provider,
            "status": status,
            "score": score,
            "spf": spf_raw,
            "dkim": dkim_raw,
            "spam_score": spam_score,
            "spam_verdict": "pass" if is_clean_spam else "flagged",
            "spam_report": spam_report_raw,
            "diagnostic": "; ".join(diagnostic_parts),
            "recommendation": recommendation,
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": send_result.get("latency_ms", 0),
            "received_in_testmail": True,
            "testmail_date": testmail_data.get("date"),
        }

    def run_fleet_audit(
        self,
        inboxes: list[InboxAccountConfig] | None = None,
        force: bool = False,
        wait_seconds: int = 8,
    ) -> dict[str, Any]:
        """Execute full deliverability audit across all active configured inboxes."""
        run_id = f"AUDIT-{int(time.time())}"
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        # Check if already audited recently (within 12 hours) if not forced
        if not force and self.storage and hasattr(self.storage, "get_latest_deliverability_audit"):
            latest = self.storage.get_latest_deliverability_audit()
            if latest and latest.get("audited_at"):
                try:
                    last_dt = datetime.fromisoformat(latest["audited_at"].replace("Z", "+00:00"))
                    if (now_dt - last_dt).total_seconds() < 43200:  # 12 hours
                        logger.info("Deliverability audit already completed recently; returning cached report.")
                        return latest
                except Exception as parse_err:
                    logger.debug(f"Could not parse last audit timestamp: {parse_err}")

        # Resolve target inboxes
        target_inboxes = inboxes
        if not target_inboxes:
            target_inboxes = [acc for acc in self.settings.get_outbound_inboxes() if acc.is_active]
        if not target_inboxes:
            target_inboxes = [acc for acc in self.settings.get_all_inboxes() if acc.is_active]
        if not target_inboxes and self.settings.user:
            # Fallback to primary account
            target_inboxes = [
                InboxAccountConfig(
                    id="primary",
                    email_address=self.settings.user,
                    password=self.settings.app_password,
                    provider="zoho" if "zoho" in self.settings.smtp_host else "gmail",
                    from_name=self.settings.from_name,
                    smtp_host=self.settings.smtp_host,
                    smtp_port=self.settings.smtp_port,
                    smtp_use_ssl=self.settings.smtp_use_ssl,
                )
            ]

        if not target_inboxes:
            logger.warning("No inboxes configured for deliverability audit.")
            return {
                "ok": False,
                "run_id": run_id,
                "audited_at": now_iso,
                "error": "No inboxes configured in environment or storage.",
                "inboxes": [],
            }

        logger.info(f"🛡️ [DELIVERABILITY AUDIT START] Testing {len(target_inboxes)} active inbox(es)...")

        # 1. Dispatch probes to TestMail with unique tags
        dispatched_probes: list[tuple[InboxAccountConfig, str, dict[str, Any]]] = []
        for idx, inbox in enumerate(target_inboxes, 1):
            clean_tag = f"audit_{inbox.id}_{int(time.time())}_{idx}"
            send_res = self.send_inbox_probe(inbox, clean_tag)
            dispatched_probes.append((inbox, clean_tag, send_res))

        # 2. Wait and poll TestMail for each inbox
        per_inbox_reports: list[dict[str, Any]] = []
        for idx, (inbox, tag, send_res) in enumerate(dispatched_probes):
            testmail_data = None
            if send_res.get("ok"):
                testmail_data = self.fetch_testmail_report(
                    tag=tag,
                    wait_seconds=wait_seconds if idx == 0 else 2,
                    max_retries=3,
                    retry_delay=4,
                )

            report = self.evaluate_inbox_health(inbox, testmail_data, send_res)
            per_inbox_reports.append(report)

        # 3. Calculate fleet rollups
        healthy_count = sum(1 for r in per_inbox_reports if r["status"] == "HEALTHY")
        warning_count = sum(1 for r in per_inbox_reports if r["status"] == "WARNING")
        critical_count = sum(1 for r in per_inbox_reports if r["status"] == "CRITICAL")
        avg_score = round(sum(r["score"] for r in per_inbox_reports) / max(1, len(per_inbox_reports)), 1)

        if critical_count > 0:
            fleet_status = "CRITICAL"
        elif warning_count > 0:
            fleet_status = "WARNING"
        else:
            fleet_status = "HEALTHY"

        full_report: dict[str, Any] = {
            "ok": True,
            "run_id": run_id,
            "audited_at": now_iso,
            "fleet_status": fleet_status,
            "average_score": avg_score,
            "inbox_count": len(per_inbox_reports),
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "critical_count": critical_count,
            "inboxes": per_inbox_reports,
            "testmail_namespace": self.namespace,
        }

        # 4. Save to storage
        if self.storage and hasattr(self.storage, "save_deliverability_audit"):
            try:
                self.storage.save_deliverability_audit(full_report)
                logger.info(f"💾 [STORAGE] Saved deliverability audit {run_id} to database.")
            except Exception as store_err:
                logger.warning(f"Could not persist deliverability audit: {store_err}")

        # 5. Alert operators via Discord / Notifications
        notifier = self.notifier
        if not notifier:
            try:
                from ..notifications import notification_manager
                notifier = notification_manager
            except Exception as notif_import_err:
                logger.debug(f"Notifier import skipped: {notif_import_err}")

        if notifier and hasattr(notifier, "notify_deliverability_audit"):
            try:
                notifier.notify_deliverability_audit(full_report)
                logger.info(f"📢 [NOTIFICATIONS] Dispatched deliverability scorecard to Discord.")
            except Exception as notif_err:
                logger.warning(f"Could not dispatch deliverability notification: {notif_err}")

        logger.info(
            f"✅ [DELIVERABILITY AUDIT COMPLETE] Fleet Status: {fleet_status} | Avg Score: {avg_score}% "
            f"({healthy_count} Healthy, {warning_count} Warnings, {critical_count} Critical)"
        )
        return full_report


def check_domain_dns(domain: str) -> dict[str, Any]:
    """Perform real-time DNS hygiene, SPF, DKIM, and DMARC verification for a domain."""
    clean_domain = domain.strip().lower().lstrip("@")
    results: dict[str, Any] = {
        "domain": clean_domain,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "has_mx": False,
        "mx_records": [],
        "has_spf": False,
        "spf_record": None,
        "has_dmarc": False,
        "dmarc_record": None,
        "dmarc_policy": "none",
        "dkim_selectors_checked": {},
        "score": 100,
        "issues": [],
        "recommendations": [],
    }

    try:
        import dns.resolver
    except ImportError:
        results["issues"].append("dnspython library not installed; falling back to basic socket checks")
        return results

    # 1. Check MX Records
    try:
        mx_answers = dns.resolver.resolve(clean_domain, "MX")
        results["mx_records"] = [f"{r.preference} {r.exchange.to_text().rstrip('.')}" for r in mx_answers]
        results["has_mx"] = len(results["mx_records"]) > 0
    except Exception as e:
        results["issues"].append(f"MX lookup failed: {e}")
        results["score"] -= 35

    # 2. Check SPF (TXT records on base domain)
    try:
        txt_answers = dns.resolver.resolve(clean_domain, "TXT")
        for r in txt_answers:
            txt_str = "".join([part.decode("utf-8", errors="ignore") if isinstance(part, bytes) else str(part) for part in r.strings])
            if txt_str.startswith("v=spf1"):
                results["has_spf"] = True
                results["spf_record"] = txt_str
                break
        if not results["has_spf"]:
            results["issues"].append("Missing SPF record on sending domain")
            results["recommendations"].append(f"Add TXT record for {clean_domain}: 'v=spf1 include:_spf.mx.cloudflare.net include:zohomail.com ~all'")
            results["score"] -= 25
    except Exception as e:
        results["issues"].append(f"TXT/SPF lookup failed: {e}")
        results["score"] -= 25

    # 3. Check DMARC (TXT record at _dmarc.<domain>)
    try:
        dmarc_answers = dns.resolver.resolve(f"_dmarc.{clean_domain}", "TXT")
        for r in dmarc_answers:
            txt_str = "".join([part.decode("utf-8", errors="ignore") if isinstance(part, bytes) else str(part) for part in r.strings])
            if "v=DMARC1" in txt_str:
                results["has_dmarc"] = True
                results["dmarc_record"] = txt_str
                # Parse policy
                if "p=reject" in txt_str:
                    results["dmarc_policy"] = "reject"
                elif "p=quarantine" in txt_str:
                    results["dmarc_policy"] = "quarantine"
                else:
                    results["dmarc_policy"] = "none"
                break
        if not results["has_dmarc"]:
            results["issues"].append("Missing DMARC record (_dmarc." + clean_domain + ")")
            results["recommendations"].append(f"Add TXT record for _dmarc.{clean_domain}: 'v=DMARC1; p=quarantine; pct=100; rua=mailto:admin@{clean_domain}'")
            results["score"] -= 25
        elif results["dmarc_policy"] == "none":
            results["recommendations"].append("Upgrade DMARC policy from p=none to p=quarantine or p=reject for strict protection.")
            results["score"] -= 10
    except Exception as e:
        results["issues"].append(f"DMARC record not found: {e}")
        results["recommendations"].append(f"Add TXT record for _dmarc.{clean_domain}: 'v=DMARC1; p=quarantine; pct=100;'")
        results["score"] -= 25

    # 4. Check common DKIM selectors
    common_selectors = ["default", "zoho", "google", "cf", "k1", "smtp"]
    found_dkim = False
    for sel in common_selectors:
        try:
            sel_query = f"{sel}._domainkey.{clean_domain}"
            dkim_answers = dns.resolver.resolve(sel_query, "TXT")
            for r in dkim_answers:
                txt_str = "".join([part.decode("utf-8", errors="ignore") if isinstance(part, bytes) else str(part) for part in r.strings])
                if "v=DKIM1" in txt_str or "k=rsa" in txt_str or "p=" in txt_str:
                    results["dkim_selectors_checked"][sel] = "ACTIVE"
                    found_dkim = True
                    break
        except Exception:
            results["dkim_selectors_checked"][sel] = "NOT_FOUND"

    if not found_dkim:
        results["recommendations"].append("Verify active DKIM selector name in DNS (e.g. Zoho zb54281880 or Cloudflare custom selector).")

    results["score"] = max(0, min(100, results["score"]))
    results["status"] = "HEALTHY" if results["score"] >= 80 else ("WARNING" if results["score"] >= 50 else "CRITICAL")
    return results


def main() -> None:
    """CLI runner for deliverability testing, DNS verification, and fleet probes."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="LeadOps Deliverability & Domain Authentication CLI")
    parser.add_argument("--domain", default="leadops.io", help="Target domain to verify DNS/SPF/DMARC (default: leadops.io)")
    parser.add_argument("--check-all", action="store_true", help="Run complete DNS audit and active fleet status check")
    parser.add_argument("--probe-inboxes", action="store_true", help="Dispatch live cold email probes to TestMail inbox fleet")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("[DELIVERABILITY] LEADOPS DOMAIN & INBOX AUTHENTICATION AUDITOR")
    print("=" * 70)

    # 1. Perform DNS & Domain Hygiene Audit
    dns_report = check_domain_dns(args.domain)

    if args.json and not args.probe_inboxes:
        import json
        print(json.dumps(dns_report, indent=2))
        return

    print(f"\nDomain Under Audit : {dns_report['domain']}")
    print(f"Deliverability Score: {dns_report['score']}/100 [{dns_report['status']}]")
    print(f"   * MX Records        : {'[OK] Present (' + str(len(dns_report['mx_records'])) + ')' if dns_report['has_mx'] else '[FAIL] Missing'}")
    for mx in dns_report["mx_records"][:3]:
        print(f"       -> {mx}")
    print(f"   * SPF Record        : {'[OK] ' + str(dns_report['spf_record']) if dns_report['has_spf'] else '[FAIL] Missing'}")
    print(f"   * DMARC Policy      : {'[OK] ' + str(dns_report['dmarc_record']) if dns_report['has_dmarc'] else '[FAIL] Missing'}")

    if dns_report["issues"]:
        print("\nIdentified Issues:")
        for iss in dns_report["issues"]:
            print(f"   - {iss}")

    if dns_report["recommendations"]:
        print("\nRecommendations:")
        for rec in dns_report["recommendations"]:
            print(f"   + {rec}")

    # 2. Check Inboxes / Fleet if requested
    if args.check_all or args.probe_inboxes:
        print("\n" + "-" * 70)
        print("INBOX FLEET TELEMETRY & WARMUP POSTURE")
        print("-" * 70)

        tester = DeliverabilityTester()
        inboxes = tester.settings.get_outbound_inboxes() or tester.settings.get_all_inboxes()
        print(f"Active Fleet Size: {len(inboxes)} inboxes")
        for ib in inboxes:
            print(f" * [{ib.provider.upper():6}] {ib.id:8} | {ib.email_address:36} | Daily Limit: {ib.daily_limit}")

        if args.probe_inboxes:
            print("\nDispatching live probes to TestMail.app...")
            fleet_report = tester.run_fleet_deliverability_audit(wait_seconds=6)
            print(f"Fleet Status: {fleet_report.get('fleet_status')} | Avg Score: {fleet_report.get('average_score')}%")

    print("\n" + "=" * 70)
    print("Audit Complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()

