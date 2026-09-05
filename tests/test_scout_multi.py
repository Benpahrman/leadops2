import pytest
from unittest.mock import patch
from agents.storage import InMemoryStorageBackend
from agents.scout_runner import ScoutBackgroundWorker
from agents.portal import PortalService
from agents.admin_ops import AdminMissionControlService

def test_scout_prospects_beyond_eight_leads():
    storage = InMemoryStorageBackend()
    portal = PortalService(storage)
    worker = ScoutBackgroundWorker(storage=storage, portal=portal)
    admin = AdminMissionControlService(storage)
    
    with patch("agents.scout_runner.probe_waf_signatures", return_value={"detected_waf": None, "is_safe_to_scrape": True}), \
         patch("agents.scout_runner.generate_browser_headers", return_value={"User-Agent": "Mozilla/5.0"}):
        # Run 10 consecutive discovery cycles
        for i in range(10):
            candidate = worker.discover_next_candidate()
            assert candidate is not None, f"Cycle {i+1} should find a candidate"
            
    leads = storage.list_leads()
    print(f"\nTotal leads produced: {len(leads)}")
    assert len(leads) >= 10, f"Expected at least 10 leads, found {len(leads)}"
    
    unique_companies = {l.company_name.strip().lower() for l in leads if l.company_name}
    print(f"Unique companies ({len(unique_companies)}): {unique_companies}")
    assert len(unique_companies) >= 10, f"Expected 10 unique companies, found {len(unique_companies)}: {unique_companies}"
    
    kanban = admin.get_pipeline_kanban()
    total_leads = kanban["total_leads"]
    print(f"Kanban total leads: {total_leads}")
    assert total_leads >= 10, f"Expected kanban to display at least 10 cards, found {total_leads}"
