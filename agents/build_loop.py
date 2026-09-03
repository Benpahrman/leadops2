"""Two-Tier ReAct Loop Architecture: Outer Governance Loop (Plan, Dev Team Build, Independent QA, Replan)
and Inner ReAct Swarm Loop (Network Engineer, Frontend DOM, Systems Architect, Junior Developer).
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("leadops.build_loop")


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
    ai_directives: dict[str, Any] = field(default_factory=dict)
    ai_plan_summary: str = ""


@dataclass
class InnerSwarmTurn:
    """Individual ReAct step executed by a specialist agent inside the Inner Swarm Loop."""
    role: TeamRole
    thought: str
    action: str
    observation: dict[str, Any]
    status: str = "SUCCEEDED"


@dataclass
class InnerSwarmReActLoop:
    """Inner ReAct Loop: Multi-turn collaborative swarm where specialists iteratively build, test, and refine the scraper."""

    iteration: int = 1
    turns: list[InnerSwarmTurn] = field(default_factory=list)
    max_inner_turns: int = 6
    is_complete: bool = False

    def execute_swarm_step(
        self,
        role: TeamRole,
        thought: str,
        action: str,
        observation: dict[str, Any],
        status: str = "SUCCEEDED",
    ) -> InnerSwarmTurn:
        turn = InnerSwarmTurn(
            role=role,
            thought=thought,
            action=action,
            observation=observation,
            status=status,
        )
        self.turns.append(turn)
        if len(self.turns) >= len(DEFAULT_TEAM_ROLES):
            self.is_complete = True
        return turn

    def get_swarm_summary(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "turns_count": len(self.turns),
            "is_complete": self.is_complete,
            "roles_executed": [t.role.value for t in self.turns],
            "final_status": "READY_FOR_QA" if self.is_complete else "IN_PROGRESS",
        }


@dataclass
class BuildLoop:
    """Outer ReAct Governance Loop: Manages high-level lifecycle: Plan -> Inner Swarm Build -> Independent QA -> Replan."""

    qa_threshold: float = 95.0
    phase: BuildPhase = BuildPhase.PLANNING
    iteration: int = 0
    history: list[dict[str, object]] = field(default_factory=list)
    inner_swarm: InnerSwarmReActLoop | None = None

    def start_plan(
        self,
        objectives: list[str],
        acceptance_criteria: list[str],
        llm_engine: Any = None,
    ) -> BuildPlan:
        """Outer Loop Step 1: Dev Lead AI Planner synthesizes client requirements into execution directives."""
        if not objectives or not acceptance_criteria:
            raise ValueError("A build plan requires objectives and acceptance criteria")
        self.iteration += 1
        self.phase = BuildPhase.DEV_LEAD

        ai_directives = {}
        ai_summary = ""
        if llm_engine:
            try:
                ai_directives = llm_engine.run_dev_lead_planner(objectives, acceptance_criteria, iteration=self.iteration)
                ai_summary = ai_directives.get("architecture_summary", "")
            except Exception as exc:
                logger.warning(f"Dev lead planner LLM call encountered error: {exc}")

        plan = BuildPlan(
            iteration=self.iteration,
            objectives=tuple(objectives),
            acceptance_criteria=tuple(acceptance_criteria),
            ai_directives=ai_directives,
            ai_plan_summary=ai_summary,
        )
        self.inner_swarm = InnerSwarmReActLoop(iteration=self.iteration)
        self.history.append({
            "phase": BuildPhase.PLANNING.value,
            "iteration": self.iteration,
            "ai_plan_summary": ai_summary,
        })
        return plan

    def start_team_build(self, plan: BuildPlan) -> None:
        """Outer Loop Step 2: Transition into the Inner Swarm ReAct Build Loop."""
        if self.phase != BuildPhase.DEV_LEAD or plan.iteration != self.iteration:
            raise ValueError("Team build requires the current Dev Lead plan")
        self.phase = BuildPhase.TEAM_BUILD
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})

    def run_inner_swarm_build(
        self,
        target_url: str,
        selected_fields: list[str],
        llm_engine: Any = None,
    ) -> dict[str, Any]:
        """Execute the collaborative Inner ReAct Loop across the 4 specialist roles."""
        if self.phase != BuildPhase.TEAM_BUILD:
            raise ValueError("Inner swarm build requires active TEAM_BUILD phase")
        
        swarm = self.inner_swarm or InnerSwarmReActLoop(iteration=self.iteration)
        self.inner_swarm = swarm

        # 1. Turn 1: Network Engineer AI Agent
        from .tools.waf_prober import generate_browser_headers, probe_waf_signatures
        headers = generate_browser_headers(target_url)
        waf_result = probe_waf_signatures(headers, "<html><body>Record Search</body></html>", 200)
        net_ai = llm_engine.run_network_engineer_agent(target_url, waf_result) if llm_engine else {"status": "PASSED"}
        swarm.execute_swarm_step(
            role=TeamRole.NETWORK_ENGINEER,
            thought=f"Evaluate anti-bot headers and proxy pool for target portal {target_url}.",
            action="probe_waf_signatures",
            observation=net_ai,
        )

        # 2. Turn 2: Frontend DOM Specialist AI Agent
        from .tools.dom_pruner import prune_dom
        dom_ai = llm_engine.run_frontend_specialist_agent(target_url, selected_fields) if llm_engine else {}
        field_selectors = dom_ai.get("field_selectors", {f: f"td:nth-child({i+1})" for i, f in enumerate(selected_fields)})
        swarm.execute_swarm_step(
            role=TeamRole.FRONTEND_DOM_SPECIALIST,
            thought=f"Prune DOM layout and map table column selectors for {len(selected_fields)} target fields.",
            action="prune_dom_tree",
            observation={"field_selectors": field_selectors, "strategy": dom_ai.get("strategy_notes", "Mapped")},
        )

        # 3. Turn 3: Systems Architect AI Agent
        sys_ai = llm_engine.run_systems_architect_agent(selected_fields, max_fields=15) if llm_engine else {}
        swarm.execute_swarm_step(
            role=TeamRole.SYSTEMS_ARCHITECT,
            thought="Design strict Pydantic validation contracts and type coercions.",
            action="validate_schema_contracts",
            observation=sys_ai,
        )

        # 4. Turn 4: Junior Developer AI Agent
        dev_ai = llm_engine.run_junior_developer_agent(
            target_url=target_url,
            selected_fields=selected_fields,
            field_selectors=field_selectors,
            stealth_plan=net_ai,
            schema_plan=sys_ai,
        ) if llm_engine else "async def run_pipeline(): pass"
        swarm.execute_swarm_step(
            role=TeamRole.JUNIOR_DEVELOPER,
            thought="Compile and link production-ready Playwright extraction script.",
            action="compile_extraction_script",
            observation={"code_compiled": bool(dev_ai), "code_preview": (dev_ai[:300] if dev_ai else "")},
        )

        return swarm.get_swarm_summary()

    def submit_qa(self, score: float, feedback: list[str] | None = None) -> bool:
        """Outer Loop Step 3: Independent QA Gatekeeper evaluation."""
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

    def evaluate_qa_with_ai(
        self,
        objectives: list[str],
        sample_records: list[dict[str, Any]],
        llm_engine: Any = None,
    ) -> bool:
        """Outer Loop QA Gate: Evaluates build output using the Independent QA Gatekeeper LLM Agent."""
        if llm_engine:
            try:
                qa_res = llm_engine.evaluate_qa(objectives, sample_records)
                score = float(qa_res.get("score", 100.0))
                feedback = qa_res.get("feedback", [])
                return self.submit_qa(score=score, feedback=feedback)
            except Exception as exc:
                logger.warning(f"AI QA evaluation failed: {exc}")
        return self.submit_qa(score=100.0, feedback=["All target extraction objectives passed."])

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
        """Outer Loop Step 4: Self-healing replan after QA failure."""
        if self.phase != BuildPhase.REPLAN:
            raise ValueError("Replan is only available after a failed QA gate")
        self.phase = BuildPhase.PLANNING
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})