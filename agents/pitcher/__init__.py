"""Pitcher (Alex) Agent Package — Outbound email dispatch, Zero-Link touch, same-day freshness gates, and lifecycle email automation."""

from .models import (
    PitchMessage,
    EmailTemplate,
    LIFECYCLE_EMAIL_TEMPLATES,
    SendPulseSettings,
    SendPulseClient,
)
from .persona import (
    _safe_str,
    generate_natural_subject,
    get_public_base_url,
    render_executive_email_html,
    render_sub_60_word_pitch,
)
from .lifecycle import (
    render_escrow_ready_email,
    render_deposit_confirmation_email,
    send_deposit_confirmation_email,
    get_ab_variant,
    send_ab_test_email,
    send_escrow_ready_notification,
    LifecycleEmailGenerator,
    send_lifecycle_email,
)
from .freshness import (
    is_record_stale,
    ensure_fresh_records_for_lead,
)
from .service import (
    PitcherService,
)

__all__ = [
    # Models & Aliases
    "PitchMessage",
    "EmailTemplate",
    "LIFECYCLE_EMAIL_TEMPLATES",
    "SendPulseSettings",
    "SendPulseClient",
    # Persona & Copy Generation
    "_safe_str",
    "generate_natural_subject",
    "get_public_base_url",
    "render_executive_email_html",
    "render_sub_60_word_pitch",
    # Freshness Gate
    "is_record_stale",
    "ensure_fresh_records_for_lead",
    # Pitcher Service
    "PitcherService",
    # Lifecycle & Milestones
    "render_escrow_ready_email",
    "render_deposit_confirmation_email",
    "send_deposit_confirmation_email",
    "get_ab_variant",
    "send_ab_test_email",
    "send_escrow_ready_notification",
    "LifecycleEmailGenerator",
    "send_lifecycle_email",
]
