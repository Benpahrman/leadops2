"""Autonomous Scout runner package for continuous lead prospecting, micro-scraping, and B2B qualification."""

from agents.office_hours import is_office_hours
from agents.tools.dom_pruner import prune_dom
from agents.tools.waf_prober import generate_browser_headers, probe_waf_signatures
from agents.tools.web_search import (
    search_web,
    search_company_intelligence,
    search_job_board_intent,
    find_linkedin_decision_maker,
    search_public_data_portals,
)
from agents.tools.web_fetcher import (
    extract_contact_info_from_url,
    fetch_page_content,
    extract_portal_sample_data,
)

from .catalog import VERTICAL_CATALOG
from .worker import ScoutBackgroundWorker
from .supervisor import ScoutAutomationSupervisor
from .web_scout import B2BWebScoutWorker
from .cli import main

__all__ = [
    "VERTICAL_CATALOG",
    "ScoutBackgroundWorker",
    "ScoutAutomationSupervisor",
    "B2BWebScoutWorker",
    "is_office_hours",
    "main",
    "prune_dom",
    "generate_browser_headers",
    "probe_waf_signatures",
    "search_web",
    "search_company_intelligence",
    "search_job_board_intent",
    "find_linkedin_decision_maker",
    "search_public_data_portals",
    "extract_contact_info_from_url",
    "fetch_page_content",
    "extract_portal_sample_data",
]

# Specialist Prospecting Engines & Orchestrators
from agents.scout_runner.national_county_orchestrator import NationalCountyOrchestrator, JurisdictionProgressState, get_national_county_orchestrator
from agents.scout_runner.wa_county_orchestrator import WashingtonCountyOrchestrator, CountyCycleState
from agents.scout_runner.contact_enricher_agent import ContactEnricherResearcherAgent
from agents.scout_runner.high_volume_prospector import HighVolumeProspectorEngine, ProspectorCampaignMetrics, get_high_volume_prospector
from agents.scout_runner.local_business_prospector import LocalBusinessProspector, DiscoveredLocalBusiness
from agents.scout_runner.sos_entity_prospector import SOSEntityProspector, DiscoveredSOSEntity
from agents.scout_runner.state_bar_prospector import StateBarProspector, DiscoveredBarAttorney
from agents.scout_runner.hiring_intent_prospector import HiringIntentProspector, DiscoveredHiringProspect
from agents.scout_runner.niche_brainstormer_agent import NicheBrainstormerAgent
from agents.scout_runner.county_filing_extractor import CountyFilingPartyExtractor, DiscoveredFilingEntity
from agents.scout_runner.website_form_submitter import WebsiteContactFormSubmitter, ContactFormSubmissionResult
from agents.scout_runner.scout_pipeline import ScoutPortalPipeline, ScoutCandidate

WACountyOrchestrator = WashingtonCountyOrchestrator
CountyFilingExtractor = CountyFilingPartyExtractor
WebsiteFormSubmitter = WebsiteContactFormSubmitter
