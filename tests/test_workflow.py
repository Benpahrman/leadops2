import unittest

from agents.build_loop import TeamRole
from agents.domain import Lead, State
from agents.workflow import ProjectWorkflow


class ProjectWorkflowTests(unittest.TestCase):
    def _workflow(self):
        lead = Lead("lead-workflow", "daily", state=State.SOW_GENERATED)
        workflow = ProjectWorkflow(lead)
        workflow.record_verified_deposit()
        return workflow

    def _handlers(self):
        return {role: lambda plan, role=role: f"{role.value} artifact" for role in TeamRole}

    def test_successful_iteration_reaches_escrow(self):
        workflow = self._workflow()
        result = workflow.run_build_iteration(
            ["build feed"],
            ["portal loads", "rows validate"],
            self._handlers(),
            [{"criterion": "portal loads", "passed": True}, {"criterion": "rows validate", "passed": True}],
        )

        self.assertTrue(result.escrow_ready)
        self.assertEqual(workflow.lead.state, State.ESCROW_PREVIEW)
        self.assertEqual(workflow.lead.qa_score, 100.0)
        self.assertEqual(workflow.lead.preview_rows, 25)

    def test_failed_qa_returns_feedback_and_stays_out_of_escrow(self):
        workflow = self._workflow()
        result = workflow.run_build_iteration(
            ["build feed"],
            ["portal loads", "rows validate"],
            self._handlers(),
            [{"criterion": "portal loads", "passed": True}, {"criterion": "rows validate", "passed": False}],
        )

        self.assertFalse(result.escrow_ready)
        self.assertEqual(workflow.lead.state, State.DEPOSIT_PAID)
        self.assertIn("rows validate", result.qa_feedback)

    def test_specialist_failure_blocks_qa(self):
        workflow = self._workflow()

        def fail(plan):
            raise ValueError("portal mapping failed")

        handlers = self._handlers()
        handlers[TeamRole.FRONTEND_DOM_SPECIALIST] = fail
        result = workflow.run_build_iteration(
            ["build feed"],
            ["portal loads"],
            handlers,
            [{"criterion": "portal loads", "passed": True}],
        )

        self.assertIsNone(result.manifest)
        self.assertEqual(workflow.lead.state, State.DEPOSIT_PAID)
        self.assertIn("portal mapping failed", result.qa_feedback)

    def test_anti_bot_blocked_escalates_to_review(self):
        workflow = self._workflow()

        def blocked_by_waf(plan):
            raise ValueError("Target source blocked access via Cloudflare CAPTCHA")

        handlers = self._handlers()
        handlers[TeamRole.NETWORK_ENGINEER] = blocked_by_waf
        result = workflow.run_build_iteration(
            ["build feed"],
            ["portal loads"],
            handlers,
            [{"criterion": "portal loads", "passed": True}],
        )

        self.assertIsNone(result.manifest)
        self.assertEqual(workflow.lead.state, State.BLOCKED_NEEDS_REVIEW)
        self.assertIn("Cloudflare CAPTCHA", result.qa_feedback[0])


if __name__ == "__main__":
    unittest.main()