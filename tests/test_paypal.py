import json
import unittest

from agents.domain import Lead, PaymentEvent, State
from agents.paypal import PayPalWebhookAdapter


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakePayPalClient:
    def __init__(self, verification_status="SUCCESS"):
        self.calls = []
        self.verification_status = verification_status

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/oauth2/token"):
            return FakeResponse(200, {"access_token": "test-token"})
        return FakeResponse(200, {"verification_status": self.verification_status})


class PayPalWebhookAdapterTests(unittest.TestCase):
    def _adapter(self, verification_status="SUCCESS"):
        return PayPalWebhookAdapter(
            FakePayPalClient(verification_status),
            "client-id",
            "client-secret",
            "webhook-id",
        )

    def _headers(self):
        return {
            "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            "PAYPAL-CERT-URL": "https://api-m.paypal.com/cert",
            "PAYPAL-TRANSMISSION-ID": "transmission-id",
            "PAYPAL-TRANSMISSION-SIG": "signature",
            "PAYPAL-TRANSMISSION-TIME": "2026-08-27T10:00:00Z",
        }

    def test_verified_deposit_advances_lead_once(self):
        adapter = self._adapter()
        lead = Lead("lead-paypal", "daily", state=State.SOW_GENERATED)
        raw_body = json.dumps({
            "id": "paypal-event-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": "deposit"},
        })

        self.assertTrue(adapter.verify_and_apply(raw_body, self._headers(), lead))
        self.assertFalse(adapter.verify_and_apply(raw_body, self._headers(), lead))
        self.assertEqual(lead.state, State.DEPOSIT_PAID)

    def test_invalid_signature_does_not_mutate_lead(self):
        adapter = self._adapter("FAILURE")
        lead = Lead("lead-paypal-invalid", "daily", state=State.SOW_GENERATED)
        raw_body = json.dumps({
            "id": "paypal-event-2",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": "deposit"},
        })

        with self.assertRaises(ValueError):
            adapter.verify_and_apply(raw_body, self._headers(), lead)
        self.assertEqual(lead.state, State.SOW_GENERATED)

    def test_unknown_capture_kind_is_rejected(self):
        adapter = self._adapter()
        lead = Lead("lead-paypal-unknown", "daily", state=State.SOW_GENERATED)
        raw_body = json.dumps({
            "id": "paypal-event-3",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": "something-else"},
        })

        with self.assertRaises(ValueError):
            adapter.verify_and_apply(raw_body, self._headers(), lead)


if __name__ == "__main__":
    unittest.main()