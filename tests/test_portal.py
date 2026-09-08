import csv
import io
import unittest

from agents.domain import Lead, State
from agents.portal import PortalService
from agents.progress import ProgressStatus


class PortalServiceTests(unittest.TestCase):
    def setUp(self):
        self.portal = PortalService()
        self.lead = Lead("lead-portal", "daily")
        self.slug = self.portal.publish_sandbox(
            self.lead,
            "Acme Research",
            [{"case_number": "A-1", "county": "Cook"}],
            "https://example.gov/cases",
        )

    def test_review_records_events_and_exports_sample(self):
        self.portal.record_interaction(self.slug, "preview.opened")
        self.portal.select_fields(self.slug, ["case_number", "county"])
        rows = list(csv.DictReader(io.StringIO(self.portal.export_csv(self.slug))))

        self.assertEqual(self.lead.state, State.CONVERSATIONAL_INTAKE)
        self.assertEqual(rows[0]["case_number"], "A-1")
        self.assertEqual(self.portal.get_sandbox(self.slug).events[-1]["event"], "sample.exported")

    def test_checkout_requires_sow(self):
        with self.assertRaises(ValueError):
            self.portal.request_checkout(self.slug)

        self.lead.transition(State.CONVERSATIONAL_INTAKE, "intake started")
        self.lead.transition(State.SOW_GENERATED, "scope approved")
        checkout = self.portal.request_checkout(self.slug)
        self.assertEqual(checkout["amount_cents"], 9900)  # $99 setup sprint deposit
        self.assertEqual(checkout["payment_provider"], "paypal")

    def test_scope_approval_unlocks_checkout(self):
        self.portal.select_fields(self.slug, ["case_number"])
        self.portal.approve_scope(self.slug)

        checkout = self.portal.request_checkout(self.slug)
        self.assertEqual(self.lead.state, State.SOW_GENERATED)
        self.assertEqual(checkout["payment_kind"], "setup_deposit")

    def test_scope_cannot_be_approved_without_selected_fields(self):
        with self.assertRaises(ValueError):
            self.portal.approve_scope(self.slug)

    def test_unknown_event_names_are_rejected(self):
        with self.assertRaises(ValueError):
            self.portal.record_interaction(self.slug, "Preview Opened")

    def test_build_progress_is_available_through_sandbox(self):
        self.portal.publish_build_progress(
            self.slug,
            "systems_architect",
            ProgressStatus.ACTIVE,
            "Validating data contracts",
        )

        progress = self.portal.build_progress(self.slug)
        self.assertEqual(progress[0]["role"], "systems_architect")
        self.assertEqual(progress[0]["status"], "ACTIVE")
        self.assertNotIn("content", progress[0])

    def test_intake_is_prefilled_from_research_and_marks_assumptions(self):
        form = self.portal.build_intake_form(self.slug, {
            "niche": "Probate research",
            "niche_confidence": "high",
            "jurisdiction": "Cook County, IL",
            "portal_name": "Cook County Probate",
            "portal_url": "https://example.gov/cases",
            "suggested_fields": ["case_number", "filing_date"],
            "recommended_tier": "daily",
            "delivery_destination": "Google Sheets",
        })

        fields = {assumption.key: assumption for assumption in form.assumptions}
        self.assertEqual(fields["niche"].value, "Probate research")
        self.assertEqual(fields["niche"].confidence, "high")
        self.assertTrue(fields["portal_url"].requires_confirmation)
        self.assertEqual(self.portal.get_sandbox(self.slug).events[-1]["event"], "intake.prefilled")


if __name__ == "__main__":
    unittest.main()