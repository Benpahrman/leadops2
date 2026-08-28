"""Reactive build-loop contract: plan, build, independent QA, replan."""

from dataclasses import dataclass, field
from enum import Enum


class BuildPhase(str, Enum):
    PLANNING = "PLANNING"
    DEV_LEAD = "DEV_LEAD"
    TEAM_BUILD = "TEAM_BUILD"
    QA_GATE = "QA_GATE"
    REPLAN = "REPLAN"
    ESCROW_READY = "ESCROW_READY"


class TeamRole(str, Enum):
    NETWORK_ENGINEER = "NETWORK_ENGINEER"
    FRONTEND_DOM_SPECIALIST = "FRONTEND_DOM_SPECIALIST"
    SYSTEMS_ARCHITECT = "SYSTEMS_ARCHITECT"
    JUNIOR_DEVELOPER = "JUNIOR_DEVELOPER"


DEFAULT_TEAM_ROLES = (
    TeamRole.NETWORK_ENGINEER,
    TeamRole.FRONTEND_DOM_SPECIALIST,
    TeamRole.SYSTEMS_ARCHITECT,
    TeamRole.JUNIOR_DEVELOPER,
)


@dataclass(frozen=True)
class BuildPlan:
    iteration: int
    objectives: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    team_roles: tuple[TeamRole, ...] = DEFAULT_TEAM_ROLES


@dataclass
class BuildLoop:
    qa_threshold: float = 95.0
    phase: BuildPhase = BuildPhase.PLANNING
    iteration: int = 0
    history: list[dict[str, object]] = field(default_factory=list)

    def start_plan(self, objectives: list[str], acceptance_criteria: list[str]) -> BuildPlan:
        if not objectives or not acceptance_criteria:
            raise ValueError("A build plan requires objectives and acceptance criteria")
        self.iteration += 1
        self.phase = BuildPhase.DEV_LEAD
        plan = BuildPlan(
            self.iteration,
            tuple(objectives),
            tuple(acceptance_criteria),
        )
        self.history.append({"phase": BuildPhase.PLANNING.value, "iteration": self.iteration})
        return plan

    def start_team_build(self, plan: BuildPlan) -> None:
        if self.phase != BuildPhase.DEV_LEAD or plan.iteration != self.iteration:
            raise ValueError("Team build requires the current Dev Lead plan")
        self.phase = BuildPhase.TEAM_BUILD
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})

    def submit_qa(self, score: float, feedback: list[str] | None = None) -> bool:
        if self.phase != BuildPhase.TEAM_BUILD:
            raise ValueError("QA can only evaluate a completed team build")
        if not 0 <= score <= 100:
            raise ValueError("QA score must be between 0 and 100")
        feedback = feedback or []
        self.phase = BuildPhase.ESCROW_READY if score >= self.qa_threshold else BuildPhase.REPLAN
        self.history.append({
            "phase": BuildPhase.QA_GATE.value,
            "iteration": self.iteration,
            "score": score,
            "feedback": feedback,
            "result": self.phase.value,
        })
        return self.phase == BuildPhase.ESCROW_READY

    def submit_evidence(self, checks: list[dict[str, object]]) -> bool:
        """Compute the QA score from acceptance checks before applying the gate."""
        if not checks:
            raise ValueError("At least one acceptance check is required")
        invalid = [check for check in checks if not isinstance(check.get("passed"), bool)]
        if invalid:
            raise ValueError("Every acceptance check needs a boolean passed value")
        passed = sum(check["passed"] for check in checks)
        score = (passed / len(checks)) * 100
        feedback = [str(check.get("criterion", "unnamed criterion")) for check in checks if not check["passed"]]
        return self.submit_qa(score, feedback)

    def begin_replan(self) -> None:
        if self.phase != BuildPhase.REPLAN:
            raise ValueError("Replan is only available after a failed QA gate")
        self.phase = BuildPhase.PLANNING
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})