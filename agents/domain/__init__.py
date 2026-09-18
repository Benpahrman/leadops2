"""
agents.domain
~~~~~~~~~~~~~

Core domain models, lifecycle state machines, and business rules for LeadOps.
Conforms to ADR-0002.
"""

from .pricing import Tier, TIERS, BUYOUT, TIER_ALIASES
from .lead import (
    State,
    SequenceState,
    PaymentEvent,
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    Lead,
)
from .events import ProgressStatus, ProgressEvent, ProgressFeed
from .artifacts import BuildArtifact, ArtifactManifest

__all__ = [
    "Tier",
    "TIERS",
    "BUYOUT",
    "TIER_ALIASES",
    "State",
    "SequenceState",
    "PaymentEvent",
    "ALLOWED_TRANSITIONS",
    "InvalidTransition",
    "Lead",
    "ProgressStatus",
    "ProgressEvent",
    "ProgressFeed",
    "BuildArtifact",
    "ArtifactManifest",
]
