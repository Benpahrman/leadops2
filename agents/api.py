"""LeadOps API application factory."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .admin_ops import AdminMissionControlService
from .auth import ClerkAuthService
from .dashboard import CustomerDashboardService
from .llm_client import LLMAgentEngine
from .logging_config import get_logger
from .middleware import EndpointRateLimiter
from .portal import PortalService
from .scout_pipeline import ScoutPortalPipeline
from .scout_runner import ScoutAutomationSupervisor
from .storage import SqliteStorageBackend, StorageBackend, create_storage_backend
from .websocket import progress_manager

from .routes import portal, dashboard, auth, admin, scout, payments, system, websocket
from .startup import bootstrap_demo_lead

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifespan manager for clean startup and shutdown."""
    scout_supervisor = getattr(app.state, "scout_supervisor", None)
    if scout_supervisor:
        scout_supervisor.start()
    inbound_watcher = getattr(app.state, "inbound_email_watcher", None)
    if inbound_watcher and os.environ.get("INBOUND_WATCHER_ENABLED", "true").lower() == "true":
        inbound_watcher.start()

    # Startup Fleet Deliverability & TestMail Spam Assessment (non-blocking)
    if os.environ.get("DELIVERABILITY_AUDIT_ON_STARTUP", "true").lower() in ("true", "1", "yes") and not os.environ.get("PYTEST_CURRENT_TEST"):
        import threading
        storage = getattr(app.state, "storage", None)
        def _bg_startup_audit():
            try:
                import time
                time.sleep(4)
                from .email.deliverability_tester import DeliverabilityTester
                tester = DeliverabilityTester(storage_backend=storage)
                tester.run_fleet_audit(force=False)
            except Exception as e:
                logger.warning(f"Startup deliverability audit error: {e}")
        threading.Thread(target=_bg_startup_audit, daemon=True).start()

    yield
    if inbound_watcher:
        await inbound_watcher.stop()
    if scout_supervisor:
        await scout_supervisor.stop()
    # Gracefully close all active WebSockets on server shutdown
    try:
        await progress_manager.close_all()
    except Exception as e:
        logger.warning(f"WebSocket shutdown notice: {e}")



def create_app(
    storage: StorageBackend | None = None,
    portal_svc: PortalService | None = None,
    dashboard_svc: CustomerDashboardService | None = None,
    admin_ops: AdminMissionControlService | None = None,
    api_token: str | None = None,
) -> FastAPI:
    """Create configured FastAPI app with security middleware and routes."""
    env = os.environ.get("ENV", "development").lower()
    enable_docs = env != "production" or os.environ.get("ENABLE_DOCS", "false").lower() == "true"
    
    app = FastAPI(
        title="LeadOps Customer Portal & Integration API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
    )
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
    storage_backend = storage or create_storage_backend()
    portal_service = portal_svc or PortalService(storage=storage_backend)
    dashboard_service = dashboard_svc or CustomerDashboardService(storage=storage_backend)
    admin_service = admin_ops or AdminMissionControlService(storage=storage_backend)
    clerk_auth = ClerkAuthService()
    scout_pipeline = ScoutPortalPipeline(portal_service)
    configured_token = api_token or os.environ.get("LEADOPS_API_TOKEN")
    if not configured_token:
        raise ValueError("LEADOPS_API_TOKEN must be set — internal scout/webhook endpoints require authentication")
    llm_engine = LLMAgentEngine()
    def _clean_env_int(key: str, default: int) -> int:
        raw = os.environ.get(key)
        if raw is None:
            return default
        cleaned = str(raw).split("#")[0].strip().strip("\"'")
        try:
            return int(cleaned)
        except (ValueError, TypeError):
            return default

    fixed_scout_interval = _clean_env_int("SCOUT_INTERVAL_SECONDS", 0) if os.environ.get("SCOUT_INTERVAL_SECONDS") else None
    default_min_rest = fixed_scout_interval if fixed_scout_interval else _clean_env_int("SCOUT_MIN_REST_SECONDS", 3600)
    default_max_rest = fixed_scout_interval if fixed_scout_interval else _clean_env_int("SCOUT_MAX_REST_SECONDS", 7200)
    target_per_cycle = _clean_env_int("SCOUT_TARGET_PER_CYCLE", 1)

    scout_supervisor = ScoutAutomationSupervisor(
        storage=storage_backend,
        portal=portal_service,
        llm_engine=llm_engine,
        target_per_cycle=target_per_cycle,
        min_rest_seconds=default_min_rest,
        max_rest_seconds=default_max_rest,
        enabled=os.environ.get("SCOUT_AUTOMATION_ENABLED", "true").lower() == "true",
    )

    # Native Email Subsystem & Inbound Watcher
    from .email.config import EmailSettings
    from .email.client import EmailClient
    from .email.warmup import WarmupManager
    from .email.inbound_watcher import InboundEmailWatcher

    email_settings = EmailSettings.from_environment()
    email_client = EmailClient(settings=email_settings)
    warmup_manager = WarmupManager(settings=email_settings, storage_backend=storage_backend)
    inbound_email_watcher = InboundEmailWatcher(
        email_client=email_client,
        storage_backend=storage_backend,
        settings=email_settings,
    )

    # Attach services to app.state so routes can access them
    app.state.storage_backend = storage_backend
    app.state.portal_service = portal_service
    app.state.dashboard_service = dashboard_service
    app.state.admin_service = admin_service
    app.state.clerk_auth = clerk_auth
    app.state.scout_pipeline = scout_pipeline
    app.state.configured_token = configured_token
    app.state.llm_engine = llm_engine
    app.state.scout_supervisor = scout_supervisor
    app.state.email_settings = email_settings
    app.state.email_client = email_client
    app.state.warmup_manager = warmup_manager
    app.state.inbound_email_watcher = inbound_email_watcher

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

    # Mount compiled React SPA static assets (/assets/...)
    dist_assets_dir = Path(__file__).parent.parent / "frontend" / "dist" / "assets"
    if dist_assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_assets_dir)), name="react-assets")

    # Mount static assets (shared CSS, favicon, client scripts)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app

# Module-level app removed — use uvicorn factory pattern:
# uvicorn agents.api:create_app --factory