import unittest

from agents.domain import Lead, PaymentEvent, State
from agents.payments import PaymentEventProcessor


class PaymentEventProcessorTests(unittest.TestCase):
    def test_duplicate_webhook_is_ignored(self):
        lead = Lead("lead-4", "weekly", state=State.SOW_GENERATED)
        processor = PaymentEventProcessor()

        self.assertTrue(processor.apply(lead, "paypal-evt-1", PaymentEvent.DEPOSIT_PAID))
        self.assertFalse(processor.apply(lead, "paypal-evt-1", PaymentEvent.DEPOSIT_PAID))
        self.assertEqual(lead.state, State.DEPOSIT_PAID)
        self.assertEqual(len(lead.audit_log), 1)

    def test_missing_event_id_is_rejected(self):
        lead = Lead("lead-5", "weekly", state=State.SOW_GENERATED)
        with self.assertRaises(ValueError):
            PaymentEventProcessor().apply(lead, "", PaymentEvent.DEPOSIT_PAID)


if __name__ == "__main__":
    unittest.main()