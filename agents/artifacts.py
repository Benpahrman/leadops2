"""Local build artifact manifest for the Builder Team to QA handoff."""

import hashlib
from dataclasses import dataclass, field

from .build_loop import TeamRole, DEFAULT_TEAM_ROLES


@dataclass(frozen=True)
class BuildArtifact:
    artifact_id: str
    role: TeamRole
    kind: str
    content: str
    checksum: str


@dataclass
class ArtifactManifest:
    iteration: int
    artifacts: list[BuildArtifact] = field(default_factory=list)
    required_roles: set[TeamRole] | None = None

    def add(
        self,
        artifact_id: str,
        role: TeamRole,
        kind: str,
        content: str,
    ) -> BuildArtifact:
        if not artifact_id.strip() or not kind.strip() or not content.strip():
            raise ValueError("artifact_id, kind, and content are required")
        if any(artifact.artifact_id == artifact_id for artifact in self.artifacts):
            raise ValueError(f"Duplicate artifact id: {artifact_id}")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        artifact = BuildArtifact(artifact_id, role, kind, content, checksum)
        self.artifacts.append(artifact)
        return artifact

    def qa_handoff(self) -> dict[str, object]:
        required = self.required_roles if self.required_roles is not None else set(DEFAULT_TEAM_ROLES)
        provided_roles = {artifact.role for artifact in self.artifacts}
        missing_roles = sorted(role.value for role in required - provided_roles)
        return {
            "iteration": self.iteration,
            "artifacts": [
                {
                    "artifact_id": artifact.artifact_id,
                    "role": artifact.role.value,
                    "kind": artifact.kind,
                    "checksum": artifact.checksum,
                }
                for artifact in self.artifacts
            ],
            "missing_roles": missing_roles,
            "ready_for_qa": not missing_roles,
            "contains_content": False,
        }