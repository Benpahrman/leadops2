"""Backward-compatible facade for admin pipeline routes.

The implementation lives in agents/routes/admin/pipeline_pkg/.
"""

from agents.routes.admin.pipeline_pkg import router

__all__ = ["router"]
