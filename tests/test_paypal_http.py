import json
import unittest

from agents.paypal_http import AsyncPayPalHttpClient, PayPalHttpClient


class FakeResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"id": "ORDER-1"}).encode()


class PayPalHttpTests(unittest.TestCase):
    def test_posts_json_and_parses_response(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse()

        response = PayPalHttpClient(opener, 5).post(
            "https://api-m.sandbox.paypal.com/v2/checkout/orders",
            headers={"Content-Type": "application/json"},
            json={"intent": "CAPTURE"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], "ORDER-1")
        self.assertEqual(json.loads(calls[0][0].data), {"intent": "CAPTURE"})
        self.assertEqual(calls[0][1], 5)

    def test_rejects_mixed_body_types(self):
        with self.assertRaises(ValueError):
            PayPalHttpClient().post(
                "https://example.test",
                headers={},
                data={"grant_type": "client_credentials"},
                json={"intent": "CAPTURE"},
            )

    def test_posts_form_data(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            return FakeResponse()

        PayPalHttpClient(opener).post(
            "https://example.test/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
        )

        self.assertEqual(calls[0].data.decode(), "grant_type=client_credentials")

    def test_async_client_initialization(self):
        client = AsyncPayPalHttpClient(timeout_seconds=15.0)
        self.assertEqual(client.timeout_seconds, 15.0)
        with self.assertRaises(ValueError):
            AsyncPayPalHttpClient(timeout_seconds=-1)


if __name__ == "__main__":
    unittest.main()