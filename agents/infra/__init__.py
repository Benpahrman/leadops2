"""
agents.infra
~~~~~~~~~~~~

Core platform infrastructure, security, and observability:
- auth: Clerk authentication adapter, token verification, RBAC
- observability: Telemetry, metrics, OpenTelemetry spans, audit vault
- logging: Centralized production logging
- middleware: Rate limiting & HTTP middleware
- websocket: WebSocket connection manager for live progress
"""

from .auth import ClerkAuthService, ClerkUser, require_admin, get_current_user
from .observability import SystemTelemetryCollector, TelemetryEvent, telemetry_collector
from .logging import configure_logging, get_logger
from .middleware import RateLimitMiddleware
from .websocket import ProgressManager, progress_manager

__all__ = [
    "ClerkAuthService",
    "ClerkUser",
    "require_admin",
    "get_current_user",
    "SystemTelemetryCollector",
    "TelemetryEvent",
    "telemetry_collector",
    "configure_logging",
    "get_logger",
    "RateLimitMiddleware",
    "ProgressManager",
    "progress_manager",
]
