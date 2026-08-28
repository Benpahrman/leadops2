import json
import unittest

from agents.domain import Lead, State
from agents.paypal import PayPalWebhookAdapter
from agents.paypal_webhook import PayPalWebhookRouter


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class Client:
    def post(self, url, **kwargs):
        if url.endswith("/oauth2/token"):
            return Response(200, {"access_token": "token"})
        return Response(200, {"verification_status": "SUCCESS"})


class PayPalWebhookRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = PayPalWebhookRouter(PayPalWebhookAdapter(
            Client(), "id", "secret", "webhook"
        ))
        self.headers = {
            "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            "PAYPAL-CERT-URL": "https://api-m.paypal.com/cert",
            "PAYPAL-TRANSMISSION-ID": "transmission-id",
            "PAYPAL-TRANSMISSION-SIG": "signature",
            "PAYPAL-TRANSMISSION-TIME": "2026-08-27T10:00:00Z",
        }

    def test_invoice_routes_verified_payment_to_lead(self):
        lead = Lead("lead-route", "daily", state=State.SOW_GENERATED)
        body = json.dumps({
            "id": "event-route-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": "deposit", "invoice_id": "setup-lead-route"},
        })

        self.assertTrue(self.router.route(body, self.headers, {lead.lead_id: lead}))
        self.assertEqual(lead.state, State.DEPOSIT_PAID)

    def test_unknown_lead_is_rejected_before_provider_verification(self):
        body = json.dumps({
            "id": "event-route-2",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": "deposit", "invoice_id": "setup-missing"},
        })

        with self.assertRaises(ValueError):
            self.router.route(body, self.headers, {})

    def test_subscription_can_route_by_explicit_lead_metadata(self):
        lead = Lead("lead-route-sub", "weekly", state=State.DELIVERED)
        body = json.dumps({
            "id": "event-route-3",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "resource": {"custom_id": "lead:lead-route-sub"},
        })

        self.assertTrue(self.router.route(body, self.headers, {lead.lead_id: lead}))
        self.assertTrue(lead.subscription_active)


if __name__ == "__main__":
    unittest.main()