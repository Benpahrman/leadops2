"""Washington State 39-County Cycling Orchestrator for LeadOps Swarm.

Manages deterministic, continuous progression across all 39 Washington counties,
ensuring comprehensive statewide coverage of small and medium businesses (SMBs)
that rely on manual county public-records and court dockets.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.logging_config import get_logger
from agents.tools.geo_county_resolver import GeoCountyResolver

logger = get_logger("wa_county_orchestrator")

DEFAULT_STATE_FILE = Path("data/wa_county_orchestrator_state.json")


@dataclass
class CountyCycleState:
    """State data structure for the 39-county cycling engine."""
    current_county_index: int = 0
    cycle_count: int = 0
    total_counties: int = 39
    county_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_updated_at: str = ""
    active_county_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_county_index": self.current_county_index,
            "cycle_count": self.cycle_count,
            "total_counties": self.total_counties,
            "county_stats": dict(self.county_stats),
            "last_updated_at": self.last_updated_at,
            "active_county_name": self.active_county_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CountyCycleState:
        state = cls()
        state.current_county_index = data.get("current_county_index", 0)
        state.cycle_count = data.get("cycle_count", 0)
        state.total_counties = data.get("total_counties", 39)
        state.county_stats = data.get("county_stats", {})
        state.last_updated_at = data.get("last_updated_at", "")
        state.active_county_name = data.get("active_county_name", "")
        return state


class WashingtonCountyOrchestrator:
    """Orchestrates deterministic cycling across all 39 Washington counties."""

    def __init__(self, state_file_path: Path | str = DEFAULT_STATE_FILE):
        self.state_file = Path(state_file_path)
        self.counties = GeoCountyResolver.get_all_counties_for_state("WA")
        if not self.counties:
            logger.warning("No Washington counties found in registry; resolving default list.")
        self.state = self._load_state()

    def _load_state(self) -> CountyCycleState:
        """Load persistent cycle state from disk or initialize fresh state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    state = CountyCycleState.from_dict(data)
                    state.total_counties = len(self.counties)
                    if self.counties:
                        idx = state.current_county_index % len(self.counties)
                        state.active_county_name = self.counties[idx]["county"]
                    return state
            except Exception as e:
                logger.error(f"Failed to load WA county cycle state from {self.state_file}: {e}")

        # Initialize fresh state
        state = CountyCycleState(total_counties=len(self.counties))
        if self.counties:
            state.active_county_name = self.counties[0]["county"]
            for c in self.counties:
                state.county_stats[c["county"]] = {
                    "visited_count": 0,
                    "leads_discovered": 0,
                    "forms_submitted": 0,
                    "last_visited_at": None,
                }
        self._save_state(state)
        return state

    def _save_state(self, state: Optional[CountyCycleState] = None) -> None:
        """Persist cycle state to disk."""
        target_state = state or self.state
        target_state.last_updated_at = datetime.now(timezone.utc).isoformat()
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(target_state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save WA county cycle state to {self.state_file}: {e}")

    def get_all_counties(self) -> list[dict[str, Any]]:
        """Return the complete list of 39 Washington counties with seats and portals."""
        return list(self.counties)

    def get_active_county(self) -> dict[str, Any]:
        """Return the county currently active in the cycle cursor."""
        if not self.counties:
            return {"county": "King County", "state": "WA", "primary_city": "Seattle", "portal_name": "King County Recorder"}

        idx = self.state.current_county_index % len(self.counties)
        county = self.counties[idx]
        self.state.active_county_name = county["county"]
        return county

    def advance_county(self) -> dict[str, Any]:
        """Advance cursor to the next Washington county and persist state."""
        if not self.counties:
            return self.get_active_county()

        prev_idx = self.state.current_county_index
        next_idx = prev_idx + 1

        if next_idx >= len(self.counties):
            self.state.current_county_index = 0
            self.state.cycle_count += 1
            logger.info(f"🔄 [WA COUNTY CYCLE] Completed full 39-county cycle #{self.state.cycle_count}! Resetting to 0.")
        else:
            self.state.current_county_index = next_idx

        new_county = self.get_active_county()
        c_name = new_county["county"]

        # Track visit
        if c_name not in self.state.county_stats:
            self.state.county_stats[c_name] = {
                "visited_count": 0,
                "leads_discovered": 0,
                "forms_submitted": 0,
                "last_visited_at": None,
            }
        self.state.county_stats[c_name]["visited_count"] += 1
        self.state.county_stats[c_name]["last_visited_at"] = datetime.now(timezone.utc).isoformat()

        self._save_state()
        logger.info(
            f"📍 [WA COUNTY CYCLE] Advanced to {c_name} (Index: {self.state.current_county_index + 1}/39 | "
            f"Seat/City: {new_county.get('primary_city')})"
        )
        return new_county

    def record_activity(
        self,
        county_name: str,
        leads_discovered: int = 0,
        forms_submitted: int = 0,
    ) -> None:
        """Update metrics for a county following discovery or outreach."""
        if county_name not in self.state.county_stats:
            self.state.county_stats[county_name] = {
                "visited_count": 1,
                "leads_discovered": 0,
                "forms_submitted": 0,
                "last_visited_at": datetime.now(timezone.utc).isoformat(),
            }

        stats = self.state.county_stats[county_name]
        stats["leads_discovered"] += leads_discovered
        stats["forms_submitted"] += forms_submitted
        stats["last_visited_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

    def get_progress_metrics(self) -> dict[str, Any]:
        """Return high-level telemetry on county coverage and progress."""
        total = len(self.counties)
        active = self.get_active_county()
        total_discovered = sum(s.get("leads_discovered", 0) for s in self.state.county_stats.values())
        total_forms = sum(s.get("forms_submitted", 0) for s in self.state.county_stats.values())
        visited_count = sum(1 for s in self.state.county_stats.values() if s.get("visited_count", 0) > 0)

        return {
            "state": "WA",
            "total_counties": total,
            "current_county_index": self.state.current_county_index,
            "active_county": active["county"],
            "active_city": active.get("primary_city", ""),
            "portal_name": active.get("portal_name", ""),
            "portal_url": active.get("portal_url", ""),
            "cycle_count": self.state.cycle_count,
            "counties_visited_in_cycle": visited_count,
            "coverage_percent": round((visited_count / max(1, total)) * 100, 1),
            "total_leads_discovered": total_discovered,
            "total_forms_submitted": total_forms,
            "last_updated_at": self.state.last_updated_at,
        }
