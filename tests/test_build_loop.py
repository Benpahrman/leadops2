import unittest

from agents.build_loop import BuildLoop, BuildPhase, DEFAULT_TEAM_ROLES, TeamRole


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


if __name__ == "__main__":
    unittest.main()