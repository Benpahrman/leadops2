import unittest

from agents.portal import PortalService
from agents.scout_pipeline import ScoutPortalPipeline


class ScoutPipelineTests(unittest.TestCase):
    def test_verified_evidence_creates_sandbox_and_intake(self):
        candidate = ScoutPortalPipeline(PortalService()).publish_candidate(
            "Acme Research",
            "lead-scout-1",
            [{"url": "https://example.gov/cases", "title": "Public cases"}],
            "https://example.gov/cases",
            [{"case_number": "A-1"}],
            {
                "niche": "Probate research",
                "portal_name": "Public cases",
                "portal_url": "https://example.gov/cases",
            },
        )

        self.assertEqual(candidate.slug, "acme-research-lead-scout-1")
        self.assertEqual(candidate.intake.slug, candidate.slug)

    def test_unverified_source_cannot_be_published(self):
        with self.assertRaises(ValueError):
            ScoutPortalPipeline(PortalService()).publish_candidate(
                "Acme Research",
                "lead-scout-2",
                [{"url": "https://other.gov"}],
                "https://example.gov/cases",
                [{"case_number": "A-1"}],
                {},
            )