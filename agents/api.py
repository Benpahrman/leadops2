"""LeadOps API application factory."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin_ops import AdminMissionControlService
from .auth import ClerkAuthService
from .dashboard import CustomerDashboardService
from .llm_client import LLMAgentEngine
from .logging_config import get_logger
from .middleware import EndpointRateLimiter
from .portal import PortalService
from .scout_pipeline import ScoutPortalPipeline
from .storage import SqliteStorageBackend, StorageBackend

from .routes import portal, dashboard, auth, admin, scout, payments, system, websocket
from .startup import bootstrap_demo_lead

logger = get_logger("api")


def create_app(
    storage: StorageBackend | None = None,
    portal_svc: PortalService | None = None,
    dashboard_svc: CustomerDashboardService | None = None,
    admin_ops: AdminMissionControlService | None = None,
    api_token: str | None = None,
) -> FastAPI:
    """Create configured FastAPI app with security middleware and routes."""
    app = FastAPI(title="LeadOps Customer Portal & Integration API", version="1.0.0")

    # Security CORS — restrict to known origins (override with LEADOPS_CORS_ORIGINS comma-separated list)
    env = os.environ.get("ENV", "production").lower()
    cors_origins_raw = os.environ.get("LEADOPS_CORS_ORIGINS")
    if not cors_origins_raw:
        if env == "production":
            raise ValueError("LEADOPS_CORS_ORIGINS must be set in production")
        cors_origins_raw = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
    
    # SECURITY: Prevent credential theft via CORS wildcard + allow_credentials
    if "*" in cors_origins:
        raise ValueError("LEADOPS_CORS_ORIGINS cannot contain wildcard '*' with allow_credentials=True")
    if not cors_origins:
        raise ValueError("LEADOPS_CORS_ORIGINS must contain at least one origin")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Per-endpoint rate limiting
    app.add_middleware(EndpointRateLimiter)

    # Initialize services
    storage_backend = storage or SqliteStorageBackend()
    portal_service = portal_svc or PortalService(storage=storage_backend)
    dashboard_service = dashboard_svc or CustomerDashboardService(storage=storage_backend)
    admin_service = admin_ops or AdminMissionControlService(storage=storage_backend)
    clerk_auth = ClerkAuthService()
    scout_pipeline = ScoutPortalPipeline(portal_service)
    configured_token = api_token or os.environ.get("LEADOPS_API_TOKEN")
    if not configured_token:
        raise ValueError("LEADOPS_API_TOKEN must be set — internal scout/webhook endpoints require authentication")
    llm_engine = LLMAgentEngine()

    # Attach services to app.state so routes can access them
    app.state.storage_backend = storage_backend
    app.state.portal_service = portal_service
    app.state.dashboard_service = dashboard_service
    app.state.admin_service = admin_service
    app.state.clerk_auth = clerk_auth
    app.state.scout_pipeline = scout_pipeline
    app.state.configured_token = configured_token
    app.state.llm_engine = llm_engine

    # Bootstrap default demo lead
    bootstrap_demo_lead(storage_backend, portal_service)

    # Register decoupled routes
    app.include_router(portal.router)
    app.include_router(dashboard.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(scout.router)
    app.include_router(payments.router)
    app.include_router(system.router)
    app.include_router(websocket.router)

    return app

# Module-level app removed — use uvicorn factory pattern:
# uvicorn agents.api:create_app --factory