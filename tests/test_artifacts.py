import unittest

from agents.artifacts import ArtifactManifest
from agents.build_loop import TeamRole


class ArtifactManifestTests(unittest.TestCase):
    def test_manifest_hides_content_and_is_ready_when_all_roles_submit(self):
        manifest = ArtifactManifest(iteration=1)
        for role in TeamRole:
            manifest.add(f"{role.value.lower()}-1", role, "report", f"{role.value} complete")

        handoff = manifest.qa_handoff()
        self.assertTrue(handoff["ready_for_qa"])
        self.assertFalse(handoff["contains_content"])
        self.assertEqual(len(handoff["artifacts"]), 4)
        self.assertIn("checksum", handoff["artifacts"][0])

    def test_missing_role_blocks_qa(self):
        manifest = ArtifactManifest(iteration=2)
        manifest.add("network-2", TeamRole.NETWORK_ENGINEER, "report", "access verified")

        handoff = manifest.qa_handoff()
        self.assertFalse(handoff["ready_for_qa"])
        self.assertIn(TeamRole.JUNIOR_DEVELOPER.value, handoff["missing_roles"])

    def test_duplicate_artifact_ids_are_rejected(self):
        manifest = ArtifactManifest(iteration=1)
        manifest.add("same-id", TeamRole.SYSTEMS_ARCHITECT, "report", "first")
        with self.assertRaises(ValueError):
            manifest.add("same-id", TeamRole.SYSTEMS_ARCHITECT, "report", "second")


if __name__ == "__main__":
    unittest.main()