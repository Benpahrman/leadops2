import unittest

from agents.domain import InvalidTransition, Lead, PaymentEvent, State


class LeadLifecycleTests(unittest.TestCase):
    def test_paid_build_preview_and_delivery_path(self):
        lead = Lead("lead-1", "daily")
        lead.transition(State.REVIEW, "sandbox published")
        lead.select_fields(["case_number", "filing_date"])
        lead.transition(State.CONVERSATIONAL_INTAKE, "fields selected")
        lead.transition(State.SOW_GENERATED, "scope approved")
        lead.record_payment(PaymentEvent.DEPOSIT_PAID)
        lead.transition(State.DEV_BUILDING, "deposit webhook")
        lead.qa_score = 96.2
        lead.preview_rows = 25
        lead.transition(State.ESCROW_PREVIEW, "qa passed")
        lead.record_payment(PaymentEvent.FINAL_PAID)
        lead.transition(State.DELIVERED, "final payment webhook")
        lead.record_payment(PaymentEvent.SUBSCRIPTION_ACTIVE)

        self.assertEqual(lead.state, State.DELIVERED)
        self.assertTrue(lead.subscription_active)

    def test_escrow_requires_quality_and_exact_preview_size(self):
        lead = Lead("lead-2", "ai", state=State.DEV_BUILDING)
        lead.qa_score = 94.9
        lead.preview_rows = 25
        with self.assertRaises(InvalidTransition):
            lead.transition(State.ESCROW_PREVIEW, "qa failed")

        lead.qa_score = 99
        lead.preview_rows = 24
        with self.assertRaises(InvalidTransition):
            lead.transition(State.ESCROW_PREVIEW, "incomplete preview")

    def test_audit_log_uses_actual_previous_state(self):
        lead = Lead("lead-audit", "weekly", state=State.DEV_BUILDING)
        lead.qa_score = 95
        lead.preview_rows = 25
        lead.transition(State.ESCROW_PREVIEW, "qa passed")

        self.assertEqual(lead.audit_log[-1]["from"], State.DEV_BUILDING.value)

    def test_buyout_can_deliver_without_subscription(self):
        lead = Lead("lead-3", "buyout", state=State.SOW_GENERATED)
        lead.record_payment(PaymentEvent.DEPOSIT_PAID)
        lead.transition(State.DEV_BUILDING, "deposit webhook")
        lead.qa_score = 95
        lead.preview_rows = 25
        lead.transition(State.ESCROW_PREVIEW, "qa passed")
        lead.record_payment(PaymentEvent.BUYOUT_PAID)
        lead.transition(State.DELIVERED, "buyout payment webhook")

    def test_blocked_needs_review_transition(self):
        lead = Lead("lead-blocked", "daily", state=State.DEV_BUILDING)
        lead.transition(State.BLOCKED_NEEDS_REVIEW, "Target triggered Cloudflare CAPTCHA")
        self.assertEqual(lead.state, State.BLOCKED_NEEDS_REVIEW)
        self.assertEqual(lead.audit_log[-1]["to"], State.BLOCKED_NEEDS_REVIEW.value)

        # Operator can review and unblock back to DEV_BUILDING or ARCHIVED
        lead.transition(State.DEV_BUILDING, "Operator resolved proxy/access issue")
        self.assertEqual(lead.state, State.DEV_BUILDING)

    def test_tier_aliases_and_fallback(self):
        lead_a = Lead("lead-tier-a", "A")
        self.assertEqual(lead_a.tier.name, "Daily Sync")
        self.assertEqual(lead_a.tier_key, "daily")

        lead_b = Lead("lead-tier-b", "tier_b")
        self.assertEqual(lead_b.tier.name, "Weekly Sync")

        lead_unknown = Lead("lead-custom", "legacy-unknown-tier")
        self.assertEqual(lead_unknown.tier.name, "Weekly Sync")


if __name__ == "__main__":
    unittest.main()