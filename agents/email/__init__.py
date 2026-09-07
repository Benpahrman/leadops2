"""Native Email Subsystem for LeadOps.

Provides Gmail SMTP/IMAP transport, deliverability & bounce verification,
multi-week warmup throttling (20-25 -> 50 -> 75 -> 100/day), Cloudflare-routed
inbound watcher, and specialized AI agents for prospect verification, voice review,
and autonomous replies.
"""

from .config import EmailSettings
from .client import EmailClient
from .verifier import DeliverabilityVerifier, DeliverabilityStatus, VerificationResult
from .warmup import WarmupManager, WarmupTier
from .inbound_watcher import InboundEmailWatcher
from .quality_gate import OutreachQualityGatekeeper, QualityGateResult

__all__ = [
    "EmailSettings",
    "EmailClient",
    "DeliverabilityVerifier",
    "DeliverabilityStatus",
    "VerificationResult",
    "WarmupManager",
    "WarmupTier",
    "InboundEmailWatcher",
    "OutreachQualityGatekeeper",
    "QualityGateResult",
]
