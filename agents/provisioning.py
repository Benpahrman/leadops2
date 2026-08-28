import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .domain import Lead, State


class ComputeProvider(str, Enum):
    AZURE = "azure"
    DIGITALOCEAN = "digitalocean"


@dataclass(frozen=True)
class ProvisioningPlan:
    lead_id: str
    provider: ComputeProvider
    environment: str
    jobs: tuple[str, ...]
    requires_secrets: tuple[str, ...]

    def generate_bicep_parameters(self) -> dict[str, Any]:
        """Generate Azure Bicep parameters payload for deployment."""
        return {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "environmentName": {"value": self.environment},
                "leadId": {"value": self.lead_id},
                "paypalClientId": {"reference": {"keyVault": {"id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv"}, "secretName": "PAYPAL-CLIENT-ID"}},
                "paypalClientSecret": {"reference": {"keyVault": {"id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv"}, "secretName": "PAYPAL-CLIENT-SECRET"}},
                "paypalWebhookId": {"value": "9N700290L1521412F"},
            },
        }

    def generate_deployment_command(self, resource_group: str = "rg-leadops-prod") -> str:
        """Generate Azure CLI command to deploy the Container App Job."""
        return (
            f"az deployment group create "
            f"--resource-group {resource_group} "
            f"--template-file infra/bicep/main.bicep "
            f"--parameters environmentName={self.environment} leadId={self.lead_id}"
        )


class ProvisioningService:
    """Create auditable plans; a cloud adapter executes them later."""

    def create_plan(
        self,
        lead: Lead,
        provider: ComputeProvider = ComputeProvider.AZURE,
        environment: str = "production",
    ) -> ProvisioningPlan:
        if lead.state != State.DEPOSIT_PAID:
            raise ValueError("Provisioning requires a verified deposit payment")
        if environment not in {"staging", "production"}:
            raise ValueError("Environment must be staging or production")
        if provider == ComputeProvider.DIGITALOCEAN and environment == "production":
            raise ValueError("DigitalOcean is staging-only until production controls are approved")
        return ProvisioningPlan(
            lead_id=lead.lead_id,
            provider=provider,
            environment=environment,
            jobs=("build", "qa", "delivery"),
            requires_secrets=("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_WEBHOOK_ID"),
        )