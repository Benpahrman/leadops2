"""Scout-to-portal pipeline using verified evidence and permitted sample data."""

from dataclasses import dataclass
from typing import Any

from .domain import Lead
from .portal import IntakeForm, PortalService


@dataclass(frozen=True)
class ScoutCandidate:
    lead_id: str
    slug: str
    source_url: str
    intake: IntakeForm


class ScoutPortalPipeline:
    def __init__(self, portal: PortalService):
        self.portal = portal

    def publish_candidate(
        self,
        company_name: str,
        lead_id: str,
        evidence: list[dict[str, str]],
        source_url: str,
        sample_rows: list[dict[str, str]],
        research: dict[str, object],
        tier_key: str = "weekly",
    ) -> ScoutCandidate:
        if not evidence or not any(item.get("url") == source_url for item in evidence):
            raise ValueError("source_url must be present in Scout evidence")
        lead = Lead(lead_id, tier_key)
        lead.jurisdiction = str(research.get("jurisdiction", ""))
        slug = self.portal.publish_sandbox(lead, company_name, sample_rows, source_url)
        intake = self.portal.build_intake_form(slug, research)
        return ScoutCandidate(lead_id, slug, source_url, intake)