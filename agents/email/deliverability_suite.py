"""Backward-compatible facade for deliverability suite classes and functions.

The implementation lives in agents/email/deliverability_pkg/.
"""

from agents.email.deliverability_pkg import (
    DnsAuthVector,
    RblBlacklistVector,
    ContentSpamVector,
    ProviderPlacementVector,
    ComprehensiveDeliverabilityReport,
    DnsMatrixAuditor,
    RblBlacklistScanner,
    ContentSpamAuditor,
    MultiProviderPlacementProbe,
    DeliverabilitySuite,
    get_deliverability_suite,
)

__all__ = [
    "DnsAuthVector",
    "RblBlacklistVector",
    "ContentSpamVector",
    "ProviderPlacementVector",
    "ComprehensiveDeliverabilityReport",
    "DnsMatrixAuditor",
    "RblBlacklistScanner",
    "ContentSpamAuditor",
    "MultiProviderPlacementProbe",
    "DeliverabilitySuite",
    "get_deliverability_suite",
]
