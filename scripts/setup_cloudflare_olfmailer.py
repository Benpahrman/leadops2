#!/usr/bin/env python3
"""Cloudflare DNS, Email Routing, and Redirect Provisioning for olfmailer.com.

Automates:
1. DNS cleanup (stale IONOS MX records).
2. Azure Communication Services DNS configuration (TXT verification, SPF, DKIM CNAMEs, DMARC).
3. Cloudflare Email Routing configuration (*@olfmailer.com -> destination inbox).
4. Cloudflare HTTP 301 redirect rule (https://olfmailer.com/* -> target).
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("leadops.cloudflare.olfmailer")

ZONE_ID = "440af43fc7b4522021f45f52190de4fa"
DOMAIN_NAME = "olfmailer.com"
DEFAULT_REDIRECT_URL = "https://omnileadfeeder.tech"
DEFAULT_DESTINATION_EMAIL = "pahrmancb@gmail.com"


class CloudflareManager:
    """Manages DNS records, Email Routing, and Rules for Cloudflare zones."""

    def __init__(self, api_token: str | None = None, zone_id: str = ZONE_ID) -> None:
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip().strip("\"'")
        self.account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip().strip("\"'")
        self.zone_id = zone_id
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN is required. Please set it in .env.")

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated HTTP request against Cloudflare Client v4 API."""
        url = f"https://api.cloudflare.com/client/v4{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body)
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8")
            logger.error(f"Cloudflare API Error [{err.code}] {err.reason}: {err_body}")
            try:
                return json.loads(err_body)
            except Exception:
                return {"success": False, "errors": [{"message": f"HTTP {err.code}: {err.reason}"}]}
        except Exception as exc:
            logger.error(f"Network error calling Cloudflare API: {exc}")
            return {"success": False, "errors": [{"message": str(exc)}]}

    # -------------------------------------------------------------
    # DNS Operations
    # -------------------------------------------------------------
    def list_dns_records(self) -> list[dict[str, Any]]:
        """List all DNS records for the zone."""
        res = self._request(f"/zones/{self.zone_id}/dns_records?per_page=100")
        return res.get("result", []) if res.get("success") else []

    def create_or_update_record(
        self,
        record_type: str,
        name: str,
        content: str,
        ttl: int = 1,
        proxied: bool = False,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Upsert a DNS record by matching record type and name."""
        existing = self.list_dns_records()
        norm_name = name.rstrip(".").lower()
        if not norm_name.endswith(DOMAIN_NAME):
            norm_name = f"{norm_name}.{DOMAIN_NAME}" if norm_name != "@" else DOMAIN_NAME

        matching = [
            r for r in existing
            if r["type"].upper() == record_type.upper() and r["name"].rstrip(".").lower() == norm_name
        ]

        payload: dict[str, Any] = {
            "type": record_type.upper(),
            "name": norm_name,
            "content": content,
            "ttl": ttl,
        }
        if record_type.upper() in ("A", "AAAA", "CNAME"):
            payload["proxied"] = proxied
        if priority is not None and record_type.upper() == "MX":
            payload["priority"] = priority

        if matching:
            record_id = matching[0]["id"]
            if matching[0].get("content", "").strip("\"'") == content.strip("\"'"):
                logger.info(f"✅ DNS Record already aligned: [{record_type}] {norm_name} -> {content}")
                return matching[0]
            logger.info(f"🔄 Updating DNS Record: [{record_type}] {norm_name} -> {content}")
            return self._request(f"/zones/{self.zone_id}/dns_records/{record_id}", method="PUT", data=payload)
        else:
            logger.info(f"➕ Creating DNS Record: [{record_type}] {norm_name} -> {content}")
            return self._request(f"/zones/{self.zone_id}/dns_records", method="POST", data=payload)

    def delete_records_by_type_and_content(self, record_type: str, content_substr: str) -> int:
        """Delete DNS records matching a type and substring in content."""
        records = self.list_dns_records()
        deleted = 0
        for r in records:
            if r["type"].upper() == record_type.upper() and content_substr.lower() in r.get("content", "").lower():
                logger.info(f"🗑️ Deleting stale record: [{r['type']}] {r['name']} -> {r['content']}")
                self._request(f"/zones/{self.zone_id}/dns_records/{r['id']}", method="DELETE")
                deleted += 1
        return deleted

    # -------------------------------------------------------------
    # Azure Communication Services DNS Provisioning
    # -------------------------------------------------------------
    def apply_azure_acs_dns_records(
        self,
        domain_verification_token: str | None = None,
        dkim_selector1_cname: str | None = None,
        dkim_selector2_cname: str | None = None,
    ) -> None:
        """Apply official Azure Communication Services DNS authentication records."""
        logger.info("🔧 Configuring Azure Communication Services DNS records for olfmailer.com...")

        # 1. Domain verification TXT (if supplied)
        if domain_verification_token:
            self.create_or_update_record(
                record_type="TXT",
                name=DOMAIN_NAME,
                content=domain_verification_token,
            )

        # 2. SPF Record: include:spfa.protection.outlook.com for ACS
        existing = self.list_dns_records()
        spf_records = [r for r in existing if r["type"] == "TXT" and "v=spf1" in r.get("content", "")]
        has_spfa = any("spfa.protection.outlook.com" in r.get("content", "") for r in spf_records)

        if not has_spfa:
            acs_spf = "v=spf1 include:spfa.protection.outlook.com ~all"
            self.create_or_update_record(
                record_type="TXT",
                name=DOMAIN_NAME,
                content=acs_spf,
            )

        # 3. DKIM CNAME Records
        if dkim_selector1_cname and dkim_selector2_cname:
            self.create_or_update_record(
                record_type="CNAME",
                name=f"selector1-olfmailer-com._domainkey.{DOMAIN_NAME}",
                content=dkim_selector1_cname,
                proxied=False,
            )
            self.create_or_update_record(
                record_type="CNAME",
                name=f"selector2-olfmailer-com._domainkey.{DOMAIN_NAME}",
                content=dkim_selector2_cname,
                proxied=False,
            )

        # 4. DMARC TXT Record
        dmarc_content = "v=DMARC1; p=none; sp=none; pct=100; rua=mailto:dmarc-reports@olfmailer.com"
        self.create_or_update_record(
            record_type="TXT",
            name=f"_dmarc.{DOMAIN_NAME}",
            content=dmarc_content,
        )

    # -------------------------------------------------------------
    # Cloudflare Email Routing Operations
    # -------------------------------------------------------------
    def list_destinations(self) -> list[dict[str, Any]]:
        """List all destination email addresses registered in the Cloudflare account."""
        if not self.account_id:
            return []
        res = self._request(f"/accounts/{self.account_id}/email/routing/addresses")
        return res.get("result", []) if res.get("success") else []

    def set_explicit_forwarding(self, destination_email: str = DEFAULT_DESTINATION_EMAIL) -> dict[str, Any]:
        """Configure explicit inbound forwarding to target destination email."""
        logger.info(f"🎯 Configuring explicit email routing to '{destination_email}'...")
        dests = self.list_destinations()
        target_dest = next((d for d in dests if d.get("email", "").lower() == destination_email.lower()), None)

        if not target_dest:
            logger.info(f"Adding '{destination_email}' as a new destination address...")
            add_res = self._request(
                f"/accounts/{self.account_id}/email/routing/addresses",
                method="POST",
                data={"email": destination_email},
            )
            if add_res.get("success"):
                logger.info(f"📩 Verification email sent to '{destination_email}'. Please check your inbox and click verify.")
            return {"success": False, "status": "verification_sent", "email": destination_email}

        if not target_dest.get("verified"):
            logger.warning(
                f"⚠️ Destination '{destination_email}' is registered but UNVERIFIED by Cloudflare. "
                f"Please open your '{destination_email}' inbox and click the 1-click verification link from Cloudflare."
            )
            return {"success": False, "status": "unverified", "email": destination_email}

        # Destination is verified: update catch_all rule
        rule_payload = {
            "name": f"Catch-All Forward to {destination_email}",
            "enabled": True,
            "matchers": [{"type": "all"}],
            "actions": [{"type": "forward", "value": [destination_email]}],
        }
        res = self._request(
            f"/zones/{self.zone_id}/email/routing/rules/catch_all",
            method="PUT",
            data=rule_payload,
        )
        if res.get("success"):
            logger.info(f"✅ Catch-all routing successfully active: *@olfmailer.com -> {destination_email}")
        return res

    def enable_email_routing(self, destination_email: str = DEFAULT_DESTINATION_EMAIL) -> dict[str, Any]:
        """Enable Cloudflare Email Routing and configure catch-all forward rule."""
        logger.info(f"📧 Enabling Cloudflare Email Routing for {DOMAIN_NAME}...")

        # 1. Enable Email Routing on the zone
        status_res = self._request(f"/zones/{self.zone_id}/email/routing")
        if not status_res.get("result", {}).get("enabled"):
            logger.info("Enabling Email Routing service...")
            self._request(f"/zones/{self.zone_id}/email/routing/enable", method="POST")

        # 2. Configure explicit forwarding
        routing_res = self.set_explicit_forwarding(destination_email=destination_email)

        # 3. Remove stale IONOS MX records if still present
        deleted_ionos = self.delete_records_by_type_and_content("MX", "ionos")
        if deleted_ionos:
            logger.info(f"Removed {deleted_ionos} stale IONOS MX records.")

        return routing_res

    # -------------------------------------------------------------
    # HTTP 301 Web Redirect
    # -------------------------------------------------------------
    def setup_http_redirect(self, target_url: str = DEFAULT_REDIRECT_URL) -> dict[str, Any]:
        """Configure HTTP 301 redirect rule: https://olfmailer.com/* -> target_url."""
        logger.info(f"🌐 Configuring HTTP 301 Redirect for {DOMAIN_NAME} -> {target_url}...")
        rule_payload = {
            "rules": [
                {
                    "expression": f'(http.host eq "{DOMAIN_NAME}") or (http.host eq "www.{DOMAIN_NAME}")',
                    "description": f"Redirect {DOMAIN_NAME} to {target_url}",
                    "action": "redirect",
                    "action_parameters": {
                        "from_value": {
                            "status_code": 301,
                            "target_url": {"value": target_url},
                            "preserve_query_string": True,
                        }
                    },
                    "enabled": True,
                }
            ]
        }
        res = self._request(
            f"/zones/{self.zone_id}/rulesets/phases/http_request_dynamic_redirect/entrypoint",
            method="PUT",
            data=rule_payload,
        )
        if res.get("success"):
            logger.info(f"✅ HTTP 301 Redirect active: {DOMAIN_NAME} -> {target_url}")
        else:
            logger.warning(f"Redirect rule warning: {res.get('errors')}")
        return res


def main() -> None:
    """CLI execution entrypoint."""
    load_dotenv()
    manager = CloudflareManager()

    import argparse
    parser = argparse.ArgumentParser(description="Cloudflare DNS and Email setup for olfmailer.com")
    parser.add_argument("--verify", action="store_true", help="List current DNS records and routing status")
    parser.add_argument("--setup-email", action="store_true", help="Configure Email Routing to destination inbox")
    parser.add_argument("--destination", type=str, default=DEFAULT_DESTINATION_EMAIL, help="Destination email for inbound forward")
    parser.add_argument("--setup-redirect", action="store_true", help="Configure HTTP 301 redirect")
    parser.add_argument("--redirect-url", type=str, default=DEFAULT_REDIRECT_URL, help="Target URL for redirect")
    parser.add_argument("--apply-azure-dns", action="store_true", help="Apply Azure Communication Services DNS records")
    parser.add_argument("--check-destinations", action="store_true", help="List registered destination inboxes and verification status")
    parser.add_argument("--set-destination", type=str, default=None, help="Explicitly route all inbound emails to this address")

    args = parser.parse_args()

    if args.check_destinations:
        dests = manager.list_destinations()
        print(f"\n--- Cloudflare Email Routing Destinations ({len(dests)}) ---")
        for d in dests:
            status_icon = "[VERIFIED]" if d.get("verified") else "[PENDING VERIFICATION]"
            print(f"{status_icon:<24} {d.get('email')}")
        return

    if args.set_destination:
        res = manager.set_explicit_forwarding(destination_email=args.set_destination)
        print(f"\nResult: {json.dumps(res, indent=2)}")
        return

    if args.verify or (len(sys.argv) == 1):
        records = manager.list_dns_records()
        print(f"\n--- Active DNS Records for {DOMAIN_NAME} ({len(records)}) ---")
        for r in records:
            p = f" (priority: {r.get('priority')})" if r.get("priority") is not None else ""
            print(f"[{r['type']:<5}] {r['name']:<35} -> {r['content']}{p}")

    if args.setup_email:
        manager.enable_email_routing(destination_email=args.destination)

    if args.setup_redirect:
        manager.setup_http_redirect(target_url=args.redirect_url)

    if args.apply_azure_dns:
        manager.apply_azure_acs_dns_records(
            domain_verification_token=args.verification_token,
            dkim_selector1_cname=args.dkim1,
            dkim_selector2_cname=args.dkim2,
        )


if __name__ == "__main__":
    main()
