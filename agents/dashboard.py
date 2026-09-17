"""Backward-compatible facade for CustomerDashboardService and DestinationConfig.

The implementation lives in agents/dashboard_pkg/.
"""

from agents.dashboard_pkg import CustomerDashboardService, DestinationConfig

__all__ = ["CustomerDashboardService", "DestinationConfig"]
