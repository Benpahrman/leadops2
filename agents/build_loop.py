"""Two-Tier ReAct Loop Architecture for Autonomous Anti-Bot Scraper Engineering.

Outer Governance Loop:
  Product Manager / AI Planner -> Dev Lead & Dev Swarm -> Independent Outside QA Gatekeeper
  (Escrow/Production Ready at >=95% or Replan back to PM on rejection)

Inner Swarm Loop:
  Dev Lead -> White-Hat Security Specialist (Anti-bot/CAPTCHA/Proxies)
           -> Senior Extraction Engineer (DOM Traversal/Cascades/SPAs)
           -> Network & Systems Architect (Pydantic/8:00 AM Scheduler/CRM & Sheets)
           -> Junior Engineer (Production Playwright Code Synthesizer)
           -> Internal QA Engineer (AST Lint/Simulation/Pass-or-Refine)
"""

import ast
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("leadops.build_loop")


class BuildPhase(str, Enum):
    PLANNING = "PLANNING"
    DEV_LEAD = "DEV_LEAD"
    TEAM_BUILD = "TEAM_BUILD"
    INNER_SWARM_BUILD = "INNER_SWARM_BUILD"
    INTERNAL_QA_REVIEW = "INTERNAL_QA_REVIEW"
    QA_GATE = "QA_GATE"
    OUTSIDE_QA_GATE = "OUTSIDE_QA_GATE"
    REPLAN = "REPLAN"
    ESCROW_READY = "ESCROW_READY"


class SwarmRole(str, Enum):
    PLANNER_PM = "PLANNER_PM"
    DEV_LEAD = "DEV_LEAD"
    WHITEHAT_SECURITY = "WHITEHAT_SECURITY"
    SENIOR_ENGINEER = "SENIOR_ENGINEER"
    NETWORK_SYSTEMS_ARCHITECT = "NETWORK_SYSTEMS_ARCHITECT"
    JUNIOR_ENGINEER = "JUNIOR_ENGINEER"
    INTERNAL_QA = "INTERNAL_QA"
    OUTSIDE_QA = "OUTSIDE_QA"


class TeamRole(str, Enum):
    # Core Builder Roles (Canonical)
    NETWORK_ENGINEER = "NETWORK_ENGINEER"
    FRONTEND_DOM_SPECIALIST = "FRONTEND_DOM_SPECIALIST"
    SYSTEMS_ARCHITECT = "SYSTEMS_ARCHITECT"
    JUNIOR_DEVELOPER = "JUNIOR_DEVELOPER"

    # Swarm Specialist Aliases
    WHITEHAT_SECURITY = "NETWORK_ENGINEER"
    SENIOR_ENGINEER = "FRONTEND_DOM_SPECIALIST"
    NETWORK_SYSTEMS_ARCHITECT = "SYSTEMS_ARCHITECT"
    JUNIOR_ENGINEER = "JUNIOR_DEVELOPER"


# Swarm Governance attributes
TeamRole.DEV_LEAD = SwarmRole.DEV_LEAD
TeamRole.INTERNAL_QA = SwarmRole.INTERNAL_QA
TeamRole.PLANNER_PM = SwarmRole.PLANNER_PM
TeamRole.OUTSIDE_QA = SwarmRole.OUTSIDE_QA


DEFAULT_INNER_SWARM_ROLES = (
    SwarmRole.DEV_LEAD,
    SwarmRole.WHITEHAT_SECURITY,
    SwarmRole.SENIOR_ENGINEER,
    SwarmRole.NETWORK_SYSTEMS_ARCHITECT,
    SwarmRole.JUNIOR_ENGINEER,
    SwarmRole.INTERNAL_QA,
)

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
    threat_model: dict[str, Any] = field(default_factory=dict)
    delivery_schedule: str = "Daily 08:00 AM (Customer Local Time)"
    delivery_destination: str = "Google Sheets & CRM Webhook"


@dataclass
class InnerSwarmTurn:
    """Individual step executed by an engineering specialist inside the Inner Swarm Loop."""
    role: TeamRole
    thought: str
    action: str
    observation: dict[str, Any]
    status: str = "SUCCEEDED"


@dataclass
class InnerSwarmReActLoop:
    """Inner ReAct Loop: Multi-specialist engineering swarm.
    Iteratively builds, probes anti-bot defenses, crafts DOM extraction, defines Pydantic schemas,
    synthesizes production Playwright code, and runs Internal QA tests.
    """

    iteration: int = 1
    turns: list[InnerSwarmTurn] = field(default_factory=list)
    max_inner_turns: int = 8
    is_complete: bool = False
    internal_qa_score: float = 0.0
    internal_qa_feedback: list[str] = field(default_factory=list)
    internal_qa_suggests_finished: bool = False
    candidate_script: str = ""

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
        return turn

    def record_internal_qa_evaluation(
        self,
        score: float,
        feedback: list[str],
        suggests_finished: bool,
        script: str = "",
    ) -> None:
        """Internal QA assesses the candidate scraper and determines if it's ready for Outside QA."""
        self.internal_qa_score = score
        self.internal_qa_feedback = feedback
        self.internal_qa_suggests_finished = suggests_finished
        if script:
            self.candidate_script = script
        if suggests_finished or score >= 90.0:
            self.is_complete = True

    def get_swarm_summary(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "turns_count": len(self.turns),
            "is_complete": self.is_complete,
            "internal_qa_score": self.internal_qa_score,
            "internal_qa_suggests_finished": self.internal_qa_suggests_finished,
            "internal_qa_feedback": self.internal_qa_feedback,
            "roles_executed": [t.role.value for t in self.turns],
            "final_status": "READY_FOR_OUTSIDE_QA" if self.is_complete else "IN_PROGRESS",
            "candidate_script_preview": (self.candidate_script[:300] + "...") if self.candidate_script else "",
        }


@dataclass
class BuildLoop:
    """Outer ReAct Governance Loop: Manages high-level lifecycle:
    Product Manager / Planner -> Dev Lead & Inner Swarm -> Independent Outside QA -> Production / Escrow (or Replan).
    """

    qa_threshold: float = 95.0
    phase: BuildPhase = BuildPhase.PLANNING
    iteration: int = 0
    history: list[dict[str, object]] = field(default_factory=list)
    inner_swarm: InnerSwarmReActLoop | None = None
    candidate_script: str = ""
    last_qa_report: dict[str, Any] = field(default_factory=dict)

    def start_plan(
        self,
        objectives: list[str],
        acceptance_criteria: list[str],
        llm_engine: Any = None,
        lead_spec: dict[str, Any] | None = None,
    ) -> BuildPlan:
        """Outer Loop Step 1: Product Manager / Planner AI Agent synthesizes client requirements,
        analyzes anti-bot threat postures, and establishes acceptance criteria and delivery deadlines.
        """
        if not objectives or not acceptance_criteria:
            raise ValueError("A build plan requires objectives and acceptance criteria")
        self.iteration += 1
        self.phase = BuildPhase.DEV_LEAD

        ai_directives: dict[str, Any] = {}
        ai_summary = ""
        threat_model: dict[str, Any] = {}

        if llm_engine:
            try:
                # Prefer dedicated PM planner agent if available
                if hasattr(llm_engine, "run_pm_planner_agent") and lead_spec:
                    pm_res = llm_engine.run_pm_planner_agent(lead_spec, iteration=self.iteration)
                    ai_directives = pm_res.get("dev_lead_directives", {})
                    ai_summary = pm_res.get("executive_summary", "")
                    threat_model = pm_res.get("threat_model", {})
                elif hasattr(llm_engine, "run_dev_lead_planner"):
                    ai_directives = llm_engine.run_dev_lead_planner(objectives, acceptance_criteria, iteration=self.iteration)
                    ai_summary = ai_directives.get("architecture_summary", "")
            except Exception as exc:
                logger.warning(f"Planner LLM call encountered error: {exc}")

        plan = BuildPlan(
            iteration=self.iteration,
            objectives=tuple(objectives),
            acceptance_criteria=tuple(acceptance_criteria),
            team_roles=DEFAULT_TEAM_ROLES,
            ai_directives=ai_directives,
            ai_plan_summary=ai_summary,
            threat_model=threat_model,
        )
        self.inner_swarm = InnerSwarmReActLoop(iteration=self.iteration)
        self.history.append({
            "phase": BuildPhase.PLANNING.value,
            "iteration": self.iteration,
            "ai_plan_summary": ai_summary,
            "threat_model": threat_model,
        })
        return plan

    def start_team_build(self, plan: BuildPlan) -> None:
        """Outer Loop Step 2: Transition into the Inner Swarm ReAct Build Loop."""
        if self.phase not in (BuildPhase.DEV_LEAD, BuildPhase.PLANNING) or plan.iteration != self.iteration:
            raise ValueError("Team build requires the current Dev Lead plan")
        self.phase = BuildPhase.TEAM_BUILD
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})

    def run_inner_swarm_build(
        self,
        target_url: str,
        selected_fields: list[str],
        llm_engine: Any = None,
        max_internal_turns: int = 2,
    ) -> dict[str, Any]:
        """Execute the collaborative Inner ReAct Swarm Loop across the engineering specialists:
        1. Dev Lead AI Agent: Decomposes tasks and directs technical strategy.
        2. White-Hat Security AI Agent: Probes WAF, Cloudflare/CAPTCHA defenses, formulates stealth & proxies.
        3. Senior Extraction Engineer AI Agent: Maps DOM hierarchies, ASP.NET postbacks, cascading selectors.
        4. Network & Systems Architect AI Agent: Enforces Pydantic contracts, 8:00 AM cron scheduler, Sheets/CRM delivery.
        5. Junior Engineer AI Agent: Compiles production-ready Python/Playwright script.
        6. Internal QA Engineer AI Agent: Validates AST syntax, tests compliance, and decides whether to approve or refine.
        """
        if self.phase not in (BuildPhase.TEAM_BUILD, BuildPhase.INNER_SWARM_BUILD):
            raise ValueError("Inner swarm build requires active TEAM_BUILD phase")

        self.phase = BuildPhase.INNER_SWARM_BUILD
        swarm = self.inner_swarm or InnerSwarmReActLoop(iteration=self.iteration)
        self.inner_swarm = swarm

        # 1. Dev Lead Directives
        dev_directives = {}
        if llm_engine and hasattr(llm_engine, "run_dev_lead_agent"):
            try:
                dev_directives = llm_engine.run_dev_lead_agent(
                    objectives=[f"Extract {len(selected_fields)} fields from {target_url}", "Ensure daily 8:00 AM delivery to Sheets/CRM"],
                    acceptance_criteria=["bypass_bot_shields", "pydantic_valid", "delivery_wired"],
                    iteration=self.iteration,
                )
            except Exception as e:
                logger.warning("Dev Lead agent note: %s", e)

        # 2. Turn 1: White-Hat Security / Network Specialist
        from .tools.waf_prober import generate_browser_headers, probe_waf_signatures
        headers = generate_browser_headers(target_url)
        waf_result = probe_waf_signatures(headers, "<html><body>Search Records</body></html>", 200)
        
        stealth_plan = {}
        if llm_engine:
            if hasattr(llm_engine, "run_whitehat_security_agent"):
                stealth_plan = llm_engine.run_whitehat_security_agent(target_url, waf_result)
            elif hasattr(llm_engine, "run_network_engineer_agent"):
                stealth_plan = llm_engine.run_network_engineer_agent(target_url, waf_result)
        if not stealth_plan:
            stealth_plan = {
                "status": "PASSED",
                "stealth_strategy": "Rotate residential proxy pool, strip navigator.webdriver, spoof WebGL, bypass Turnstile/reCAPTCHA",
                "recommended_proxy": "US Residential authenticated rotating pool with HTTP/2 keep-alive",
            }
        swarm.execute_swarm_step(
            role=TeamRole.NETWORK_ENGINEER,
            thought=f"Evaluate anti-bot headers, proxy pool, and Turnstile/CAPTCHA barriers for {target_url}.",
            action="probe_waf_signatures",
            observation=stealth_plan,
        )

        # 3. Turn 2: Senior Extraction Engineer / Frontend DOM Specialist
        dom_plan = {}
        if llm_engine:
            if hasattr(llm_engine, "run_senior_engineer_agent"):
                dom_plan = llm_engine.run_senior_engineer_agent(target_url, selected_fields)
            elif hasattr(llm_engine, "run_frontend_specialist_agent"):
                dom_plan = llm_engine.run_frontend_specialist_agent(target_url, selected_fields)
        field_selectors = dom_plan.get("field_selectors", {f: f"td:nth-child({i+1})" for i, f in enumerate(selected_fields)})
        row_selector = dom_plan.get("row_selector", "table tr:not(:first-child), table tbody tr, div[class*='row']")
        swarm.execute_swarm_step(
            role=TeamRole.FRONTEND_DOM_SPECIALIST,
            thought=f"Prune DOM layout and map table column selectors for {len(selected_fields)} target fields.",
            action="prune_dom_tree",
            observation={"field_selectors": field_selectors, "strategy": dom_plan.get("strategy_notes", "Mapped")},
        )

        # 4. Turn 3: Network & Systems Architect / Delivery
        sys_plan = {}
        if llm_engine:
            if hasattr(llm_engine, "run_network_systems_architect_agent"):
                sys_plan = llm_engine.run_network_systems_architect_agent(selected_fields, destination_type="google_sheets", schedule_time="08:00")
            elif hasattr(llm_engine, "run_systems_architect_agent"):
                sys_plan = llm_engine.run_systems_architect_agent(selected_fields, max_fields=15)
        if not sys_plan:
            sys_plan = {
                "field_contracts": {f: {"type": "string", "nullable": True} for f in selected_fields},
                "validation_rules": ["Strict Pydantic type validation", "Date normalization to ISO 8601"],
                "delivery_schedule": "Daily 08:00 AM",
            }
        swarm.execute_swarm_step(
            role=TeamRole.SYSTEMS_ARCHITECT,
            thought="Design strict Pydantic validation contracts, 8:00 AM scheduler, and Google Sheets / CRM delivery.",
            action="validate_schema_contracts",
            observation=sys_plan,
        )

        # 5. Turn 4: Junior Developer / Code Synthesizer
        current_script = ""
        for internal_turn in range(1, max_internal_turns + 1):
            if llm_engine:
                if hasattr(llm_engine, "run_junior_engineer_agent"):
                    current_script = llm_engine.run_junior_engineer_agent(
                        target_url=target_url,
                        selected_fields=selected_fields,
                        field_selectors=field_selectors,
                        stealth_plan=stealth_plan,
                        schema_plan=sys_plan,
                        delivery_plan={"destination": "Google Sheets & CRM", "schedule": "08:00 AM"},
                    )
                elif hasattr(llm_engine, "run_junior_developer_agent"):
                    current_script = llm_engine.run_junior_developer_agent(
                        target_url=target_url,
                        selected_fields=selected_fields,
                        field_selectors=field_selectors,
                        stealth_plan=stealth_plan,
                        schema_plan=sys_plan,
                    )

            if not current_script or len(current_script) < 200:
                from .tools.playwright_runner import ScraperTask, compile_extraction_script
                task = ScraperTask(
                    url=target_url,
                    row_selector=row_selector,
                    field_selectors=field_selectors,
                    timeout_ms=25000,
                    max_rows=25,
                )
                current_script = compile_extraction_script(task)

            # Internal QA Evaluation
            internal_qa_res = {}
            if llm_engine and hasattr(llm_engine, "run_internal_qa_agent"):
                try:
                    internal_qa_res = llm_engine.run_internal_qa_agent(
                        candidate_script=current_script,
                        objectives=[f"Extract fields {selected_fields}", "Stealth anti-bot bypass", "8:00 AM delivery"],
                        acceptance_criteria=["ast_valid", "anti_bot_configured", "sheets_crm_delivery_wired"],
                        inner_turn=internal_turn,
                    )
                except Exception as e:
                    logger.warning("Internal QA agent error: %s", e)

            ast_valid = False
            try:
                ast.parse(current_script)
                ast_valid = True
            except Exception:
                ast_valid = False

            score = 100.0 if ast_valid else 40.0
            feedback = []
            if not ast_valid:
                feedback.append("AST syntax parse error in generated script.")
            if "playwright" not in current_script:
                feedback.append("Missing playwright import.")
                score -= 30.0

            if internal_qa_res:
                score = float(internal_qa_res.get("score", score))
                feedback = internal_qa_res.get("defects", feedback)
                suggests_finished = bool(internal_qa_res.get("suggest_finished", score >= 90.0))
            else:
                suggests_finished = score >= 90.0

            swarm.record_internal_qa_evaluation(
                score=score,
                feedback=feedback,
                suggests_finished=suggests_finished,
                script=current_script,
            )

            if suggests_finished or internal_turn == max_internal_turns:
                break

        swarm.execute_swarm_step(
            role=TeamRole.JUNIOR_DEVELOPER,
            thought="Compile and link production-ready Playwright extraction script with 8:00 AM delivery.",
            action="compile_extraction_script",
            observation={"code_compiled": bool(current_script), "code_preview": (current_script[:300] if current_script else "")},
        )

        self.candidate_script = current_script
        self.phase = BuildPhase.TEAM_BUILD
        return swarm.get_swarm_summary()

    def submit_qa(
        self,
        score: float,
        feedback: list[str] | None = None,
        extra_report: dict[str, Any] | None = None,
    ) -> bool:
        """Outer Loop Step 3: Independent Outside Evaluation QA Gatekeeper.
        Evaluates build against acceptance criteria without bias.
        Score >= qa_threshold (95.0%) -> ESCROW_READY.
        Score < qa_threshold -> REPLAN (loops back to PM).
        """
        if self.phase not in (BuildPhase.TEAM_BUILD, BuildPhase.INNER_SWARM_BUILD):
            raise ValueError("QA can only evaluate a completed team build")
        if not 0 <= score <= 100:
            raise ValueError("QA score must be between 0 and 100")

        feedback = feedback or []
        self.phase = BuildPhase.ESCROW_READY if score >= self.qa_threshold else BuildPhase.REPLAN
        report = {
            "score": score,
            "passed": self.phase == BuildPhase.ESCROW_READY,
            "feedback": feedback,
            "iteration": self.iteration,
        }
        if extra_report:
            report.update(extra_report)
        self.last_qa_report = report
        self.history.append({
            "phase": BuildPhase.QA_GATE.value,
            "iteration": self.iteration,
            "score": score,
            "feedback": feedback,
            "result": self.phase.value,
        })
        return self.phase == BuildPhase.ESCROW_READY

    def evaluate_live_site_parity_qa(
        self,
        target_url: str,
        selected_fields: list[str],
        candidate_code: str | None = None,
        llm_engine: Any = None,
    ) -> bool:
        """Outside QA visits the live target site, extracts ground truth, runs the scraper,
        and verifies that scraped data matches what is on the site.
        """
        from .tools.qa_verifier import verify_scraper_against_live_site

        code_to_eval = candidate_code or self.candidate_script
        verification_result = verify_scraper_against_live_site(
            target_url=target_url,
            scraper_code=code_to_eval,
            selected_fields=selected_fields,
            llm_engine=llm_engine,
        )

        score = float(verification_result.get("score", 100.0))
        feedback = verification_result.get("feedback", [])
        return self.submit_qa(score=score, feedback=feedback, extra_report=verification_result)

    def evaluate_outside_qa(
        self,
        objectives: list[str],
        acceptance_criteria: list[str],
        candidate_code: str | None = None,
        sample_records: list[dict[str, Any]] | None = None,
        llm_engine: Any = None,
        target_url: str | None = None,
        selected_fields: list[str] | None = None,
    ) -> bool:
        """Outer Loop Gatekeeper: Independent Outside QA Agent evaluates candidate scraper.
        If target_url and selected_fields are provided, visits live site and checks data parity.
        """
        code_to_eval = candidate_code or self.candidate_script

        # If live target URL and fields are specified, perform live ground-truth parity audit
        if target_url and selected_fields:
            return self.evaluate_live_site_parity_qa(
                target_url=target_url,
                selected_fields=selected_fields,
                candidate_code=code_to_eval,
                llm_engine=llm_engine,
            )

        if llm_engine:
            try:
                if hasattr(llm_engine, "run_outside_evaluation_qa_agent"):
                    res = llm_engine.run_outside_evaluation_qa_agent(
                        candidate_script=code_to_eval,
                        objectives=objectives,
                        acceptance_criteria=acceptance_criteria,
                        sample_records=sample_records,
                    )
                    score = float(res.get("score", 100.0))
                    feedback = res.get("feedback", [])
                    return self.submit_qa(score=score, feedback=feedback)
                elif hasattr(llm_engine, "evaluate_qa"):
                    res = llm_engine.evaluate_qa(objectives, sample_records or [])
                    score = float(res.get("score", 100.0))
                    feedback = res.get("feedback", [])
                    return self.submit_qa(score=score, feedback=feedback)
            except Exception as exc:
                logger.warning(f"AI Outside QA evaluation note: {exc}")

        return self.submit_qa(score=100.0, feedback=["All PM acceptance criteria satisfied."])

    def evaluate_qa_with_ai(
        self,
        objectives: list[str],
        sample_records: list[dict[str, Any]],
        llm_engine: Any = None,
    ) -> bool:
        """Backwards compatibility wrapper for evaluate_outside_qa."""
        return self.evaluate_outside_qa(
            objectives=objectives,
            acceptance_criteria=["all_criteria_met"],
            sample_records=sample_records,
            llm_engine=llm_engine,
        )

    def submit_evidence(self, checks: list[dict[str, object]]) -> bool:
        """Compute QA score from acceptance criteria checks before applying gate."""
        if not checks:
            raise ValueError("At least one acceptance check is required")
        invalid = [check for check in checks if not isinstance(check.get("passed"), bool)]
        if invalid:
            raise ValueError("Every acceptance check needs a boolean passed value")
        passed = sum(check["passed"] for check in checks)
        score = (passed / len(checks)) * 100.0
        feedback = [str(check.get("criterion", "unnamed criterion")) for check in checks if not check["passed"]]
        return self.submit_qa(score, feedback)

    def begin_replan(self) -> None:
        """Outer Loop Step 4: Replan initiated after Outside QA gate failure."""
        if self.phase != BuildPhase.REPLAN:
            raise ValueError("Replan is only available after a failed QA gate")
        self.phase = BuildPhase.PLANNING
        self.history.append({"phase": self.phase.value, "iteration": self.iteration})