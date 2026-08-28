import unittest
from unittest import mock

from agents.domain import Lead, State
from agents.paypal_checkout import PayPalCheckout


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class Client:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/oauth2/token"):
            return Response(200, {"access_token": "token"})
        return Response(201, {"id": "ORDER-123"})


class PayPalCheckoutTests(unittest.TestCase):
    def test_creates_half_price_deposit_order(self):
        client = Client()
        lead = Lead("lead-checkout", "daily", state=State.SOW_GENERATED)

        result = PayPalCheckout(client, "id", "secret").create_setup_order(lead)

        self.assertEqual(result, {"order_id": "ORDER-123", "purpose": "deposit", "amount": "250.00"})
        order_payload = client.calls[-1][1]["json"]
        self.assertEqual(order_payload["purchase_units"][0]["custom_id"], "deposit")
        self.assertEqual(order_payload["purchase_units"][0]["amount"]["value"], "250.00")
        self.assertFalse(lead.deposit_paid)

    def test_buyout_uses_buyout_purpose(self):
        client = Client()
        lead = Lead("lead-buyout-checkout", "buyout", state=State.SOW_GENERATED)

        result = PayPalCheckout(client, "id", "secret").create_setup_order(lead)

        self.assertEqual(result["purpose"], "buyout")
        self.assertEqual(result["amount"], "750.00")

    def test_checkout_does_not_start_before_sow(self):
        with self.assertRaises(ValueError):
            PayPalCheckout(Client(), "id", "secret").create_setup_order(
                Lead("lead-unready", "daily")
            )

    def test_environment_constructor_uses_sandbox_endpoint(self):
        with mock.patch.dict("os.environ", {
            "PAYPAL_CLIENT_ID": "id",
            "PAYPAL_CLIENT_SECRET": "secret",
            "PAYPAL_WEBHOOK_ID": "webhook",
            "PAYPAL_MODE": "sandbox",
        }, clear=True):
            checkout = PayPalCheckout.from_environment(Client())

        self.assertEqual(checkout.base_url, "https://api-m.sandbox.paypal.com")

    def test_final_order_requires_escrow_preview(self):
        checkout = PayPalCheckout(Client(), "id", "secret")
        lead = Lead("lead-final", "daily", state=State.ESCROW_PREVIEW)

        result = checkout.create_final_order(lead)

        self.assertEqual(result["purpose"], "final")
        self.assertEqual(result["amount"], "250.00")
        self.assertFalse(lead.final_paid)

        lead.state = State.DEV_BUILDING
        with self.assertRaises(ValueError):
            checkout.create_final_order(lead)


if __name__ == "__main__":
    unittest.main()