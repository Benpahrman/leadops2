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

    def run(self, plan: BuildPlan) -> ArtifactManifest | None:
        self.jobs = [SpecialistJob(role) for role in plan.team_roles]
        manifest = ArtifactManifest(plan.iteration)
        for job in self.jobs:
            job.status = JobStatus.RUNNING
            self.progress.publish(job.role.value, ProgressStatus.ACTIVE, "Work is in progress")
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
                return None
            job.status = JobStatus.SUCCEEDED
            self.progress.publish(
                job.role.value,
                ProgressStatus.COMPLETE,
                "Work completed and sent for independent review",
            )
        return manifest if manifest.qa_handoff()["ready_for_qa"] else None