"""End-to-End Integration Tests for High-ROI Multi-Channel Scout Discovery Engine."""

import unittest
from unittest.mock import MagicMock, patch

from agents.scout_runner import ScoutBackgroundWorker
from agents.domain import State
from agents.storage import InMemoryStorageBackend
from agents.portal import PortalService
from agents.county_filing_extractor import DiscoveredFilingEntity
from agents.state_bar_prospector import DiscoveredBarAttorney
from agents.sos_entity_prospector import DiscoveredSOSEntity
from agents.local_business_prospector import DiscoveredLocalBusiness


class HighROIDiscoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.storage = InMemoryStorageBackend()
        self.portal = PortalService(storage=self.storage)
        self.mock_llm_engine = MagicMock()
        self.mock_llm_engine.run_lead_enrichment_agent.return_value = {
            "verified_email": "partner@jenkinsmorrowlaw.com",
            "verified_phone": "(312) 555-0199",
            "cleaned_sample_records": [],
        }
        self.mock_llm_engine.run_scout_discovery_agent.return_value = {
            "company_name": "Test Commercial Practice",
            "contact_name": "Sarah Jenkins",
            "contact_role": "Managing Partner",
            "contact_email": "test@testlaw.com",
            "contact_phone": "(312) 555-0199",
            "website": "https://testlaw.com",
            "pain_point": "Need automated court records",
            "pitch_subject": "automated court records",
            "pitch_body": "automated court records feed",
        }
        self.mock_llm_engine.classify_target_portal.return_value = {
            "niche": "Legal Practice & Court Docket Administration",
            "portal_name": "Cook County Probate Division Court Portal",
            "target_url": "https://www.cookcountyclerkofcourt.org/",
            "jurisdiction": "Cook County, IL (Chicago)",
            "pain_point": "Manual monitoring of newly filed Cook County probate petitions.",
            "tier_key": "daily",
        }
        self.worker = ScoutBackgroundWorker(
            storage=self.storage,
            portal=self.portal,
            llm_engine=self.mock_llm_engine,
        )

    @patch("agents.scout_runner.generate_browser_headers")
    @patch("agents.scout_runner.probe_waf_signatures")
    @patch("httpx.Client")
    def test_county_filing_party_discovery_cycle(self, mock_httpx_class, mock_probe_waf, mock_gen_headers):
        """Verify complete discovery cycle through County Filing Party extraction (Priority 1)."""
        mock_probe_waf.return_value = {"detected_waf": None, "is_safe_to_scrape": True}
        mock_resp = MagicMock(status_code=200, text="<html>County Court Docket Portal</html>", headers={})
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx_class.return_value = mock_client

        mock_discovered = [
            DiscoveredFilingEntity(
                entity_name="Jenkins & Morrow Probate Litigation PLLC",
                attorney_name="Sarah Jenkins",
                entity_type="law_firm",
                filing_case_number="2026-P-00889",
                filing_date="2026-08-20",
                portal_name="Cook County Probate Division Court Portal",
                jurisdiction="Cook County, IL (Chicago)",
                source_record_url="https://www.cookcountyclerkofcourt.org/",
            )
        ]
        self.worker.county_extractor.extract_candidates_from_records = MagicMock(return_value=mock_discovered)
        self.worker.county_extractor.enrich_filing_prospect = MagicMock(return_value={
            "company_name": "Jenkins & Morrow Probate Litigation PLLC",
            "contact_name": "Sarah Jenkins",
            "contact_role": "Attorney of Record / Managing Partner",
            "contact_email": "sjenkins@jenkinsmorrowlaw.com",
            "contact_phone": "(312) 555-0199",
            "linkedin_url": "https://linkedin.com/in/sarah-jenkins-probate",
            "website": "https://www.jenkinsmorrowlaw.com",
            "discovery_channel": "COUNTY_FILING_PARTY",
            "niche": "Legal Practice & Court Docket Administration",
            "pain_point": "Manual monitoring of newly filed Cook County probate petitions.",
            "target_url": "https://www.cookcountyclerkofcourt.org/",
            "portal_name": "Cook County Probate Division Court Portal",
            "jurisdiction": "Cook County, IL (Chicago)",
            "filing_case_number": "2026-P-00889",
            "suggested_fields": ["case_number", "filing_date", "matter_title", "status"],
            "tier_key": "daily",
            "sample_data": [{"case_number": "2026-P-00889", "status": "PETITION FILED"}],
            "pitch_subject": "cook filings for jenkins",
            "pitch_body": "Saw your firm filed matter #2026-P-00889 in Cook County Probate Court. Curious if you pull daily updates manually?",
        })

        result = self.worker.discover_next_candidate(channel="county_filing_party")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result["company_name"], "Jenkins & Morrow Probate Litigation PLLC")

        # Verify lead created in storage with discovery channel and filing case number
        lead = self.storage.get_lead(result["lead_id"])
        self.assertIsNotNone(lead)
        self.assertEqual(lead.discovery_channel, "COUNTY_FILING_PARTY")
        self.assertEqual(lead.filing_case_number, "2026-P-00889")
        self.assertEqual(lead.state, State.PITCH_PENDING_APPROVAL)
        self.assertIn("2026-P-00889", lead.outreach_body)

    @patch("agents.scout_runner.generate_browser_headers")
    @patch("agents.scout_runner.probe_waf_signatures")
    @patch("httpx.Client")
    def test_state_bar_directory_discovery_cycle(self, mock_httpx_class, mock_probe_waf, mock_gen_headers):
        """Verify complete discovery cycle through State Bar directory prospector (Priority 2)."""
        mock_probe_waf.return_value = {"detected_waf": None, "is_safe_to_scrape": True}
        mock_resp = MagicMock(status_code=200, text="<html>State Bar Portal</html>", headers={})
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx_class.return_value = mock_client

        mock_attorneys = [
            DiscoveredBarAttorney(
                attorney_name="David Sterling",
                firm_name="Sterling Title & Estate Law PLLC",
                state="TX",
                practice_area="Probate and Estate Administration",
                bar_number="24099881",
                target_portal={
                    "portal_name": "Harris County District Clerk & County Clerk",
                    "target_url": "https://www.cclerk.hctx.net/",
                    "jurisdiction": "Harris County, TX (Houston)",
                    "dataset_key": "harris-foreclosure",
                }
            )
        ]
        self.worker.bar_prospector.discover_attorneys = MagicMock(return_value=mock_attorneys)
        self.worker.bar_prospector.enrich_bar_prospect = MagicMock(return_value={
            "company_name": "Sterling Title & Estate Law PLLC",
            "contact_name": "David Sterling",
            "contact_role": "Managing Partner",
            "contact_email": "dsterling@sterlingestatelaw.com",
            "contact_phone": "(713) 555-0177",
            "website": "https://www.sterlingestatelaw.com",
            "discovery_channel": "STATE_BAR_DIRECTORY",
            "niche": "Probate and Estate Administration",
            "pain_point": "Manual court record monitoring.",
            "target_url": "https://www.cclerk.hctx.net/",
            "portal_name": "Harris County District Clerk & County Clerk",
            "jurisdiction": "Harris County, TX (Houston)",
            "bar_number": "24099881",
            "suggested_fields": ["case_number", "status"],
            "tier_key": "daily",
            "sample_data": [{"record_id": "HC-101", "status": "ACTIVE"}],
            "pitch_subject": "probate docket feeds for sterling",
            "pitch_body": "Saw your practice listed with the State Bar of Texas. We build automated feeds for Harris County dockets.",
        })

        result = self.worker.discover_next_candidate(channel="state_bar")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result["company_name"], "Sterling Title & Estate Law PLLC")

        lead = self.storage.get_lead(result["lead_id"])
        self.assertEqual(lead.discovery_channel, "STATE_BAR_DIRECTORY")
        self.assertEqual(lead.state, State.PITCH_PENDING_APPROVAL)
        self.assertIn("State Bar of Texas", lead.outreach_body)

    @patch("agents.scout_runner.generate_browser_headers")
    @patch("agents.scout_runner.probe_waf_signatures")
    @patch("httpx.Client")
    def test_local_business_discovery_cycle(self, mock_httpx_class, mock_probe_waf, mock_gen_headers):
        """Verify complete discovery cycle through Local Business & Maps prospector (Priority 4)."""
        mock_probe_waf.return_value = {"detected_waf": None, "is_safe_to_scrape": True}
        mock_resp = MagicMock(status_code=200, text="<html>Local Business Registry</html>", headers={})
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx_class.return_value = mock_client

        mock_local = [
            DiscoveredLocalBusiness(
                business_name="Orlando Title & Escrow Partners",
                city="Orlando",
                state="FL",
                county="Orange County",
                category="Title Company",
                phone="(407) 555-0199",
                portal_info={"portal_name": "Orange County Comptroller", "portal_url": "https://www.occompt.com/"}
            )
        ]
        self.worker.local_prospector.discover_local_operators = MagicMock(return_value=mock_local)
        self.worker.local_prospector.enrich_local_prospect = MagicMock(return_value={
            "company_name": "Orlando Title & Escrow Partners",
            "contact_name": "Amanda Cross",
            "contact_role": "Branch Escrow Officer",
            "contact_email": "across@orlandotitlepartners.com",
            "contact_phone": "(407) 555-0199",
            "website": "https://www.orlandotitlepartners.com",
            "discovery_channel": "GOOGLE_MAPS_LOCAL",
            "niche": "Regional Title Company Operations",
            "pain_point": "Manual daily pulling of newly recorded deeds in Orange County.",
            "target_url": "https://www.occompt.com/",
            "portal_name": "Orange County Comptroller & Clerk Registry",
            "jurisdiction": "Orlando, Orange County, FL",
            "suggested_fields": ["doc_id", "status"],
            "tier_key": "daily",
            "sample_data": [{"doc_id": "ORL-001", "status": "RECORDED"}],
            "pitch_subject": "orlando recordings for orlando title",
            "pitch_body": "Saw your practice serving Orlando. We build automated feeds for Orange County recordings.",
        })

        result = self.worker.discover_next_candidate(channel="local_business")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result["company_name"], "Orlando Title & Escrow Partners")

        lead = self.storage.get_lead(result["lead_id"])
        self.assertEqual(lead.discovery_channel, "GOOGLE_MAPS_LOCAL")
        self.assertEqual(lead.state, State.PITCH_PENDING_APPROVAL)

    @patch("agents.scout_runner.generate_browser_headers")
    @patch("agents.scout_runner.probe_waf_signatures")
    @patch("httpx.Client")
    def test_sos_entity_discovery_cycle(self, mock_httpx_class, mock_probe_waf, mock_gen_headers):
        """Verify complete discovery cycle through Secretary of State new business registrations (Priority 6)."""
        mock_probe_waf.return_value = {"detected_waf": None, "is_safe_to_scrape": True}
        mock_resp = MagicMock(status_code=200, text="<html>SOS Registry</html>", headers={})
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx_class.return_value = mock_client

        mock_sos = [
            DiscoveredSOSEntity(
                company_name="Lone Star Abstract & Settlement LLC",
                state="TX",
                entity_type="Title Company",
                registered_agent="Bradley Cooper",
                filing_number="800998877",
            )
        ]
        self.worker.sos_prospector.discover_new_registrations = MagicMock(return_value=mock_sos)
        self.worker.sos_prospector.enrich_sos_prospect = MagicMock(return_value={
            "company_name": "Lone Star Abstract & Settlement LLC",
            "contact_name": "Bradley Cooper",
            "contact_role": "Managing Principal",
            "contact_email": "bcooper@lonestarsettlement.com",
            "contact_phone": "(512) 555-0188",
            "website": "https://www.lonestarsettlement.com",
            "discovery_channel": "SOS_NEW_BUSINESS",
            "niche": "Commercial Operations (Title Company)",
            "pain_point": "Setting up automated daily public record feeds for new operations.",
            "target_url": "https://data.texas.gov/",
            "portal_name": "Texas Secretary of State Corporate Registry",
            "jurisdiction": "Texas Statewide",
            "suggested_fields": ["entity_id", "status"],
            "tier_key": "weekly",
            "sample_data": [{"entity_id": "800998877", "status": "ACTIVE"}],
            "pitch_subject": "title company records for lone star",
            "pitch_body": "Saw your registration for Title Company operations in Texas. We stream automated county filings.",
        })

        result = self.worker.discover_next_candidate(channel="sos_entity")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result["company_name"], "Lone Star Abstract & Settlement LLC")

        lead = self.storage.get_lead(result["lead_id"])
        self.assertEqual(lead.discovery_channel, "SOS_NEW_BUSINESS")
        self.assertEqual(lead.state, State.PITCH_PENDING_APPROVAL)


if __name__ == "__main__":
    unittest.main()
