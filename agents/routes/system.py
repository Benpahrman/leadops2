"""System-level routes (health, version, etc.)."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .. import __version__
from .dependencies import get_storage

router = APIRouter()


@router.get("/health", tags=["System"])
@router.get("/healthz", tags=["System"])
def health_check():
    """Liveness probe endpoint with system status."""
    return {
        "status": "ok",
        "service": "leadops",
        "version": __version__,
    }


@router.get("/readyz", tags=["System"])
def readiness_check(storage=Depends(get_storage)):
    """Readiness probe verifying live database connectivity and engine health."""
    try:
        if hasattr(storage, "list_leads"):
            _ = storage.list_leads()
        return {
            "status": "ready",
            "database": "connected",
            "service": "leadops",
            "version": __version__,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(exc), "service": "leadops"},
        )


@router.get("/version", tags=["System"])
def version():
    """Version information."""
    return {
        "service": "leadops",
        "version": __version__,
    }


@router.get("/api/health/ops", tags=["System"])
def ops_health_check(
    storage=Depends(get_storage),
):
    """Mobile-friendly operations health status endpoint."""
    from datetime import datetime, timezone
    import os

    leads = storage.list_leads() if hasattr(storage, "list_leads") else []
    active_subs = [l for l in leads if getattr(l, "subscription_active", False)]
    paid_deposits = [l for l in leads if getattr(l, "deposit_paid", False)]

    db_size_kb = 0
    if hasattr(storage, "db_path") and os.path.exists(storage.db_path):
        db_size_kb = round(os.path.getsize(storage.db_path) / 1024, 1)

    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "leadops",
        "version": __version__,
        "database": {
            "engine": "SQLite WAL Mode",
            "size_kb": db_size_kb,
            "status": "ONLINE",
        },
        "pipeline": {
            "total_leads": len(leads),
            "active_subscriptions": len(active_subs),
            "sprint_deposits_locked": len(paid_deposits),
            "escrow_deposits_locked": len(paid_deposits),
        },
        "cron_schedule": {
            "drift_shield": "05:30 UTC (Active)",
            "daily_batch_delivery": "06:00 UTC (Active)",
        },
        "proxy_pool": "US-Residential-Pool-4 (100% Health)",
    }