"""Unit and Integration Tests for SOS Entity Prospector and Local Business Prospector."""

import unittest
from unittest.mock import MagicMock, patch

from agents.sos_entity_prospector import SOSEntityProspector, DiscoveredSOSEntity
from agents.local_business_prospector import LocalBusinessProspector, DiscoveredLocalBusiness


class SOSAndLocalProspectorTests(unittest.TestCase):
    def setUp(self):
        self.sos_prospector = SOSEntityProspector()
        self.local_prospector = LocalBusinessProspector()

    @patch("agents.sos_entity_prospector.search_web")
    def test_sos_discover_new_registrations(self, mock_search_web):
        """Test discovering newly registered title and escrow companies from SOS registries."""
        mock_search_web.return_value = [
            {
                "title": "Lone Star Title Solutions LLC | Secretary of State Entity Filing",
                "url": "https://www.sos.state.tx.us/corp/filing/800112233",
                "snippet": "Formation date: 2026-06-15. Registered Agent: Robert Sterling. Filing #: 800112233. Austin, TX.",
            }
        ]

        entities = self.sos_prospector.discover_new_registrations(state_code="TX", keyword="Title Company", max_results=1)
        self.assertEqual(len(entities), 1)
        ent = entities[0]
        self.assertEqual(ent.company_name, "Lone Star Title Solutions LLC")
        self.assertEqual(ent.registered_agent, "Robert Sterling")
        self.assertEqual(ent.filing_number, "800112233")
        self.assertEqual(ent.state, "TX")

    @patch("agents.sos_entity_prospector.search_company_intelligence")
    @patch("agents.sos_entity_prospector.extract_contact_info_from_url")
    @patch("agents.sos_entity_prospector.find_linkedin_decision_maker")
    def test_enrich_sos_prospect(self, mock_linkedin, mock_extract_contact, mock_search_intel):
        """Test enriching newly formed entity into qualified prospect."""
        mock_search_intel.return_value = {"website": "https://www.lonestartitlesolutions.com"}
        mock_extract_contact.return_value = {
            "verified_email": "rsterling@lonestartitlesolutions.com",
            "verified_phone": "(512) 555-0144",
            "emails": ["rsterling@lonestartitlesolutions.com"],
        }
        mock_linkedin.return_value = {"name": "Robert Sterling", "role": "Principal / Owner"}

        ent = DiscoveredSOSEntity(
            company_name="Lone Star Title Solutions LLC",
            state="TX",
            entity_type="Title Company",
            registered_agent="Robert Sterling",
            filing_number="800112233",
        )

        prospect = self.sos_prospector.enrich_sos_prospect(ent)
        self.assertIsNotNone(prospect)
        self.assertEqual(prospect["company_name"], "Lone Star Title Solutions LLC")
        self.assertEqual(prospect["discovery_channel"], "SOS_NEW_BUSINESS")
        self.assertIn("Title Company operations in TX", prospect["pitch_body"])

    @patch("agents.local_business_prospector.search_web")
    def test_local_business_discover(self, mock_search_web):
        """Test local business discovery for title companies by city and state."""
        mock_search_web.return_value = [
            {
                "title": "Apex Title & Escrow Group - Houston, TX",
                "url": "https://www.apextitlehouston.com",
                "snippet": "Serving Harris County. Call (713) 555-0199. 1200 Post Oak Blvd, Houston, TX 77056.",
            }
        ]

        businesses = self.local_prospector.discover_local_operators(city="Houston", state="TX", category="Title Company", max_results=1)
        self.assertEqual(len(businesses), 1)
        b = businesses[0]
        self.assertEqual(b.business_name, "Apex Title & Escrow Group")
        self.assertEqual(b.phone, "(713) 555-0199")
        self.assertIn("1200 Post Oak Blvd", b.address)
        self.assertEqual(b.city, "Houston")
        self.assertEqual(b.state, "TX")

    @patch("agents.local_business_prospector.search_company_intelligence")
    @patch("agents.local_business_prospector.extract_contact_info_from_url")
    @patch("agents.local_business_prospector.find_linkedin_decision_maker")
    def test_enrich_local_prospect(self, mock_linkedin, mock_extract_contact, mock_search_intel):
        """Test local prospect enrichment with geo-targeted pitch."""
        mock_search_intel.return_value = {"website": "https://www.apextitlehouston.com"}
        mock_extract_contact.return_value = {
            "verified_email": "operations@apextitlehouston.com",
            "verified_phone": "(713) 555-0199",
            "emails": ["operations@apextitlehouston.com"],
        }
        mock_linkedin.return_value = {"name": "Patricia Adams", "role": "Escrow Branch Manager"}

        biz = DiscoveredLocalBusiness(
            business_name="Apex Title & Escrow Group",
            city="Houston",
            state="TX",
            county="Harris County",
            category="Title Company",
            phone="(713) 555-0199",
            portal_info={"portal_name": "Harris County Clerk & Deeds Registry", "portal_url": "https://cclerk.hctx.net"}
        )

        prospect = self.local_prospector.enrich_local_prospect(biz)
        self.assertIsNotNone(prospect)
        self.assertEqual(prospect["company_name"], "Apex Title & Escrow Group")
        self.assertEqual(prospect["discovery_channel"], "GOOGLE_MAPS_LOCAL")
        self.assertIn("Harris County Clerk & Deeds Registry", prospect["pitch_body"])
        self.assertIn("Houston area", prospect["pitch_body"])


if __name__ == "__main__":
    unittest.main()
