import ast
import unittest
from unittest.mock import MagicMock

from agents.build_loop import (
    BuildLoop,
    BuildPhase,
    DEFAULT_TEAM_ROLES,
    DEFAULT_INNER_SWARM_ROLES,
    TeamRole,
    InnerSwarmReActLoop,
)
from agents.llm_client import LLMAgentEngine
from agents.tools.playwright_runner import ScraperTask, compile_extraction_script


class BuildLoopTests(unittest.TestCase):
    def test_qa_failure_returns_to_planning(self):
        loop = BuildLoop()
        plan = loop.start_plan(["map portal"], ["25 valid preview rows"])
        loop.start_team_build(plan)

        self.assertFalse(loop.submit_qa(91, ["missing filing date"]))
        self.assertEqual(loop.phase, BuildPhase.REPLAN)
        loop.begin_replan()
        self.assertEqual(loop.phase, BuildPhase.PLANNING)

    def test_qa_pass_unlocks_escrow(self):
        loop = BuildLoop()
        plan = loop.start_plan(["build feed"], ["95 percent valid"])
        loop.start_team_build(plan)

        self.assertTrue(loop.submit_qa(95))
        self.assertEqual(loop.phase, BuildPhase.ESCROW_READY)

    def test_evidence_submission_computes_score_and_replans(self):
        loop = BuildLoop()
        plan = loop.start_plan(["build feed"], ["portal loads", "rows validate"])
        loop.start_team_build(plan)

        self.assertFalse(loop.submit_evidence([
            {"criterion": "portal loads", "passed": True},
            {"criterion": "rows validate", "passed": False},
        ]))
        self.assertEqual(loop.phase, BuildPhase.REPLAN)
        self.assertEqual(loop.history[-1]["score"], 50.0)

    def test_plan_includes_cross_functional_builder_team(self):
        plan = BuildLoop().start_plan(["build feed"], ["feed passes validation"])
        self.assertEqual(plan.team_roles, DEFAULT_TEAM_ROLES)
        self.assertIn(TeamRole.NETWORK_ENGINEER, plan.team_roles)
        self.assertIn(TeamRole.FRONTEND_DOM_SPECIALIST, plan.team_roles)
        self.assertIn(TeamRole.SYSTEMS_ARCHITECT, plan.team_roles)
        self.assertIn(TeamRole.JUNIOR_DEVELOPER, plan.team_roles)

    def test_qa_cannot_run_before_team_build(self):
        with self.assertRaises(ValueError):
            BuildLoop().submit_qa(99)

    def test_pm_planner_agent_formulates_anti_bot_threat_and_8am_delivery(self):
        """Test Product Manager / AI Planner Agent generates threat model, acceptance criteria, and 8 AM schedule."""
        engine = LLMAgentEngine()
        lead_spec = {
            "company_name": "Apex Legal Research",
            "source_url": "https://cookcountyclerkofcourt.org/probate",
            "selected_fields": ["case_number", "filing_date", "decedent_name", "status"],
            "delivery_schedule": "Daily 08:00 AM",
            "destination": "Google Sheets & CRM Webhook",
        }
        pm_plan = engine.run_pm_planner_agent(lead_spec)

        self.assertIn("objectives", pm_plan)
        self.assertIn("acceptance_criteria", pm_plan)
        self.assertIn("threat_model", pm_plan)
        self.assertIn("delivery_requirements", pm_plan)

        # Verify threat model recognizes bot shields and Turnstile/CAPTCHA
        bot_shields = pm_plan["threat_model"].get("bot_shields", [])
        self.assertTrue(any("cloudflare" in str(s).lower() or "bot" in str(s).lower() for s in bot_shields))

        # Verify 8:00 AM delivery requirement
        self.assertEqual(pm_plan["delivery_requirements"]["schedule"], "Daily 08:00 AM")
        self.assertIn("Google Sheets", pm_plan["delivery_requirements"]["destination"])

    def test_inner_swarm_specialist_turns_and_internal_qa(self):
        """Test the Inner Swarm ReAct loop coordinating all engineering specialists and Internal QA."""
        loop = BuildLoop()
        plan = loop.start_plan(
            objectives=["Extract probate filings", "Bypass Cloudflare Turnstile", "Deliver at 08:00 AM to Google Sheets"],
            acceptance_criteria=["stealth_probe_pass", "captcha_bypass_configured", "schema_contracts_valid", "sheets_crm_delivery_ready"],
        )
        loop.start_team_build(plan)

        # Run inner swarm build
        engine = LLMAgentEngine()
        summary = loop.run_inner_swarm_build(
            target_url="https://cookcountyclerkofcourt.org/probate",
            selected_fields=["case_number", "filing_date", "decedent_name", "status"],
            llm_engine=engine,
            max_internal_turns=2,
        )

        self.assertTrue(summary["is_complete"])
        self.assertEqual(summary["final_status"], "READY_FOR_OUTSIDE_QA")
        self.assertGreaterEqual(summary["internal_qa_score"], 90.0)

        # Verify executed roles in inner loop
        roles = summary["roles_executed"]
        self.assertIn(TeamRole.NETWORK_ENGINEER.value, roles)
        self.assertIn(TeamRole.FRONTEND_DOM_SPECIALIST.value, roles)
        self.assertIn(TeamRole.SYSTEMS_ARCHITECT.value, roles)
        self.assertIn(TeamRole.JUNIOR_DEVELOPER.value, roles)

    def test_internal_qa_defect_detection_and_refinement(self):
        """Test that Internal QA catches defects, requests revisions, and approves once clean."""
        swarm = InnerSwarmReActLoop(iteration=1)

        # Turn 1: Defective code with missing stealth
        swarm.record_internal_qa_evaluation(
            score=60.0,
            feedback=["Missing Cloudflare Turnstile solver hook", "Missing navigator.webdriver stealth"],
            suggests_finished=False,
            script="def run_pipeline(): pass",
        )
        self.assertFalse(swarm.is_complete)
        self.assertFalse(swarm.internal_qa_suggests_finished)

        # Turn 2: Repaired code with full anti-bot stealth
        swarm.record_internal_qa_evaluation(
            score=95.0,
            feedback=["All anti-bot and 8:00 AM delivery criteria verified."],
            suggests_finished=True,
            script="""
from playwright.async_api import async_playwright
async def apply_stealth(context): pass
async def run_pipeline(): return [{'case_number': '2026-P-001'}]
""",
        )
        self.assertTrue(swarm.is_complete)
        self.assertTrue(swarm.internal_qa_suggests_finished)

    def test_compiled_scraper_has_antibot_captchas_and_8am_delivery(self):
        """Test that synthesized scraper code is clean Python with anti-bot, Turnstile, Pydantic, and 8:00 AM delivery."""
        task = ScraperTask(
            url="https://example.gov/probate/cases",
            row_selector="table.results tr:not(:first-child)",
            field_selectors={
                "case_number": "td:nth-child(1)",
                "filing_date": "td:nth-child(2)",
                "decedent_name": "td:nth-child(3)",
                "status": "td:nth-child(4)",
            },
            timeout_ms=30000,
            max_rows=50,
        )
        script = compile_extraction_script(task)

        # 1. AST syntax parsing - zero syntax errors allowed
        parsed_ast = ast.parse(script)
        self.assertIsNotNone(parsed_ast)

        # 2. Anti-bot stealth verification
        self.assertIn("apply_stealth_evasions", script)
        self.assertIn("webdriver", script)
        self.assertIn("WebGLRenderingContext", script)

        # 3. CAPTCHA handling verification (Cloudflare Turnstile, reCAPTCHA)
        self.assertIn("handle_captchas_and_challenges", script)
        self.assertIn("Turnstile", script)
        self.assertIn("recaptcha", script)

        # 4. Pydantic validation model verification
        self.assertIn("class RecordSchema(BaseModel):", script)
        self.assertIn("case_number", script)
        self.assertIn("filing_date", script)

        # 5. Delivery to Google Sheets & CRM Webhook
        self.assertIn("def deliver_records(records:", script)
        self.assertIn("GOOGLE_SHEETS_ID", script)
        self.assertIn("CRM_WEBHOOK_URL", script)

        # 6. Daily 8:00 AM scheduler daemon verification
        self.assertIn("def run_daily_8am_scheduler():", script)
        self.assertIn("08:00", script)
        self.assertIn("--schedule", script)
        self.assertIn("--run-now", script)

    def test_full_two_loop_governance_replan_and_pass(self):
        """End-to-end test of the complete 2-Loop system:
        Outer Iteration 1: PM plan -> Dev build -> Outside QA rejects (<95%) -> Replan back to PM
        Outer Iteration 2: PM replans -> Dev build -> Outside QA passes (>=95%) -> Escrow Ready!
        """
        loop = BuildLoop()
        engine = LLMAgentEngine()

        # --- OUTER LOOP ITERATION 1 ---
        plan_iter1 = loop.start_plan(
            objectives=["Scrape tax liens", "Daily 8 AM sync"],
            acceptance_criteria=["lien_id_present", "amount_valid", "captcha_bypass"],
            llm_engine=engine,
        )
        self.assertEqual(loop.phase, BuildPhase.DEV_LEAD)
        self.assertEqual(loop.iteration, 1)

        loop.start_team_build(plan_iter1)
        self.assertEqual(loop.phase, BuildPhase.TEAM_BUILD)

        # Run inner swarm
        summary1 = loop.run_inner_swarm_build(
            target_url="https://county.gov/liens",
            selected_fields=["lien_id", "amount", "owner"],
            llm_engine=engine,
        )
        self.assertTrue(summary1["is_complete"])

        # Outside QA evaluates and rejects (e.g. 75% due to dynamic token barrier)
        outside_qa_pass_1 = loop.submit_qa(score=75.0, feedback=["Cloudflare Turnstile token not verified", "Missing lien_id"])
        self.assertFalse(outside_qa_pass_1)
        self.assertEqual(loop.phase, BuildPhase.REPLAN)

        # Transition back to PM for replan
        loop.begin_replan()
        self.assertEqual(loop.phase, BuildPhase.PLANNING)

        # --- OUTER LOOP ITERATION 2 ---
        plan_iter2 = loop.start_plan(
            objectives=["Scrape tax liens with Cloudflare Turnstile bypass", "Daily 8 AM sync to Google Sheets"],
            acceptance_criteria=["lien_id_present", "amount_valid", "turnstile_solved", "sheets_delivered"],
            llm_engine=engine,
        )
        self.assertEqual(loop.iteration, 2)
        loop.start_team_build(plan_iter2)

        summary2 = loop.run_inner_swarm_build(
            target_url="https://county.gov/liens",
            selected_fields=["lien_id", "amount", "owner"],
            llm_engine=engine,
        )
        self.assertTrue(summary2["is_complete"])

        # Outside QA independently validates and approves
        outside_qa_pass_2 = loop.submit_qa(score=99.0, feedback=["All PM acceptance criteria and 8 AM delivery requirements met."])
        self.assertTrue(outside_qa_pass_2)
        self.assertEqual(loop.phase, BuildPhase.ESCROW_READY)
        self.assertEqual(len(loop.history), 7)


if __name__ == "__main__":
    unittest.main()