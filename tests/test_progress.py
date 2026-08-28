import unittest

from agents.build_loop import TeamRole
from agents.progress import ProgressFeed, ProgressStatus


class ProgressFeedTests(unittest.TestCase):
    def test_team_snapshot_is_ordered_and_customer_safe(self):
        feed = ProgressFeed()
        feed.publish_team_status(ProgressStatus.ACTIVE)
        snapshot = feed.public_snapshot()

        self.assertEqual(len(snapshot), 4)
        self.assertEqual(snapshot[0]["sequence"], 1)
        self.assertEqual(snapshot[0]["role"], TeamRole.NETWORK_ENGINEER.value)
        self.assertEqual(snapshot[0]["status"], "ACTIVE")
        self.assertNotIn("prompt", snapshot[0])
        self.assertNotIn("secret", snapshot[0])

    def test_blocked_event_has_safe_message(self):
        feed = ProgressFeed()
        event = feed.publish("qa_gatekeeper", ProgressStatus.BLOCKED, "Review required")

        self.assertEqual(event.status, ProgressStatus.BLOCKED)
        self.assertEqual(feed.public_snapshot()[0]["message"], "Review required")

    def test_empty_events_are_rejected(self):
        with self.assertRaises(ValueError):
            ProgressFeed().publish("", ProgressStatus.ACTIVE, "working")


if __name__ == "__main__":
    unittest.main()