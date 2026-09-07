"""Free local runner for Builder Team work items and QA handoff."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .artifacts import ArtifactManifest
from .build_loop import BuildPlan, TeamRole
from .progress import ProgressFeed, ProgressStatus


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class SpecialistJob:
    role: TeamRole
    status: JobStatus = JobStatus.PENDING
    error: str | None = None


@dataclass
class LocalBuildRunner:
    handlers: dict[TeamRole, Callable[[BuildPlan], str]]
    jobs: list[SpecialistJob] = field(default_factory=list)
    progress: ProgressFeed = field(default_factory=ProgressFeed)
    progress_callback: Callable = None

    def run(self, plan: BuildPlan) -> ArtifactManifest | None:
        self.jobs = [SpecialistJob(role) for role in plan.team_roles]
        manifest = ArtifactManifest(plan.iteration, required_roles=set(plan.team_roles))
        for idx, job in enumerate(self.jobs):
            job.status = JobStatus.RUNNING
            self.progress.publish(job.role.value, ProgressStatus.ACTIVE, "Work is in progress")
            
            role_slug = job.role.value.lower()
            if self.progress_callback:
                progress_pct = 20 + int((idx / len(self.jobs)) * 60)
                self.progress_callback(
                    None,
                    progress_pct,
                    f"Agent {job.role.value} is running...",
                    details={"active_agent": role_slug, "status": "ACTIVE"}
                )
                
            try:
                handler = self.handlers[job.role]
                content = handler(plan)
                manifest.add(
                    f"{job.role.value.lower()}-{plan.iteration}",
                    job.role,
                    "specialist_report",
                    content,
                )
            except (KeyError, ValueError) as error:
                job.status = JobStatus.FAILED
                job.error = str(error)
                self.progress.publish(
                    job.role.value,
                    ProgressStatus.BLOCKED,
                    "Work needs attention before independent review",
                )
                if self.progress_callback:
                    self.progress_callback(
                        None,
                        20 + int((idx / len(self.jobs)) * 60),
                        f"Agent {job.role.value} failed: {error}",
                        details={"active_agent": role_slug, "status": "BLOCKED"}
                    )
                return None
            job.status = JobStatus.SUCCEEDED
            self.progress.publish(
                job.role.value,
                ProgressStatus.COMPLETE,
                "Work completed and sent for independent review",
            )
            if self.progress_callback:
                progress_pct = 20 + int(((idx + 1) / len(self.jobs)) * 60)
                self.progress_callback(
                    None,
                    progress_pct,
                    f"Agent {job.role.value} completed work.",
                    details={"active_agent": role_slug, "status": "COMPLETE"}
                )
        return manifest if manifest.qa_handoff()["ready_for_qa"] else None