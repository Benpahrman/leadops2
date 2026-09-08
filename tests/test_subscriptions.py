import unittest
from unittest import mock

from agents.domain import Lead, State
from agents.subscriptions import subscription_activation, subscription_plan


class SubscriptionTests(unittest.TestCase):
    def test_plan_reads_paypal_plan_id_from_environment(self):
        with mock.patch.dict("os.environ", {"PAYPAL_PLAN_ID_DAILY": "P-DAILY"}, clear=True):
            plan = subscription_plan("daily")

        self.assertEqual(plan.name, "Daily Sync")
        self.assertEqual(plan.amount_cents, 50_000)
        self.assertEqual(plan.paypal_plan_id, "P-DAILY")

    def test_buyout_has_no_subscription_plan(self):
        with self.assertRaises(ValueError):
            subscription_plan("buyout")

    def test_activation_requires_delivery_and_plan_id(self):
        lead = Lead("lead-sub", "weekly", state=State.DELIVERED)
        with mock.patch.dict("os.environ", {"PAYPAL_PLAN_ID_WEEKLY": ""}):
            with self.assertRaises(ValueError):
                subscription_activation(lead)

        with mock.patch.dict("os.environ", {"PAYPAL_PLAN_ID_WEEKLY": "P-WEEKLY"}, clear=True):
            activation = subscription_activation(lead)
        self.assertEqual(activation["paypal_plan_id"], "P-WEEKLY")
        self.assertEqual(activation["activation_confirmed"], "false")


if __name__ == "__main__":
    unittest.main()