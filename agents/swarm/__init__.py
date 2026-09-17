"""Autonomous Dev Swarm & Pipeline Engine package."""

from agents.swarm.build_loop import (
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
from agents.swarm.workflow import ProjectWorkflow, BuildIterationResult
from agents.swarm.self_healing import SelfHealingEngine, PostMortemReport
from agents.swarm.drift_monitor import RetainerMonitorWorker, DriftIncident, DriftSeverity
from agents.swarm.scraper_catalog import (
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
from agents.swarm.delivery import (
    DeliveryPlan,
    GoogleSheetsDestination,
    WebhookDestination,
    DeliveryJob,
    compute_webhook_signature,
    test_webhook_connection,
    test_notion_connection,
)
from agents.swarm.datasets import (
    AUTHENTIC_REGISTRY_DATASETS,
    DynamicRegistryEntry,
    UniversalWebDatasetRegistry,
    resolve_record_verification_url,
)
from agents.swarm.job_runner import LocalBuildRunner, JobStatus, SpecialistJob

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

