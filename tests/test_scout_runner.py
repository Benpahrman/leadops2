import unittest
from unittest.mock import MagicMock, patch
from agents.scout_runner import VERTICAL_CATALOG, ScoutBackgroundWorker, B2BWebScoutWorker
from agents.datasets import AUTHENTIC_REGISTRY_DATASETS
from agents.domain import State
from agents.storage import InMemoryStorageBackend
from agents.portal import PortalService

class ScoutRunnerTests(unittest.TestCase):
    def test_vertical_catalog_keys_exist_in_authentic_registry_datasets(self):
        """Verify that every dataset_key defined in VERTICAL_CATALOG exists in AUTHENTIC_REGISTRY_DATASETS."""
        for vertical, entry in VERTICAL_CATALOG.items():
            dataset_key = entry.get("dataset_key")
            self.assertIn(
                dataset_key, 
                AUTHENTIC_REGISTRY_DATASETS, 
                f"dataset_key '{dataset_key}' in vertical '{vertical}' was not found in AUTHENTIC_REGISTRY_DATASETS."
            )

    @patch("agents.scout_runner.generate_browser_headers")
    @patch("agents.scout_runner.probe_waf_signatures")
    @patch("httpx.Client")
    def test_discover_next_candidate_all_verticals(self, mock_httpx_client_class, mock_probe_waf, mock_gen_headers):
        """Verify discover_next_candidate can process every single vertical in VERTICAL_CATALOG without KeyError or crash."""
        # Mock WAF probe to return safe to scrape
        mock_probe_waf.return_value = {
            "detected_waf": None,
            "is_safe_to_scrape": True
        }
        
        # Mock HTTP client to return a 200 OK response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Sample Content</html>"
        mock_response.headers = {}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_httpx_client_class.return_value = mock_client
        
        # Setup mocks for storage, portal, and llm
        storage = InMemoryStorageBackend()
        portal = PortalService(storage=storage)
        
        mock_llm_engine = MagicMock()
        mock_llm_engine.run_scout_discovery_agent.return_value = {
            "company_name": "Test Company",
            "contact_name": "John Doe",
            "contact_role": "Director",
            "contact_email": "john@test.com",
            "contact_phone": "123-456-7890",
            "website": "https://test.com",
            "pain_point": "Need test data",
            "pitch_subject": "Test pitch",
            "pitch_body": "This is a test pitch"
        }
        mock_llm_engine.run_lead_enrichment_agent.return_value = {
            "verified_email": "john.doe@test.com",
            "verified_phone": "123-456-7890",
            "cleaned_sample_records": []
        }
        
        worker = ScoutBackgroundWorker(storage=storage, portal=portal, llm_engine=mock_llm_engine)
        
        # Test every vertical individually to verify correct key lookup and pipeline run
        for vertical in VERTICAL_CATALOG.keys():
            with patch("random.choice", return_value=vertical):
                result = worker.discover_next_candidate()
                
                # Verify successful path
                self.assertIsNotNone(result)
                # If it didn't get rejected due to status_code or WAF, it should successfully create a candidate
                if result.get("ok") is not False:
                    self.assertIn("slug", result)
                    self.assertIn("lead_id", result)
                    lead = storage.get_lead(result["lead_id"])
                    self.assertEqual(lead.state, State.PITCH_PENDING_APPROVAL)

    @patch("agents.tools.web_search.search_web")
    @patch("agents.tools.web_fetcher.extract_contact_info_from_url")
    @patch("agents.tools.web_fetcher.extract_portal_sample_data")
    def test_b2b_web_scout_worker(self, mock_extract_portal, mock_extract_contact, mock_search_web):
        """Verify that B2BWebScoutWorker runs the full open web discovery flow successfully."""
        # Setup mocks
        mock_search_web.side_effect = [
            # First call for companies
            [{"title": "Austin Roofing Pros", "url": "https://austinroofingpros.com", "snippet": "Best roofing in Austin"}],
            # Second call for portal
            [{"title": "City of Austin Issued Construction Permits", "url": "https://data.austintexas.gov/permits", "snippet": "Official permits portal"}]
        ]
        
        mock_extract_contact.return_value = {
            "website": "https://austinroofingpros.com",
            "verified_email": "contact@austinroofingpros.com",
            "verified_phone": "512-555-0199",
            "title": "Austin Roofing Pros"
        }
        
        mock_extract_portal.return_value = {
            "ok": True,
            "records": [{"permit_id": "P-1234", "issue_date": "2026-08-28", "valuation": "$120,000"}],
            "fields": ["permit_id", "issue_date", "valuation"]
        }
        
        storage = InMemoryStorageBackend()
        portal = PortalService(storage=storage)
        
        mock_llm_engine = MagicMock()
        mock_llm_engine.run_web_scout_brainstorm_agent.return_value = {
            "niche": "Roofing contractors in Austin",
            "company_search_query": "top roofing contractors Austin Texas",
            "portal_search_query": "Austin Travis County building permits portal gov",
            "jurisdiction": "Austin, TX"
        }
        mock_llm_engine.run_web_scout_dossier_agent.return_value = {
            "company_name": "Austin Roofing Pros",
            "contact_name": "Marcus Vance",
            "contact_role": "President",
            "contact_email": "marcus@austinroofingpros.com",
            "contact_phone": "512-555-0199",
            "website": "https://austinroofingpros.com",
            "niche": "Roofing contractors in Austin",
            "pain_point": "Needs automated tracking of new permits",
            "target_url": "https://data.austintexas.gov/permits",
            "portal_name": "City of Austin Issued Construction Permits",
            "jurisdiction": "Austin, TX",
            "suggested_fields": ["permit_id", "issue_date", "valuation"],
            "tier_key": "weekly",
            "pitch_subject": "Automating your construction permit lead stream",
            "pitch_body": "Hi Marcus, we noticed your team manually monitors permits. Here is a live sandbox of your automated feed."
        }
        
        worker = B2BWebScoutWorker(storage=storage, portal=portal, llm_engine=mock_llm_engine)
        
        # Trigger run
        result = worker.discover_next_candidate(custom_niche="Roofing")
        
        # Verify success output
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("company_name"), "Austin Roofing Pros")
        self.assertEqual(result.get("portal_name"), "City of Austin Issued Construction Permits")
        self.assertEqual(result.get("record_count"), 1)  # Only genuine records saved (no mock padding)
        
        # Verify sandbox lead exists
        lead = storage.get_lead(result["lead_id"])
        self.assertIsNotNone(lead)
        self.assertEqual(lead.contact_name, "Marcus Vance")
        self.assertEqual(lead.niche, "Roofing contractors in Austin")

    @patch("agents.tools.web_search.search_web")
    @patch("agents.tools.web_fetcher.extract_contact_info_from_url")
    @patch("agents.tools.web_fetcher.extract_portal_sample_data")
    def test_b2b_web_scout_worker_runs_until_new_lead_found(self, mock_extract_portal, mock_extract_contact, mock_search_web):
        """Verify that B2BWebScoutWorker skips existing duplicate leads and continues until finding a new lead."""
        from agents.domain import Lead
        storage = InMemoryStorageBackend()
        portal = PortalService(storage=storage)

        # Pre-seed an existing lead
        existing = Lead(
            lead_id="lead-existing-roofing-llc",
            tier_key="weekly",
            company_name="Existing Roofing LLC",
            website="https://existingroofing.com",
            contact_email="sales@existingroofing.com",
            state=State.OUTREACH_SENT,
        )
        storage.save_lead(existing)

        # Search returns the existing duplicate first, followed by a brand-new firm
        mock_search_web.side_effect = [
            [
                {"title": "Existing Roofing LLC", "url": "https://existingroofing.com", "snippet": "Already in DB"},
                {"title": "Lone Star State Roofing", "url": "https://lonestarstateroofing.com", "snippet": "Fresh candidate"},
            ],
            [{"title": "City of Austin Issued Construction Permits", "url": "https://data.austintexas.gov/permits", "snippet": "Official permits portal"}],
        ]

        mock_extract_contact.return_value = {
            "website": "https://lonestarstateroofing.com",
            "verified_email": "hello@lonestarstateroofing.com",
            "verified_phone": "512-555-0999",
            "title": "Lone Star State Roofing",
        }

        mock_extract_portal.return_value = {
            "ok": True,
            "records": [{"permit_id": "P-9999", "issue_date": "2026-09-01", "valuation": "$250,000"}],
            "fields": ["permit_id", "issue_date", "valuation"],
        }

        mock_llm_engine = MagicMock()
        mock_llm_engine.run_web_scout_brainstorm_agent.return_value = {
            "niche": "Roofing in Austin",
            "company_search_query": "top commercial roofing Austin Texas",
            "portal_search_query": "Austin Travis County building permits portal gov",
            "jurisdiction": "Austin, TX",
        }
        mock_llm_engine.run_web_scout_dossier_agent.return_value = {
            "company_name": "Lone Star State Roofing",
            "contact_name": "David Miller",
            "contact_role": "Managing Director",
            "contact_email": "hello@lonestarstateroofing.com",
            "contact_phone": "512-555-0999",
            "website": "https://lonestarstateroofing.com",
            "niche": "Roofing in Austin",
            "pain_point": "Needs automated tracking of new permits",
            "target_url": "https://data.austintexas.gov/permits",
            "portal_name": "City of Austin Issued Construction Permits",
            "jurisdiction": "Austin, TX",
            "suggested_fields": ["permit_id", "issue_date", "valuation"],
            "tier_key": "weekly",
            "pitch_subject": "permits feed for lone star",
            "pitch_body": "Hi David, live data feed ready for review.",
        }

        worker = B2BWebScoutWorker(storage=storage, portal=portal, llm_engine=mock_llm_engine)

        # Trigger run with run_until_found=True
        result = worker.discover_next_candidate(custom_niche="Roofing", run_until_found=True)

        # Verify that it bypassed Existing Roofing LLC and successfully created Lone Star State Roofing
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("company_name"), "Lone Star State Roofing")

        new_lead = storage.get_lead(result["lead_id"])
        self.assertIsNotNone(new_lead)
        self.assertEqual(new_lead.company_name, "Lone Star State Roofing")
        self.assertEqual(new_lead.contact_email, "hello@lonestarstateroofing.com")


if __name__ == "__main__":
    unittest.main()
