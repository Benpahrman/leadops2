"""Autonomous Dev Swarm & Pipeline Engine package."""

from .build_loop import (
    BuildLoop,
    BuildPhase,
    BuildPlan,
    DEFAULT_TEAM_ROLES,
    DEFAULT_INNER_SWARM_ROLES,
    TeamRole,
    SwarmRole,
    InnerSwarmTurn,
    InnerSwarmReActLoop,
)
from .workflow import ProjectWorkflow, BuildIterationResult
from .self_healing import SelfHealingEngine, PostMortemReport
from .drift_monitor import RetainerMonitorWorker, DriftIncident, DriftSeverity
from .scraper_catalog import (
    load_json,
    inspect_lead_artifact,
    build_catalog,
    write_catalog_files,
    get_catalog,
    search_catalog,
    get_scraper_source_code,
    get_scraper_output_data,
    execute_scraper_on_demand,
)
from .delivery import (
    DeliveryPlan,
    GoogleSheetsDestination,
    WebhookDestination,
    DeliveryJob,
    compute_webhook_signature,
    test_webhook_connection,
    test_notion_connection,
)
from .datasets import (
    AUTHENTIC_REGISTRY_DATASETS,
    DynamicRegistryEntry,
    UniversalWebDatasetRegistry,
    resolve_record_verification_url,
)
from .job_runner import LocalBuildRunner, JobStatus, SpecialistJob

__all__ = [
    "BuildLoop",
    "BuildPhase",
    "BuildPlan",
    "DEFAULT_TEAM_ROLES",
    "DEFAULT_INNER_SWARM_ROLES",
    "TeamRole",
    "SwarmRole",
    "InnerSwarmTurn",
    "InnerSwarmReActLoop",
    "ProjectWorkflow",
    "BuildIterationResult",
    "SelfHealingEngine",
    "PostMortemReport",
    "RetainerMonitorWorker",
    "DriftIncident",
    "DriftSeverity",
    "load_json",
    "inspect_lead_artifact",
    "build_catalog",
    "write_catalog_files",
    "get_catalog",
    "search_catalog",
    "get_scraper_source_code",
    "get_scraper_output_data",
    "execute_scraper_on_demand",
    "DeliveryPlan",
    "GoogleSheetsDestination",
    "WebhookDestination",
    "DeliveryJob",
    "compute_webhook_signature",
    "test_webhook_connection",
    "test_notion_connection",
    "AUTHENTIC_REGISTRY_DATASETS",
    "DynamicRegistryEntry",
    "UniversalWebDatasetRegistry",
    "resolve_record_verification_url",
    "LocalBuildRunner",
    "JobStatus",
    "SpecialistJob",
]

