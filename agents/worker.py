"""Autonomous Swarm Background Worker for Azure Container Apps (KEDA-scaled).

Consumes job messages from Azure Service Bus, coordinates multi-agent crawler
synthesis, Playwright headless browsing, and persists outputs to Azure PostgreSQL
and Azure Blob Storage.
"""

import logging
import os
import signal
import sys
import time
from typing import Any

from .blob_storage import blob_storage
from .logging_config import get_logger
from .service_bus import JobPayload, JobType, create_queue_broker
from .storage import create_storage_backend

logger = get_logger("worker")


class AutonomousSwarmWorker:
    """Daemon worker process executing asynchronous tasks dispatched via Azure Service Bus."""

    def __init__(self, queue_name: str = "leadops-jobs") -> None:
        self.queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME", queue_name)
        self.storage = create_storage_backend()
        self.broker = create_queue_broker()
        self.running = True
        self._setup_signals()

    def _setup_signals(self) -> None:
        def handle_stop(signum, frame):
            logger.info("Received termination signal (%s). Shutting down worker gracefully...", signum)
            self.running = False

        try:
            signal.signal(signal.SIGINT, handle_stop)
            signal.signal(signal.SIGTERM, handle_stop)
        except (ValueError, AttributeError):
            pass

    def run(self) -> None:
        logger.info("🚀 Autonomous Swarm Worker started. Listening on queue '%s'...", self.queue_name)
        idle_counter = 0

        while self.running:
            try:
                jobs = self.broker.receive_jobs(self.queue_name, max_messages=5, timeout_seconds=5.0)
                if not jobs:
                    idle_counter += 1
                    if idle_counter % 12 == 0:  # Every minute
                        logger.debug("Swarm worker idle. Waiting for incoming jobs...")
                    time.sleep(2.0)
                    continue

                idle_counter = 0
                for job in jobs:
                    self.process_job(job)

            except Exception as e:
                logger.error("Unexpected error in worker loop: %s", e, exc_info=True)
                time.sleep(3.0)

        logger.info("Worker process completed clean exit.")

    def process_job(self, job: JobPayload) -> None:
        """Dispatch job payload to specific agent subsystem."""
        logger.info("Processing job %s: Type=%s LeadID=%s Slug=%s", job.job_id, job.job_type.value, job.lead_id, job.slug)

        try:
            if job.job_type == JobType.SCOUT_EVALUATION:
                self._handle_scout_job(job)
            elif job.job_type == JobType.BUILD_PLAN_EXECUTION:
                self._handle_build_job(job)
            elif job.job_type == JobType.SELECTOR_REPAIR:
                self._handle_repair_job(job)
            elif job.job_type == JobType.DRIFT_CHECK:
                self._handle_drift_job(job)
            elif job.job_type == JobType.LIFECYCLE_EMAIL:
                self._handle_email_job(job)
            else:
                logger.warning("Unrecognized job type: %s", job.job_type)
        except Exception as e:
            logger.error("Failed to execute job %s: %s", job.job_id, e, exc_info=True)

    def _handle_scout_job(self, job: JobPayload) -> None:
        url = job.params.get("source_url")
        jurisdiction = job.params.get("jurisdiction", "")
        company_name = job.params.get("company_name", "")
        logger.info("Executing Scout Recon on: %s", url)

        # Run scout via pipeline
        from .scout_pipeline import ScoutPortalPipeline
        from .portal import PortalService
        portal = PortalService(storage=self.storage)
        pipeline = ScoutPortalPipeline(portal)

        slug = job.slug or pipeline.generate_slug(company_name or url)
        # Process and store preview
        sandbox = pipeline.create_prospect_sandbox(
            slug=slug,
            source_url=url,
            company_name=company_name,
            jurisdiction=jurisdiction,
        )
        logger.info("Scout completed. Generated sandbox: slug=%s", slug)

    def _handle_build_job(self, job: JobPayload) -> None:
        lead_id = job.lead_id
        lead = self.storage.get_lead(lead_id)
        if not lead:
            logger.error("Build job aborted: Lead %s not found in storage", lead_id)
            return

        logger.info("Executing Build Swarm for lead: %s (%s)", lead_id, lead.company_name)
        from .workflow import CustomerJourneyWorkflow
        from .tools.specialist_handlers import get_production_handlers
        handlers = get_production_handlers()
        workflow = CustomerJourneyWorkflow(lead)
        result = workflow.execute_build_iteration(
            objectives=["Build production county scraper", "Verify extraction schema"],
            acceptance_criteria=["25 valid records extracted", "QA score >= 0.85"],
            handlers=handlers,
            checks=[{"name": "schema_validator"}],
        )
        self.storage.save_lead(lead)
        logger.info("Build iteration finished: ready_for_review=%s QA=%.2f", result.ready_for_review, lead.qa_score or 0.0)

    def _handle_repair_job(self, job: JobPayload) -> None:
        lead_id = job.lead_id
        lead = self.storage.get_lead(lead_id)
        if not lead:
            return
        logger.info("Executing Self-Healing selector repair for: %s", lead.company_name)
        from .self_healing import self_healing_engine
        healed_script, pm_report = self_healing_engine.heal_scraper_failure(
            lead=lead,
            failure_stage="DOM_DRIFT",
            error_message=job.params.get("error_message", "Automated drift detected"),
        )
        logger.info("Selector repair completed. Post mortem stored.")

    def _handle_drift_job(self, job: JobPayload) -> None:
        logger.info("Executing scheduled drift probe...")
        from .drift_monitor import RetainerMonitorWorker
        from .portal import PortalService
        portal = PortalService(storage=self.storage)
        worker = RetainerMonitorWorker(self.storage, portal, check_interval_seconds=3600)
        worker.check_all_active_subscriptions()
        logger.info("Drift audit completed.")

    def _handle_email_job(self, job: JobPayload) -> None:
        lead_id = job.lead_id
        lead = self.storage.get_lead(lead_id)
        if not lead:
            return
        event_name = job.params.get("event_name", "outreach")
        from .pitcher import send_lifecycle_email
        send_lifecycle_email(lead, event_name, job.params.get("extra_context", {}))
        self.storage.save_lead(lead)
        logger.info("Lifecycle email sent for lead %s (event: %s)", lead_id, event_name)


if __name__ == "__main__":
    worker = AutonomousSwarmWorker()
    worker.run()
