#!/usr/bin/env python3
"""Azure Communication Services (ACS) Provisioning & Verification Orchestrator.

Orchestrates:
1. Azure Resource Group & Communication Services deployment.
2. Custom domain 'olfmailer.com' registration in Azure Email Communication Services.
3. Retrieval of Azure DNS authentication tokens (TXT verification, SPF, DKIM CNAMEs, DMARC).
4. Direct synchronization into Cloudflare DNS via Cloudflare API.
5. Domain verification trigger against Azure.
6. Persistence of AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING into .env.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is in Python module search path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from scripts.setup_cloudflare_olfmailer import CloudflareManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("leadops.azure.acs")

DOMAIN_NAME = "olfmailer.com"
DEFAULT_RG = "rg-leadops-prod"
DEFAULT_LOCATION = "eastus"
DEFAULT_COMM_SERVICE = "leadops-acs"
DEFAULT_EMAIL_SERVICE = "leadops-email-service"


class AzureAcsProvisioner:
    """Manages Azure Communication Services and Email Service lifecycle."""

    def __init__(
        self,
        resource_group: str = DEFAULT_RG,
        location: str = DEFAULT_LOCATION,
        domain_name: str = DOMAIN_NAME,
        env_file: Path | None = None,
    ) -> None:
        self.resource_group = resource_group
        self.location = location
        self.domain_name = domain_name
        self.comm_service_name = DEFAULT_COMM_SERVICE
        self.email_service_name = DEFAULT_EMAIL_SERVICE
        self.env_file = env_file or (Path(__file__).parent.parent / ".env")
        self.cloudflare = CloudflareManager()

    def _run_az(self, args: list[str]) -> tuple[int, str, str]:
        """Execute an Azure CLI command and return (exit_code, stdout, stderr)."""
        cmd = ["az"] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=sys.platform == "win32",
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except FileNotFoundError:
            return 127, "", "Azure CLI ('az') is not installed in the system PATH."

    def check_azure_login(self) -> bool:
        """Verify if Azure CLI is authenticated."""
        code, stdout, stderr = self._run_az(["account", "show"])
        if code == 0:
            try:
                acc = json.loads(stdout)
                logger.info(f"✅ Azure CLI authenticated to subscription '{acc.get('name')}' ({acc.get('id')}) in tenant '{acc.get('tenantId')}'.")
                return True
            except Exception:
                return True
        logger.warning(f"⚠️ Azure CLI not authenticated: {stderr or stdout}")
        return False

    def ensure_resource_group(self) -> bool:
        """Ensure the target Azure resource group exists."""
        logger.info(f"Checking resource group '{self.resource_group}'...")
        code, stdout, _ = self._run_az(["group", "show", "-n", self.resource_group])
        if code == 0:
            logger.info(f"✅ Resource group '{self.resource_group}' already exists.")
            return True

        logger.info(f"Creating resource group '{self.resource_group}' in '{self.location}'...")
        code, stdout, stderr = self._run_az(["group", "create", "-n", self.resource_group, "-l", self.location])
        if code == 0:
            logger.info(f"✅ Resource group '{self.resource_group}' created.")
            return True
        logger.error(f"Failed to create resource group: {stderr}")
        return False

    def provision_via_bicep(self) -> dict[str, Any] | None:
        """Deploy Azure Communication Services using the communication.bicep template."""
        bicep_path = Path(__file__).parent.parent / "infra" / "bicep" / "modules" / "communication.bicep"
        if not bicep_path.exists():
            logger.error(f"Bicep template not found at {bicep_path}")
            return None

        logger.info(f"🚀 Deploying Azure Communication Services via Bicep template: {bicep_path.name}...")
        args = [
            "deployment", "group", "create",
            "--resource-group", self.resource_group,
            "--template-file", str(bicep_path),
            "--parameters", f"domainName={self.domain_name}",
        ]
        code, stdout, stderr = self._run_az(args)
        if code != 0:
            logger.error(f"Bicep deployment failed: {stderr or stdout}")
            return None

        try:
            deploy_result = json.loads(stdout)
            outputs = deploy_result.get("properties", {}).get("outputs", {})
            conn_str = outputs.get("primaryConnectionString", {}).get("value")
            records = outputs.get("verificationRecords", {}).get("value", {})
            return {
                "connection_string": conn_str,
                "verification_records": records,
            }
        except Exception as err:
            logger.error(f"Failed to parse deployment output: {err}")
            return None

    def get_domain_verification_records(self) -> dict[str, Any] | None:
        """Fetch custom domain verification and DKIM DNS records from Azure."""
        logger.info(f"Retrieving DNS verification records for '{self.domain_name}'...")
        args = [
            "communication", "email", "domain", "show",
            "--resource-group", self.resource_group,
            "--email-service-name", self.email_service_name,
            "--domain-name", self.domain_name,
        ]
        code, stdout, stderr = self._run_az(args)
        if code != 0:
            logger.warning(f"Could not retrieve domain status via CLI: {stderr}")
            return None

        try:
            data = json.loads(stdout)
            return data.get("verificationRecords", {})
        except Exception as e:
            logger.error(f"Failed to parse domain records: {e}")
            return None

    def sync_azure_dns_to_cloudflare(self, verification_records: dict[str, Any]) -> None:
        """Push Azure verification tokens and DKIM CNAMEs directly into Cloudflare DNS."""
        logger.info("🔄 Synchronizing Azure DNS records into Cloudflare table...")

        # Domain verification TXT
        domain_token = verification_records.get("Domain", {}).get("value")
        # DKIM CNAMEs
        dkim1 = verification_records.get("DKIM", {}).get("value")
        dkim2 = verification_records.get("DKIM2", {}).get("value")

        self.cloudflare.apply_azure_acs_dns_records(
            domain_verification_token=domain_token,
            dkim_selector1_cname=dkim1,
            dkim_selector2_cname=dkim2,
        )
        logger.info("✅ Cloudflare DNS records synchronized with Azure authentication requirements.")

    def trigger_domain_verification(self) -> bool:
        """Instruct Azure to verify domain DNS records."""
        logger.info(f"Triggering verification check on Azure for '{self.domain_name}'...")
        args = [
            "communication", "email", "domain", "initiate-verification",
            "--resource-group", self.resource_group,
            "--email-service-name", self.email_service_name,
            "--domain-name", self.domain_name,
            "--verification-type", "Domain",
        ]
        code, stdout, stderr = self._run_az(args)
        if code == 0:
            logger.info("✅ Azure domain verification initiated.")
            return True
        logger.warning(f"Verification trigger status: {stderr or stdout}")
        return False

    def retrieve_connection_string(self) -> str | None:
        """Fetch primary connection string from Azure Communication Services."""
        logger.info(f"Retrieving connection string for ACS resource '{self.comm_service_name}'...")
        args = [
            "communication", "list-key",
            "--resource-group", self.resource_group,
            "--name", self.comm_service_name,
        ]
        code, stdout, stderr = self._run_az(args)
        if code != 0:
            logger.error(f"Failed to retrieve keys: {stderr}")
            return None

        try:
            keys = json.loads(stdout)
            return keys.get("primaryConnectionString")
        except Exception as e:
            logger.error(f"Failed to parse keys: {e}")
            return None

    def persist_connection_string(self, connection_string: str) -> None:
        """Write AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING into .env."""
        if not self.env_file.exists():
            content = ""
        else:
            content = self.env_file.read_text(encoding="utf-8")

        key = "AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING"
        val_line = f'{key}="{connection_string}"'

        if key in content:
            content = re.sub(rf"^{key}=.*$", val_line, content, flags=re.MULTILINE)
        else:
            content = content.rstrip() + f"\n\n# Azure Communication Services\n{val_line}\n"

        # Also ensure sender domain is set
        domain_key = "AZURE_COMMUNICATION_SENDER_DOMAIN"
        if domain_key not in content:
            content = content.rstrip() + f'\n{domain_key}="{self.domain_name}"\n'

        self.env_file.write_text(content, encoding="utf-8")
        logger.info(f"💾 Successfully persisted {key} into {self.env_file.name}.")


def main() -> None:
    """CLI orchestrator entrypoint."""
    load_dotenv()
    provisioner = AzureAcsProvisioner()

    import argparse
    parser = argparse.ArgumentParser(description="Azure ACS Provisioner for olfmailer.com")
    parser.add_argument("--check-login", action="store_true", help="Check Azure CLI login status")
    parser.add_argument("--deploy", action="store_true", help="Deploy Azure resources and sync DNS")
    parser.add_argument("--sync-dns", action="store_true", help="Sync existing Azure DNS records to Cloudflare")
    parser.add_argument("--verify-domain", action="store_true", help="Trigger Azure domain verification")
    parser.add_argument("--save-key", type=str, default=None, help="Directly save ACS Connection String to .env")

    args = parser.parse_args()

    if args.save_key:
        provisioner.persist_connection_string(args.save_key)
        sys.exit(0)

    is_logged_in = provisioner.check_azure_login()
    if args.check_login:
        sys.exit(0 if is_logged_in else 1)

    if not is_logged_in:
        print("\n" + "="*70)
        print("ACTION REQUIRED: Please authenticate Azure CLI by running:")
        print('az login --tenant "d0547f8c-7cec-4eb6-b27c-6bb508b6c57c"')
        print("="*70 + "\n")

    if args.deploy:
        if not is_logged_in:
            logger.error("Cannot deploy without an active Azure CLI session.")
            sys.exit(1)
        provisioner.ensure_resource_group()
        result = provisioner.provision_via_bicep()
        if result and result.get("verification_records"):
            provisioner.sync_azure_dns_to_cloudflare(result["verification_records"])
            if result.get("connection_string"):
                provisioner.persist_connection_string(result["connection_string"])
            provisioner.trigger_domain_verification()

    if args.sync_dns and is_logged_in:
        records = provisioner.get_domain_verification_records()
        if records:
            provisioner.sync_azure_dns_to_cloudflare(records)

    if args.verify_domain and is_logged_in:
        provisioner.trigger_domain_verification()


if __name__ == "__main__":
    main()
