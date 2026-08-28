"""System-level routes (health, version, etc.)."""

from fastapi import APIRouter, Depends

from ..admin_ops import AdminMissionControlService
from .dependencies import get_admin_service

router = APIRouter()


@router.get("/health", tags=["System"])
def health_check(admin_service=Depends(get_admin_service)):
    """Health check endpoint with system status."""
    return {
        "status": "ok",
        "service": "leadops",
        "version": "1.0.0",
        "emergency_stop_active": admin_service.governance.emergency_stop_active,
    }


@router.get("/version", tags=["System"])
def version():
    """Version information."""
    return {
        "service": "leadops",
        "version": "1.0.0",
    }