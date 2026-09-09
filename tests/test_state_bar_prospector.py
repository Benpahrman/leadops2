"""Unit and Integration Tests for State Bar Association Directory Prospector."""

import unittest
from unittest.mock import MagicMock, patch

from agents.state_bar_prospector import (
    StateBarProspector,
    DiscoveredBarAttorney,
)


class StateBarProspectorTests(unittest.TestCase):
    def setUp(self):
        self.prospector = StateBarProspector()

    @patch("agents.state_bar_prospector.search_web")
    def test_discover_attorneys(self, mock_search_web):
        """Test searching State Bar directory listings for probate and real estate attorneys."""
        mock_search_web.return_value = [
            {
                "title": "Marcus Aurelius Vance - Probate & Trust Attorney | State Bar of Texas",
                "url": "https://www.texasbar.com/attorneys/12345678",
                "snippet": "Licensed 2012. Active member in good standing. Bar No: 24089112. Practice: Probate and Estate Planning.",
            },
            {
                "title": "Elena Rostova - Rostova Title & Real Estate Law PC",
                "url": "https://www.texasbar.com/attorneys/87654321",
                "snippet": "State Bar of Texas Member. Bar Number: 24099233. Houston, TX.",
            }
        ]

        attorneys = self.prospector.discover_attorneys(
            state_code="TX",
            practice_area="Probate and Estate Administration",
            max_results=2,
        )

        self.assertEqual(len(attorneys), 2)
        atty1 = attorneys[0]
        self.assertEqual(atty1.attorney_name, "Marcus Aurelius Vance")
        self.assertEqual(atty1.state, "TX")
        self.assertEqual(atty1.bar_number, "24089112")
        self.assertEqual(atty1.practice_area, "Probate and Estate Administration")

    def test_parse_attorney_entry(self):
        """Test parsing attorney name, firm name, and bar number from directory snippets."""
        title = "Jonathan C. Meyers - Meyers Estate Counsel PLLC | Find a Lawyer"
        snip = "Active member. Bar #: 0998822. Dallas, TX."
        name, firm, bar_no = self.prospector._parse_attorney_entry(title, snip)

        self.assertEqual(name, "Jonathan C. Meyers")
        self.assertEqual(firm, "Meyers Estate Counsel PLLC")
        self.assertEqual(bar_no, "0998822")

    @patch("agents.state_bar_prospector.search_company_intelligence")
    @patch("agents.state_bar_prospector.extract_contact_info_from_url")
    @patch("agents.state_bar_prospector.find_linkedin_decision_maker")
    def test_enrich_bar_prospect(self, mock_linkedin, mock_extract_contact, mock_search_intel):
        """Test enrichment of bar attorney into qualified target with State Bar pitch."""
        mock_search_intel.return_value = {
            "website": "https://www.meyersestatecounsel.com",
            "company_name": "Meyers Estate Counsel PLLC"
        }
        mock_extract_contact.return_value = {
            "verified_email": "jmeyers@meyersestatecounsel.com",
            "verified_phone": "(214) 555-0188",
            "emails": ["jmeyers@meyersestatecounsel.com"],
        }
        mock_linkedin.return_value = {
            "name": "Jonathan Meyers",
            "role": "Managing Partner",
            "linkedin_url": "https://linkedin.com/in/jonathan-meyers-probate",
        }

        atty = DiscoveredBarAttorney(
            attorney_name="Jonathan Meyers",
            firm_name="Meyers Estate Counsel PLLC",
            state="TX",
            practice_area="Probate and Estate Administration",
            bar_number="0998822",
            target_portal={
                "portal_name": "Dallas County Probate Court",
                "target_url": "https://www.dallascounty.org/probate",
                "jurisdiction": "Dallas County, TX",
            }
        )

        prospect = self.prospector.enrich_bar_prospect(atty)
        self.assertIsNotNone(prospect)
        self.assertEqual(prospect["company_name"], "Meyers Estate Counsel PLLC")
        self.assertEqual(prospect["contact_name"], "Jonathan Meyers")
        self.assertEqual(prospect["discovery_channel"], "STATE_BAR_DIRECTORY")
        self.assertEqual(prospect["bar_number"], "0998822")
        self.assertIn("State Bar of Texas", prospect["pitch_body"])
        self.assertIn("Dallas County Probate Court", prospect["pitch_body"])


if __name__ == "__main__":
    unittest.main()
