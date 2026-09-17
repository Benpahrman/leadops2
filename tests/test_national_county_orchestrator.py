"""Unit tests for NationalCountyOrchestrator and 50-State / County-by-County swarm engine."""

import json
import tempfile
from pathlib import Path
import pytest

from agents.scout.national_county_orchestrator import (
    NationalCountyOrchestrator,
    JurisdictionProgressState,
    DEFAULT_PRIORITY_STATES,
)
from agents.tools.geo_county_resolver import GeoCountyResolver


@pytest.fixture
def temp_orchestrator():
    """Create an orchestrator instance using an ephemeral state file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    orchestrator = NationalCountyOrchestrator(
        state_file_path=temp_path,
        state_sequence=["WA", "TX", "FL"],
    )
    yield orchestrator

    if temp_path.exists():
        temp_path.unlink()


def test_orchestrator_initialization(temp_orchestrator):
    """Test fresh orchestrator starts at state 0 (WA) with valid jurisdiction info."""
    active = temp_orchestrator.get_active_jurisdiction()
    assert active["state_code"] == "WA"
    assert active["state_index"] == 0
    assert active["total_states"] == 3
    assert active["county_index"] == 0
    assert len(active["county_name"]) > 0
    assert active["total_counties_in_state"] > 0
    assert not active["is_state_locked"]


def test_orchestrator_advances_through_counties(temp_orchestrator):
    """Test that advance_cursor steps county-by-county."""
    initial = temp_orchestrator.get_active_jurisdiction()
    initial_county = initial["county_name"]

    next_jur = temp_orchestrator.advance_cursor()
    assert next_jur["state_code"] == "WA"
    assert next_jur["county_index"] == 1
    assert next_jur["county_name"] != initial_county


def test_orchestrator_advances_to_next_state_on_county_exhaustion():
    """Test that once all counties in a state are completed, it advances to next state."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    # Use a custom short 2-state sequence with 2 counties each
    orch = NationalCountyOrchestrator(
        state_file_path=temp_path,
        state_sequence=["WA", "TX"],
    )

    wa_counties = orch.get_counties_for_state("WA")
    total_wa = len(wa_counties)

    # Fast forward to the last county of WA
    orch.state.current_county_index = total_wa - 1
    orch._sync_active_jurisdiction()

    # Next advance should cross state boundary into TX
    next_jur = orch.advance_cursor()
    assert next_jur["state_code"] == "TX"
    assert next_jur["state_index"] == 1
    assert next_jur["county_index"] == 0

    if temp_path.exists():
        temp_path.unlink()


def test_orchestrator_state_focus_lock_and_unlock(temp_orchestrator):
    """Test locking focus to a specific state (e.g. TX) and unlocking."""
    # Lock to TX
    locked = temp_orchestrator.set_state_focus("TX")
    assert locked["state_code"] == "TX"
    assert locked["is_state_locked"] is True
    assert locked["locked_state"] == "TX"
    assert locked["county_index"] == 0

    # Advance cursor while locked
    advanced = temp_orchestrator.advance_cursor()
    assert advanced["state_code"] == "TX"
    assert advanced["county_index"] == 1

    # Unlock focus
    unlocked = temp_orchestrator.set_state_focus(None)
    assert unlocked["is_state_locked"] is False
    assert unlocked["locked_state"] is None


def test_orchestrator_record_lead_discovered(temp_orchestrator):
    """Test recording lead discoveries updates jurisdiction telemetry."""
    temp_orchestrator.record_lead_discovered("WA", "King")
    temp_orchestrator.record_lead_discovered("WA", "King")

    stats = temp_orchestrator.state.jurisdiction_stats
    assert "WA:King" in stats
    assert stats["WA:King"]["leads_discovered"] == 2


def test_geo_county_resolver_has_rich_counties():
    """Verify GeoCountyResolver returns valid county records for major states."""
    wa_counties = GeoCountyResolver.get_all_counties_for_state("WA")
    assert len(wa_counties) >= 30
    assert any("King" in c["county"] for c in wa_counties)
    assert any("Pierce" in c["county"] for c in wa_counties)

    tx_counties = GeoCountyResolver.get_all_counties_for_state("TX")
    assert len(tx_counties) >= 5
    assert any("Harris" in c["county"] for c in tx_counties)

    fl_counties = GeoCountyResolver.get_all_counties_for_state("FL")
    assert len(fl_counties) >= 4
    assert any("Miami-Dade" in c["county"] or "Miami" in c["county"] for c in fl_counties)
