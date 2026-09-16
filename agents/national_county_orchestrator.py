"""National 50-State & County-by-County Swarm Prospecting Orchestrator.

Manages deterministic, continuous progression across all US States and their Municipal / County
jurisdictions, ensuring 100% systematic nationwide coverage of commercial prospects (probate attorneys,
estate planners, title companies, mechanics lien filers, and commercial permit applicants).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .logging_config import get_logger
from .tools.geo_county_resolver import GeoCountyResolver, STATE_NAMES_TO_ABBR, CITY_COUNTY_REGISTRY

logger = get_logger("national_county_orchestrator")

DEFAULT_STATE_FILE = Path("data/national_county_orchestrator_state.json")

# Default prioritized state sweep sequence
DEFAULT_PRIORITY_STATES = [
    "WA", "TX", "FL", "CA", "AZ", "IL", "GA", "NC", "OH", "CO",
    "NV", "NY", "TN", "PA", "MI", "VA", "MA", "MD", "NJ", "MO",
    "IN", "WI", "MN", "SC", "AL", "LA", "KY", "OR", "OK", "CT",
    "UT", "IA", "NV", "AR", "MS", "KS", "NM", "NE", "ID", "WV",
    "HI", "NH", "ME", "RI", "MT", "DE", "SD", "ND", "AK", "VT", "WY",
]


@dataclass
class JurisdictionProgressState:
    """State data structure for the 50-State and County cycling engine."""
    current_state_code: str = "WA"
    current_state_index: int = 0
    current_county_index: int = 0
    active_county_name: str = ""
    active_city: str = ""
    active_portal_name: str = ""
    active_portal_url: str = ""
    cycle_count: int = 0
    total_states_configured: int = len(DEFAULT_PRIORITY_STATES)
    locked_state_focus: Optional[str] = None  # If set, stays within this state
    jurisdiction_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state_code": self.current_state_code,
            "current_state_index": self.current_state_index,
            "current_county_index": self.current_county_index,
            "active_county_name": self.active_county_name,
            "active_city": self.active_city,
            "active_portal_name": self.active_portal_name,
            "active_portal_url": self.active_portal_url,
            "cycle_count": self.cycle_count,
            "total_states_configured": self.total_states_configured,
            "locked_state_focus": self.locked_state_focus,
            "jurisdiction_stats": dict(self.jurisdiction_stats),
            "last_updated_at": self.last_updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JurisdictionProgressState:
        state = cls()
        state.current_state_code = data.get("current_state_code", "WA")
        state.current_state_index = data.get("current_state_index", 0)
        state.current_county_index = data.get("current_county_index", 0)
        state.active_county_name = data.get("active_county_name", "")
        state.active_city = data.get("active_city", "")
        state.active_portal_name = data.get("active_portal_name", "")
        state.active_portal_url = data.get("active_portal_url", "")
        state.cycle_count = data.get("cycle_count", 0)
        state.total_states_configured = data.get("total_states_configured", len(DEFAULT_PRIORITY_STATES))
        state.locked_state_focus = data.get("locked_state_focus")
        state.jurisdiction_stats = data.get("jurisdiction_stats", {})
        state.last_updated_at = data.get("last_updated_at", "")
        return state


class NationalCountyOrchestrator:
    """Orchestrates deterministic state-by-state, county-by-county B2B prospecting sweeps."""

    def __init__(
        self,
        state_file_path: Path | str = DEFAULT_STATE_FILE,
        state_sequence: list[str] | None = None,
    ):
        self.state_file = Path(state_file_path)
        self.state_sequence = [s.upper() for s in (state_sequence or DEFAULT_PRIORITY_STATES)]
        self.state = self._load_state()
        self._sync_active_jurisdiction()

    def _load_state(self) -> JurisdictionProgressState:
        """Load persistent cycle state from disk or initialize fresh state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    state = JurisdictionProgressState.from_dict(data)
                    state.total_states_configured = len(self.state_sequence)
                    return state
            except Exception as e:
                logger.error(f"Failed to load national county cycle state from {self.state_file}: {e}")

        # Fresh state
        state = JurisdictionProgressState(
            current_state_code=self.state_sequence[0] if self.state_sequence else "WA",
            current_state_index=0,
            current_county_index=0,
            total_states_configured=len(self.state_sequence),
        )
        self._save_state(state)
        return state

    def _save_state(self, state: Optional[JurisdictionProgressState] = None) -> None:
        """Persist cycle state to disk."""
        target_state = state or self.state
        target_state.last_updated_at = datetime.now(timezone.utc).isoformat()
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(target_state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save national county cycle state to {self.state_file}: {e}")

    def get_counties_for_state(self, state_code: str) -> list[dict[str, Any]]:
        """Return all recognized counties, seats, and public records portals for a state."""
        st = state_code.upper().strip()
        counties = GeoCountyResolver.get_all_counties_for_state(st)
        if not counties:
            # Fallback for states without granular registry yet
            counties = [
                {
                    "county": "Statewide Primary County",
                    "state": st,
                    "fips": "",
                    "primary_city": "State Capital",
                    "cities": ["State Capital"],
                    "portal_name": f"{st} Statewide Public Registry",
                    "portal_url": "https://data.gov",
                }
            ]
        return counties

    def _sync_active_jurisdiction(self) -> None:
        """Ensure current active jurisdiction metadata aligns with current state and county indices."""
        curr_st = self.state.locked_state_focus or self.state.current_state_code
        counties = self.get_counties_for_state(curr_st)
        if not counties:
            return

        c_idx = self.state.current_county_index % len(counties)
        c_info = counties[c_idx]

        self.state.current_state_code = curr_st
        self.state.active_county_name = c_info["county"]
        self.state.active_city = c_info.get("primary_city", "")
        self.state.active_portal_name = c_info.get("portal_name", f"{c_info['county']} Public Records")
        self.state.active_portal_url = c_info.get("portal_url", "")

    def get_active_jurisdiction(self) -> dict[str, Any]:
        """Return the current active state, county, primary city, and municipal portal."""
        self._sync_active_jurisdiction()
        curr_st = self.state.current_state_code
        counties = self.get_counties_for_state(curr_st)
        total_counties_in_state = len(counties)

        return {
            "state_code": curr_st,
            "state_index": self.state.current_state_index,
            "total_states": len(self.state_sequence),
            "county_name": self.state.active_county_name,
            "county_index": self.state.current_county_index,
            "total_counties_in_state": total_counties_in_state,
            "primary_city": self.state.active_city,
            "portal_name": self.state.active_portal_name,
            "portal_url": self.state.active_portal_url,
            "cycle_count": self.state.cycle_count,
            "is_state_locked": bool(self.state.locked_state_focus),
            "locked_state": self.state.locked_state_focus,
        }

    def advance_cursor(self) -> dict[str, Any]:
        """Advance cursor to the next county. If state is complete, advances to the next state."""
        curr_st = self.state.locked_state_focus or self.state.current_state_code
        counties = self.get_counties_for_state(curr_st)
        total_counties = len(counties)

        prev_c_idx = self.state.current_county_index
        next_c_idx = prev_c_idx + 1

        if next_c_idx < total_counties:
            # Step to next county in current state
            self.state.current_county_index = next_c_idx
        else:
            # Completed all counties in current state
            logger.info(f"🏛️ [STATE SWEEP COMPLETE] Completed all {total_counties} counties in state '{curr_st}'.")
            self.state.current_county_index = 0

            if self.state.locked_state_focus:
                # Locked on this state: start new cycle within the same state
                self.state.cycle_count += 1
                logger.info(f"🔄 [LOCKED STATE CYCLE] Starting cycle #{self.state.cycle_count} for state '{curr_st}'.")
            else:
                # Advance to next state in national sequence
                next_st_idx = self.state.current_state_index + 1
                if next_st_idx >= len(self.state_sequence):
                    self.state.current_state_index = 0
                    self.state.cycle_count += 1
                    logger.info(f"🌎 [NATIONAL SWEEP COMPLETE] Completed all 50 states! Starting national cycle #{self.state.cycle_count}.")
                else:
                    self.state.current_state_index = next_st_idx

                self.state.current_state_code = self.state_sequence[self.state.current_state_index]

        self._sync_active_jurisdiction()
        self._record_jurisdiction_visit(self.state.current_state_code, self.state.active_county_name)
        self._save_state()

        active = self.get_active_jurisdiction()
        logger.info(
            f"🗺️ [ORCHESTRATOR CURSOR ADVANCED] State: {active['state_code']} ({active['state_index']+1}/{active['total_states']}) | "
            f"County: {active['county_name']} ({active['county_index']+1}/{active['total_counties_in_state']}) | City: {active['primary_city']}"
        )
        return active

    def set_state_focus(self, state_code: Optional[str] = None) -> dict[str, Any]:
        """Lock prospecting to a single state (e.g. 'WA', 'TX', 'FL') or unlock for 50-state sweep."""
        if state_code:
            st = state_code.upper().strip()
            self.state.locked_state_focus = st
            self.state.current_state_code = st
            self.state.current_county_index = 0
            logger.info(f"🔒 [STATE FOCUS LOCKED] Prospecting locked to state '{st}'.")
        else:
            self.state.locked_state_focus = None
            logger.info("🔓 [STATE FOCUS UNLOCKED] Resuming continuous 50-state national sweep.")

        self._sync_active_jurisdiction()
        self._save_state()
        return self.get_active_jurisdiction()

    def record_lead_discovered(self, state_code: str, county_name: str) -> None:
        """Record a successful lead discovery for the given jurisdiction."""
        key = f"{state_code.upper()}:{county_name.title()}"
        if key not in self.state.jurisdiction_stats:
            self.state.jurisdiction_stats[key] = {
                "state": state_code.upper(),
                "county": county_name.title(),
                "visited_count": 1,
                "leads_discovered": 1,
                "forms_submitted": 0,
                "last_visited_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            self.state.jurisdiction_stats[key]["leads_discovered"] += 1
            self.state.jurisdiction_stats[key]["last_visited_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

    def _record_jurisdiction_visit(self, state_code: str, county_name: str) -> None:
        """Track visit telemetry for jurisdiction."""
        key = f"{state_code.upper()}:{county_name.title()}"
        if key not in self.state.jurisdiction_stats:
            self.state.jurisdiction_stats[key] = {
                "state": state_code.upper(),
                "county": county_name.title(),
                "visited_count": 1,
                "leads_discovered": 0,
                "forms_submitted": 0,
                "last_visited_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            self.state.jurisdiction_stats[key]["visited_count"] += 1
            self.state.jurisdiction_stats[key]["last_visited_at"] = datetime.now(timezone.utc).isoformat()


_global_orchestrator: NationalCountyOrchestrator | None = None


def get_national_county_orchestrator() -> NationalCountyOrchestrator:
    """Retrieve singleton NationalCountyOrchestrator instance."""
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = NationalCountyOrchestrator()
    return _global_orchestrator
