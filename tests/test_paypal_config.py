import unittest
from unittest import mock

from agents.paypal_config import PayPalSettings


class PayPalSettingsTests(unittest.TestCase):
    def test_sandbox_is_the_default_mode_and_endpoint(self):
        settings = PayPalSettings("id", "secret", "webhook")
        self.assertEqual(settings.mode, "sandbox")
        self.assertEqual(settings.base_url, "https://api-m.sandbox.paypal.com")

    def test_live_mode_uses_live_endpoint(self):
        settings = PayPalSettings("id", "secret", "webhook", mode="live")
        self.assertEqual(settings.base_url, "https://api-m.paypal.com")

    def test_environment_requires_credentials(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                PayPalSettings.from_environment()

    def test_environment_reads_sandbox_settings_without_exposing_values(self):
        values = {
            "PAYPAL_CLIENT_ID": "sandbox-id",
            "PAYPAL_CLIENT_SECRET": "sandbox-secret",
            "PAYPAL_WEBHOOK_ID": "sandbox-webhook",
            "PAYPAL_MODE": "sandbox",
        }
        with mock.patch.dict("os.environ", values, clear=True):
            settings = PayPalSettings.from_environment()

        self.assertEqual(settings.base_url, "https://api-m.sandbox.paypal.com")
        self.assertEqual(settings.client_id, "sandbox-id")


if __name__ == "__main__":
    unittest.main()