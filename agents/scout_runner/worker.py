"""Backward-compatible facade for ScoutBackgroundWorker.

The implementation lives in agents/scout_runner/worker_pkg/.
"""

from agents.scout_runner.worker_pkg import (
    prune_dom,
    generate_browser_headers,
    probe_waf_signatures,
    search_web,
    search_company_intelligence,
    search_job_board_intent,
    find_linkedin_decision_maker,
    search_public_data_portals,
    extract_contact_info_from_url,
    fetch_page_content,
    ScoutBackgroundWorker,
)

__all__ = [
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
    "ScoutBackgroundWorker",
]
