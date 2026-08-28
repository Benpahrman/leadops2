import unittest

from agents.domain import Lead, PaymentEvent, State
from agents.provisioning import ComputeProvider, ProvisioningService


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.lead = Lead("lead-provision", "daily", state=State.SOW_GENERATED)
        self.lead.record_payment(PaymentEvent.DEPOSIT_PAID)
        self.service = ProvisioningService()

    def test_default_plan_uses_azure_production(self):
        plan = self.service.create_plan(self.lead)

        self.assertEqual(plan.provider, ComputeProvider.AZURE)
        self.assertEqual(plan.environment, "production")
        self.assertIn("delivery", plan.jobs)
        self.assertIn("PAYPAL_WEBHOOK_ID", plan.requires_secrets)

    def test_digitalocean_is_available_for_staging(self):
        plan = self.service.create_plan(
            self.lead,
            ComputeProvider.DIGITALOCEAN,
            "staging",
        )

        self.assertEqual(plan.provider, ComputeProvider.DIGITALOCEAN)

    def test_unpaid_lead_cannot_be_provisioned(self):
        unpaid = Lead("lead-unpaid", "weekly", state=State.SOW_GENERATED)
        with self.assertRaises(ValueError):
            self.service.create_plan(unpaid)

    def test_bicep_parameters_and_deployment_command_generation(self):
        plan = self.service.create_plan(self.lead)
        params = plan.generate_bicep_parameters()
        self.assertIn("parameters", params)
        self.assertEqual(params["parameters"]["leadId"]["value"], "lead-provision")
        self.assertEqual(params["parameters"]["environmentName"]["value"], "production")

        cmd = plan.generate_deployment_command("rg-leadops-eastus")
        self.assertIn("az deployment group create", cmd)
        self.assertIn("--template-file infra/bicep/main.bicep", cmd)
        self.assertIn("leadId=lead-provision", cmd)


if __name__ == "__main__":
    unittest.main()