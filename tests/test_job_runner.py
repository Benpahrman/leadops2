import unittest

from agents.build_loop import BuildLoop, TeamRole
from agents.job_runner import JobStatus, LocalBuildRunner
from agents.progress import ProgressStatus


class JobRunnerTests(unittest.TestCase):
    def setUp(self):
        loop = BuildLoop()
        self.plan = loop.start_plan(["build feed"], ["rows validate"])

    def test_runner_executes_all_specialists_and_returns_qa_manifest(self):
        runner = LocalBuildRunner({
            role: lambda plan, role=role: f"{role.value} evidence"
            for role in TeamRole
        })
        manifest = runner.run(self.plan)

        self.assertIsNotNone(manifest)
        self.assertTrue(manifest.qa_handoff()["ready_for_qa"])
        self.assertTrue(all(job.status == JobStatus.SUCCEEDED for job in runner.jobs))
        statuses = [event["status"] for event in runner.progress.public_snapshot()]
        self.assertEqual(statuses.count(ProgressStatus.ACTIVE.value), 4)
        self.assertEqual(statuses.count(ProgressStatus.COMPLETE.value), 4)

    def test_failed_specialist_blocks_qa_handoff(self):
        def fail(plan):
            raise ValueError("DOM mapping failed")

        handlers = {
            role: (fail if role == TeamRole.FRONTEND_DOM_SPECIALIST else lambda plan: "evidence")
            for role in TeamRole
        }
        runner = LocalBuildRunner(handlers)

        self.assertIsNone(runner.run(self.plan))
        failed = next(job for job in runner.jobs if job.role == TeamRole.FRONTEND_DOM_SPECIALIST)
        self.assertEqual(failed.status, JobStatus.FAILED)
        self.assertEqual(failed.error, "DOM mapping failed")
        blocked = runner.progress.public_snapshot()[-1]
        self.assertEqual(blocked["status"], ProgressStatus.BLOCKED.value)
        self.assertEqual(blocked["role"], TeamRole.FRONTEND_DOM_SPECIALIST.value)

    def test_missing_handler_blocks_qa_handoff(self):
        runner = LocalBuildRunner({TeamRole.NETWORK_ENGINEER: lambda plan: "evidence"})

        self.assertIsNone(runner.run(self.plan))
        self.assertEqual(runner.jobs[1].status, JobStatus.FAILED)


if __name__ == "__main__":
    unittest.main()