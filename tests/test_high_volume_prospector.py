"""Tests for 14-Day High-Volume Prospector, Deduplication Engine, and Pre-Outreach Same-Day Freshness Gate."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agents.domain import Lead, State
from agents.scout.high_volume_prospector import HighVolumeProspectorEngine, ProspectorCampaignMetrics
from agents.pitcher import ensure_fresh_records_for_lead
from agents.portal import PortalService, Sandbox
from agents.storage import (
    InMemoryStorageBackend,
    normalize_company_name,
    normalize_domain,
)


def test_normalization_helpers():
    """Verify company name and domain normalizers eliminate formatting discrepancies."""
    assert normalize_company_name("Acme Builders, LLC") == "acmebuilders"
    assert normalize_company_name("Peak Title Services Inc.") == "peaktitle"
    assert normalize_company_name("Zenith Real Estate Corp 2026") == "zenithrealestate"
    assert normalize_company_name("  Apex  Roofing,   P.L.L.C. ") == "apexroofing"

    assert normalize_domain("https://www.acmebuilders.com/about") == "acmebuilders.com"
    assert normalize_domain("http://peaktitle.org/") == "peaktitle.org"
    assert normalize_domain("subdomain.example.com") == "subdomain.example.com"


def test_multi_key_deduplication():
    """Verify strict deduplication detects duplicates across company, email, domain, suppression, and contact history."""
    storage = InMemoryStorageBackend()

    # Seed an existing lead
    lead1 = Lead(
        lead_id="lead-test-01",
        tier_key="daily",
        company_name="Apex Construction LLC",
        contact_email="mark@apexconstruction.com",
        website="https://www.apexconstruction.com",
        state=State.PITCH_PENDING_APPROVAL,
    )
    storage.save_lead(lead1)

    # 1. Duplicate company name check
    is_dup, reason = storage.check_prospect_deduplication(
        company_name="Apex Construction Inc",
        domain="newapex.com",
        email="john@newapex.com",
    )
    assert is_dup is True
    assert reason == "DUPLICATE_COMPANY"

    # 2. Duplicate email check (distinct domain so email check fires)
    is_dup, reason = storage.check_prospect_deduplication(
        company_name="Different Builder",
        domain="newbuilder.com",
        email="mark@apexconstruction.com",
    )
    assert is_dup is True
    assert reason in ("DUPLICATE_EMAIL", "RECENTLY_CONTACTED_45D")

    # 3. Duplicate domain check
    is_dup, reason = storage.check_prospect_deduplication(
        company_name="Completely New Name",
        domain="apexconstruction.com",
        email="info@apexconstruction.com",
    )
    assert is_dup is True
    assert reason in ("DUPLICATE_DOMAIN", "RECENTLY_CONTACTED_45D")

    # 4. Universal Suppression check
    storage.add_to_global_suppression("optout@competitor.com", reason="Unsubscribe request")
    is_dup, reason = storage.check_prospect_deduplication(
        company_name="Random Brand",
        domain="brand.com",
        email="optout@competitor.com",
    )
    assert is_dup is True
    assert reason == "GLOBAL_SUPPRESSION"

    # 5. Unique new prospect check
    is_dup, reason = storage.check_prospect_deduplication(
        company_name="Vanguard Logistics Group",
        domain="vanguardlogistics.com",
        email="ops@vanguardlogistics.com",
    )
    assert is_dup is False
    assert reason == "UNIQUE"


def test_high_volume_prospector_lifecycle():
    """Test start, pause, resume, and burst telemetry on HighVolumeProspectorEngine."""
    storage = InMemoryStorageBackend()
    portal = PortalService(storage)

    engine = HighVolumeProspectorEngine(
        storage=storage,
        portal=portal,
        campaign_duration_days=14,
        volume_per_cycle=3,
        rest_seconds_min=1,
        rest_seconds_max=2,
    )

    status = engine.get_status()
    assert status["campaign_duration_days"] == 14
    assert status["current_day"] == 1
    assert status["is_campaign_expired"] is False
    assert "metrics" in status

    # Start campaign
    status_started = engine.start_campaign(duration_days=14, volume_per_cycle=5)
    assert status_started["is_active"] is True
    assert status_started["volume_per_cycle"] == 5

    # Pause campaign
    status_paused = engine.pause_campaign()
    assert status_paused["is_active"] is False

    # Resume campaign
    status_resumed = engine.resume_campaign()
    assert status_resumed["is_active"] is True

    # Stop background task cleanly
    engine.pause_campaign()


@pytest.mark.asyncio
async def test_prospector_trigger_burst():
    """Verify trigger_burst executes multi-lead discovery, updates telemetry, and increments backlog."""
    storage = InMemoryStorageBackend()
    portal = PortalService(storage)

    engine = HighVolumeProspectorEngine(
        storage=storage,
        portal=portal,
        campaign_duration_days=14,
        volume_per_cycle=3,
    )
    engine.metrics = ProspectorCampaignMetrics()

    mock_discovered_lead = {
        "ok": True,
        "lead_id": "lead-burst-01",
        "company_name": "Lone Star Concrete LLC",
        "contact_email": "ops@lonestarconcrete.com",
        "slug": "lone-star-concrete",
    }

    with patch("agents.scout_runner.ScoutBackgroundWorker.discover_next_candidate", return_value=mock_discovered_lead):
        res = await engine.trigger_burst(count=2)
        assert res["ok"] is True
        assert res["qualified_count"] == 2
        assert engine.metrics.deliverability_passed == 2
        assert engine.metrics.total_evaluated == 2
        assert engine.metrics.sandboxes_created == 2


def test_pre_outreach_same_day_freshness_gate():
    """Verify ensure_fresh_records_for_lead detects stale (>24h) records and injects fresh same-day filings."""
    storage = InMemoryStorageBackend()
    portal = PortalService(storage)

    # Lead with stale records (3 days old)
    stale_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    lead = Lead(
        lead_id="lead-stale-01",
        tier_key="daily",
        company_name="Austin Metro Builders",
        contact_email="contact@austinmetrobuilders.com",
        target_portal_name="Austin Commercial Permits Portal",
        jurisdiction="Travis County, TX",
        niche="Commercial Permitting",
        slug="austin-metro-builders",
    )
    lead.sample_data = [{"filing_date": stale_date, "permit_id": "P-9988"}]
    storage.save_lead(lead)

    # Seed sandbox with stale records
    sandbox = Sandbox(
        slug="austin-metro-builders",
        lead=lead,
        rows=[{"filing_date": stale_date, "permit_id": "P-9988"}],
        source_url="https://data.austintexas.gov",
    )
    storage.save_sandbox(sandbox)

    # Run freshness check
    fresh_res = ensure_fresh_records_for_lead(
        lead=lead,
        portal_service=portal,
        storage_backend=storage,
        max_age_hours=24,
    )

    assert fresh_res["fresh"] is True
    assert fresh_res["refreshed"] is True
    assert fresh_res["record_count"] >= 1

    # Verify updated sandbox has fresh filings
    updated_sandbox = portal.get_sandbox("austin-metro-builders")
    assert updated_sandbox is not None
    assert len(updated_sandbox.rows) >= 1
    assert updated_sandbox.rows[0]["filing_date"] is not None
    assert lead.sample_data[0]["filing_date"] == updated_sandbox.rows[0]["filing_date"]


def test_admin_prospector_api_endpoints():
    """Verify FastAPI admin routes for high-volume prospector status, start, pause, and burst."""
    from fastapi.testclient import TestClient
    from agents.api import create_app
    from agents.admin_ops import AdminMissionControlService

    storage = InMemoryStorageBackend()
    portal = PortalService(storage)
    admin_service = AdminMissionControlService(storage=storage)
    app = create_app(storage=storage, portal_svc=portal, admin_ops=admin_service)
    client = TestClient(app)

    headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    # 1. GET status
    res = client.get("/api/admin/prospector/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "campaign_duration_days" in data
    assert "metrics" in data
    assert "is_office_hours" in data
    assert "run_24_7" in data

    # 2. POST toggle-24-7
    res = client.post("/api/admin/prospector/toggle-24-7", json={"enabled": True}, headers=headers)
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["run_24_7"] is True

    # 3. POST start
    res = client.post("/api/admin/prospector/start", json={"duration_days": 14, "volume_per_cycle": 4}, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is True
    assert res.json()["volume_per_cycle"] == 4

    # 4. POST pause
    res = client.post("/api/admin/prospector/pause", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # 5. POST resume
    res = client.post("/api/admin/prospector/resume", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    # 6. POST pause cleanup
    client.post("/api/admin/prospector/pause", headers=headers)


@pytest.mark.asyncio
async def test_prospector_24_7_unhindered_by_work_hours():
    """Verify that in 24/7 mode, Scout is NOT hindered by off-hours and executes bursts all day."""
    storage = InMemoryStorageBackend()
    portal = PortalService(storage)

    engine = HighVolumeProspectorEngine(
        storage=storage,
        portal=portal,
        campaign_duration_days=14,
        volume_per_cycle=2,
    )
    engine.run_24_7 = True

    mock_lead = {
        "ok": True,
        "lead_id": "lead-night-01",
        "company_name": "Midnight Title Services",
        "contact_email": "ops@midnighttitle.com",
        "slug": "midnight-title-services",
    }

    # Simulate running outside office hours (midnight, Sunday, etc.)
    with patch("agents.scout.high_volume_prospector.is_office_hours", return_value=(False, 28800, "Outside office hours")):
        with patch("agents.scout_runner.ScoutBackgroundWorker.discover_next_candidate", return_value=mock_lead):
            burst_res = await engine.trigger_burst(count=1)
            assert burst_res["ok"] is True
            assert burst_res["qualified_count"] == 1
            assert engine.get_status()["run_24_7"] is True
            assert engine.get_status()["is_office_hours"] is False
