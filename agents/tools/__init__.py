"""LeadOps specialist scraping tools and handlers."""

from .dom_pruner import prune_dom
from .waf_prober import generate_browser_headers, probe_waf_signatures
from .playwright_runner import PlaywrightRunner, ScraperTask, compile_extraction_script
from .specialist_handlers import (
    frontend_dom_specialist_handler,
    get_default_specialist_handlers,
    junior_developer_handler,
    network_engineer_handler,
    systems_architect_handler,
)

__all__ = [
    "prune_dom",
    "generate_browser_headers",
    "probe_waf_signatures",
    "PlaywrightRunner",
    "ScraperTask",
    "compile_extraction_script",
    "network_engineer_handler",
    "frontend_dom_specialist_handler",
    "systems_architect_handler",
    "junior_developer_handler",
    "get_default_specialist_handlers",
]