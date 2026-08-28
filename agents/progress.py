"""Customer-safe progress events for the portal build view."""

from dataclasses import dataclass, field
from enum import Enum

from .build_loop import TeamRole


class ProgressStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ProgressEvent:
    sequence: int
    role: str
    status: ProgressStatus
    public_message: str


@dataclass
class ProgressFeed:
    events: list[ProgressEvent] = field(default_factory=list)

    def publish(self, role: str, status: ProgressStatus, public_message: str) -> ProgressEvent:
        if not role.strip() or not public_message.strip():
            raise ValueError("role and public_message are required")
        event = ProgressEvent(len(self.events) + 1, role, status, public_message)
        self.events.append(event)
        return event

    def publish_team_status(self, status: ProgressStatus) -> None:
        for role in TeamRole:
            self.publish(role.value, status, self._message(role, status))

    def public_snapshot(self) -> list[dict[str, object]]:
        return [
            {
                "sequence": event.sequence,
                "role": event.role,
                "status": event.status.value,
                "message": event.public_message,
            }
            for event in self.events
        ]

    @staticmethod
    def _message(role: TeamRole, status: ProgressStatus) -> str:
        labels = {
            TeamRole.NETWORK_ENGINEER: "Checking permitted source connectivity",
            TeamRole.FRONTEND_DOM_SPECIALIST: "Mapping the source portal structure",
            TeamRole.SYSTEMS_ARCHITECT: "Validating data and runtime contracts",
            TeamRole.JUNIOR_DEVELOPER: "Implementing the approved feed tasks",
        }
        if status == ProgressStatus.COMPLETE:
            return "Work completed and sent for independent review"
        if status == ProgressStatus.BLOCKED:
            return "Work needs attention before independent review"
        return labels[role]