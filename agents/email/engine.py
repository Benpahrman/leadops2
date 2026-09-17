"""Backward-compatible facade for email engine classes.

The implementation lives in agents/email/engine_pkg/.
"""

from agents.email.engine_pkg import (
    RampStage,
    RAMP_SCHEDULE,
    WarmupAgent,
    SpintaxGenerator,
    EmailEngineQueue,
    PeerInboxWarmupWatcher,
    EmailEngine,
    DEFAULT_DB_PATH,
    DEFAULT_PRIMARY_DOMAIN,
    DEFAULT_SECONDARY_DOMAIN,
    DEFAULT_SENDER_IDENTITY,
    DEFAULT_SENDER_MAILBOXES,
)

__all__ = [
    "RampStage",
    "RAMP_SCHEDULE",
    "WarmupAgent",
    "SpintaxGenerator",
    "EmailEngineQueue",
    "PeerInboxWarmupWatcher",
    "EmailEngine",
    "DEFAULT_DB_PATH",
    "DEFAULT_PRIMARY_DOMAIN",
    "DEFAULT_SECONDARY_DOMAIN",
    "DEFAULT_SENDER_IDENTITY",
    "DEFAULT_SENDER_MAILBOXES",
]
