"""Application startup logic (bootstrap, seeding, etc.)."""

import logging
from .domain import Lead
from .portal import PortalService
from .storage import StorageBackend

logger = logging.getLogger("api.startup")


def bootstrap_demo_lead(storage_backend: StorageBackend, portal_service: PortalService) -> None:
    """Bootstrap a default demo lead if none exists."""
    try:
        if not storage_backend.get_lead("demo-lead"):
            demo_lead = Lead("demo-lead", "daily")
            portal_service.publish_sandbox(
                demo_lead,
                "Acme Legal Intelligence",
                [
                    {"case_number": "2026-CV-100", "filing_date": "2026-08-26", "county": "Cook", "status": "Active"},
                    {"case_number": "2026-CV-101", "filing_date": "2026-08-27", "county": "Cook", "status": "Pending"},
                ],
                "https://court.cookcountyil.gov/search",
            )
            logger.info("Bootstrapped demo lead")
    except Exception as e:
        logger.error(f"Failed to bootstrap demo lead: {e}")