"""
agents.outreach
~~~~~~~~~~~~~~~

Autonomous outbound lead engagement, timing, and playbooks:
- scheduler: Grace period auto-outreach scheduler & anti-spam jitter engine
- playbooks: Strategic campaign blueprints & copy templates
- office_hours: Business hours and delivery window calculators
"""

from .scheduler import AutoOutreachScheduler
from .playbooks import (
    format_county_filing_pitch,
    format_state_bar_pitch,
    format_sos_new_business_pitch,
    format_linkedin_connection_note,
    format_referral_amplification_ask,
)
from .office_hours import is_office_hours

__all__ = [
    "AutoOutreachScheduler",
    "format_county_filing_pitch",
    "format_state_bar_pitch",
    "format_sos_new_business_pitch",
    "format_linkedin_connection_note",
    "format_referral_amplification_ask",
    "is_office_hours",
]
