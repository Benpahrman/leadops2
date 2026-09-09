"""Unit and Integration Tests for County Filing Party Extractor."""

import unittest
from unittest.mock import MagicMock, patch

from agents.county_filing_extractor import (
    CountyFilingPartyExtractor,
    DiscoveredFilingEntity,
)


class CountyFilingPartyExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = CountyFilingPartyExtractor()

    def test_extract_candidates_from_structured_dockets(self):
        """Test extraction of attorneys and law firms from structured docket records."""
        records = [
            {
                "case_number": "2026-P-00124",
                "decedent_name": "Estate of Arthur Pendelton",
                "attorney_name": "Sarah Jenkins",
                "law_firm": "Jenkins & Morrow Probate Litigation PLLC",
                "filing_date": "2026-08-15",
                "est_value": "$1,450,000",
                "status": "PETITION FILED",
                "source_url": "https://cookcountyclerkofcourt.org/probate/124",
            },
            {
                "case_number": "2026-P-00125",
                "decedent_name": "Estate of Robert Henderson",
                "attorney_name": "Marcus Vance",
                "law_firm": "Jenkins & Morrow Probate Litigation PLLC",
                "filing_date": "2026-08-16",
                "est_value": "$890,000",
                "status": "LETTERS ISSUED",
                "source_url": "https://cookcountyclerkofcourt.org/probate/125",
            },
            {
                "case_number": "2026-P-00126",
                "decedent_name": "Estate of Linda Miller",
                "attorney_name": "Hon. Judge William Baxter",  # Court / Government entity
                "law_firm": "Circuit Court of Cook County",
                "filing_date": "2026-08-16",
                "status": "ORDER ENTERED",
            }
        ]

        candidates = self.extractor.extract_candidates_from_records(
            records=records,
            portal_name="Cook County Probate Court",
            jurisdiction="Cook County, IL",
            source_url="https://cookcountyclerkofcourt.org",
        )

        # Disallowed court entity should be filtered out
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.entity_name, "Jenkins & Morrow Probate Litigation PLLC")
        self.assertEqual(c.attorney_name, "Sarah Jenkins")
        self.assertEqual(c.entity_type, "law_firm")
        self.assertEqual(c.filing_case_number, "2026-P-00124")
        self.assertEqual(c.filing_frequency, 2)  # Filed twice!

    def test_extract_candidates_from_unstructured_details(self):
        """Test extraction of title companies and lenders from unstructured descriptions."""
        records = [
            {
                "record_id": "TX-UCC-998811",
                "details": "Financing Statement filed by Lone Star Asset Lending LLC against debtor equipment.",
                "date": "2026-07-20",
                "source_url": "https://sos.state.tx.us/ucc/998811",
            },
            {
                "record_id": "FL-LIEN-445522",
                "details": "Claim of Lien recorded. Attorney: David Thorne, Thorne & Associates Title Agency.",
                "date": "2026-08-01",
                "source_url": "https://occompt.com/liens/445522",
            }
        ]

        candidates = self.extractor.extract_candidates_from_records(
            records=records,
            portal_name="Texas SOS & Orange County Registry",
            jurisdiction="Regional",
        )

        self.assertEqual(len(candidates), 2)
        names = [c.entity_name for c in candidates]
        self.assertTrue(any("Lone Star Asset Lending" in n for n in names))
        self.assertTrue(any("Thorne" in n for n in names))

    @patch("agents.county_filing_extractor.search_company_intelligence")
    @patch("agents.county_filing_extractor.extract_contact_info_from_url")
    @patch("agents.county_filing_extractor.find_linkedin_decision_maker")
    def test_enrich_filing_prospect(self, mock_linkedin, mock_extract_contact, mock_search_intel):
        """Test complete enrichment of discovered filing entity into qualified target."""
        mock_search_intel.return_value = {
            "website": "https://www.jenkinsmorrowlaw.com",
            "company_name": "Jenkins & Morrow Probate Litigation PLLC"
        }
        mock_extract_contact.return_value = {
            "verified_email": "sjenkins@jenkinsmorrowlaw.com",
            "verified_phone": "(312) 555-0199",
            "emails": ["sjenkins@jenkinsmorrowlaw.com"],
            "phones": ["(312) 555-0199"],
        }
        mock_linkedin.return_value = {
            "name": "Sarah Jenkins",
            "role": "Managing Partner",
            "linkedin_url": "https://linkedin.com/in/sarah-jenkins-probate",
        }

        entity = DiscoveredFilingEntity(
            entity_name="Jenkins & Morrow Probate Litigation PLLC",
            attorney_name="Sarah Jenkins",
            entity_type="law_firm",
            filing_case_number="2026-P-00124",
            filing_date="2026-08-15",
            portal_name="Cook County Probate Court",
            jurisdiction="Cook County, IL",
            source_record_url="https://cookcountyclerkofcourt.org",
        )

        prospect = self.extractor.enrich_filing_prospect(entity)
        self.assertIsNotNone(prospect)
        self.assertEqual(prospect["company_name"], "Jenkins & Morrow Probate Litigation PLLC")
        self.assertEqual(prospect["contact_name"], "Sarah Jenkins")
        self.assertEqual(prospect["contact_email"], "sjenkins@jenkinsmorrowlaw.com")
        self.assertEqual(prospect["discovery_channel"], "COUNTY_FILING_PARTY")
        self.assertEqual(prospect["filing_case_number"], "2026-P-00124")
        self.assertIn("matter #2026-P-00124", prospect["pitch_body"])
        self.assertIn("Cook County Probate Court", prospect["pitch_body"])


if __name__ == "__main__":
    unittest.main()
