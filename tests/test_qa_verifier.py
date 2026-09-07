"""Unit and integration tests for QA live site ground-truth extraction and scraper data parity verification."""

import unittest
from unittest.mock import patch, MagicMock

from agents.build_loop import BuildLoop, BuildPhase
from agents.tools.qa_verifier import (
    compare_ground_truth_parity,
    fetch_site_ground_truth,
    verify_scraper_against_live_site,
)
from agents.llm_client import LLMAgentEngine


class LiveSiteQAVerifierTests(unittest.TestCase):
    def test_parity_check_identical_records_passes(self):
        """When the scraper extracted the exact same records as on the site, parity should be 100%."""
        site_records = [
            {"case_number": "2026-P-101", "filing_date": "2026-03-01", "title": "Estate of John Doe", "status": "ACTIVE"},
            {"case_number": "2026-P-102", "filing_date": "2026-03-02", "title": "Estate of Jane Smith", "status": "PENDING"},
        ]
        scraped_records = [
            {"case_number": "2026-p-101", "filing_date": "2026-03-01", "title": "Estate of John Doe", "status": "ACTIVE"},
            {"case_number": "2026-P-102", "filing_date": "2026-03-02", "title": "Estate of Jane Smith", "status": "PENDING"},
        ]
        fields = ["case_number", "filing_date", "title", "status"]

        report = compare_ground_truth_parity(site_records, scraped_records, fields)

        self.assertTrue(report["passed"])
        self.assertEqual(report["parity_score"], 100.0)
        self.assertEqual(len(report["discrepancies"]), 0)
        self.assertEqual(report["field_accuracies"]["case_number"], 1.0)
        self.assertEqual(report["field_accuracies"]["filing_date"], 1.0)

    def test_parity_check_detects_field_discrepancies(self):
        """When the scraper extracted wrong dates or corrupted names, QA catches the exact discrepancies."""
        site_records = [
            {"case_number": "2026-P-101", "filing_date": "2026-03-01", "title": "Estate of John Doe", "status": "ACTIVE"},
            {"case_number": "2026-P-102", "filing_date": "2026-03-02", "title": "Estate of Jane Smith", "status": "PENDING"},
        ]
        # Scraper misparsed row 1 filing date and row 2 title
        scraped_records = [
            {"case_number": "2026-P-101", "filing_date": "2025-11-20", "title": "Estate of John Doe", "status": "ACTIVE"},
            {"case_number": "2026-P-102", "filing_date": "2026-03-02", "title": "UNKNOWN", "status": "PENDING"},
        ]
        fields = ["case_number", "filing_date", "title", "status"]

        report = compare_ground_truth_parity(site_records, scraped_records, fields)

        self.assertFalse(report["passed"])
        self.assertLess(report["parity_score"], 95.0)
        self.assertEqual(len(report["discrepancies"]), 2)

        # Check exact discrepancy details
        discrepancy_fields = [d["field"] for d in report["discrepancies"]]
        self.assertIn("filing_date", discrepancy_fields)
        self.assertIn("title", discrepancy_fields)

        date_disc = next(d for d in report["discrepancies"] if d["field"] == "filing_date")
        self.assertEqual(date_disc["expected_site_value"], "2026-03-01")
        self.assertEqual(date_disc["scraped_value"], "2025-11-20")

    def test_outside_qa_live_site_audit_rejects_discrepancies_and_replans(self):
        """BuildLoop.evaluate_live_site_parity_qa fails and transitions to REPLAN if scraper data doesn't match site data."""
        loop = BuildLoop()
        plan = loop.start_plan(["extract court records"], ["data_matches_live_site"])
        loop.start_team_build(plan)

        site_data = [
            {"case_number": "TX-9901", "filing_date": "2026-01-10", "status": "FILED"},
        ]
        mismatched_scraped_data = [
            {"case_number": "TX-0000", "filing_date": "1999-01-01", "status": "CLOSED"},
        ]

        with patch("agents.tools.qa_verifier.fetch_site_ground_truth", return_value=site_data), \
             patch("agents.tools.qa_verifier.run_scraper_extraction", return_value=mismatched_scraped_data):

            passed = loop.evaluate_live_site_parity_qa(
                target_url="https://county.gov/records",
                selected_fields=["case_number", "filing_date", "status"],
                candidate_code="async def run_pipeline(): pass",
            )

            self.assertFalse(passed)
            self.assertEqual(loop.phase, BuildPhase.REPLAN)
            self.assertIn("discrepancies", loop.last_qa_report)
            self.assertGreater(len(loop.last_qa_report["discrepancies"]), 0)

            # Replan back to PM
            loop.begin_replan()
            self.assertEqual(loop.phase, BuildPhase.PLANNING)

    def test_outside_qa_live_site_audit_approves_when_parity_verified(self):
        """BuildLoop.evaluate_live_site_parity_qa passes and transitions to ESCROW_READY when scraper matches site."""
        loop = BuildLoop()
        plan = loop.start_plan(["extract court records"], ["data_matches_live_site"])
        loop.start_team_build(plan)

        verified_data = [
            {"case_number": "TX-9901", "filing_date": "2026-01-10", "status": "FILED"},
            {"case_number": "TX-9902", "filing_date": "2026-01-11", "status": "PENDING"},
        ]

        with patch("agents.tools.qa_verifier.fetch_site_ground_truth", return_value=verified_data), \
             patch("agents.tools.qa_verifier.run_scraper_extraction", return_value=verified_data):

            passed = loop.evaluate_live_site_parity_qa(
                target_url="https://county.gov/records",
                selected_fields=["case_number", "filing_date", "status"],
                candidate_code="async def run_pipeline(): pass",
            )

            self.assertTrue(passed)
            self.assertEqual(loop.phase, BuildPhase.ESCROW_READY)
            self.assertEqual(loop.last_qa_report["parity_report"]["parity_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
