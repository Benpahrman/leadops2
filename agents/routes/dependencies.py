import hashlib
import hmac
import os

from fastapi import Depends, Header, HTTPException, Request, status

from ..admin_ops import AdminMissionControlService
from ..auth import ClerkAuthService, ClerkUser, get_current_user
from ..dashboard import CustomerDashboardService
from ..llm_client import LLMAgentEngine
from ..portal import PortalService
from ..scout_pipeline import ScoutPortalPipeline
from ..storage import StorageBackend


def get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage_backend

def get_portal_service(request: Request) -> PortalService:
    return request.app.state.portal_service

def get_dashboard_service(request: Request) -> CustomerDashboardService:
    return request.app.state.dashboard_service

def get_admin_service(request: Request) -> AdminMissionControlService:
    return request.app.state.admin_service

def get_clerk_auth(request: Request) -> ClerkAuthService:
    return request.app.state.clerk_auth

def get_scout_pipeline(request: Request) -> ScoutPortalPipeline:
    return request.app.state.scout_pipeline

def get_configured_token(request: Request) -> str:
    return request.app.state.configured_token

def get_llm_engine(request: Request) -> LLMAgentEngine:
    return request.app.state.llm_engine

def get_inbound_watcher(request: Request):
    return getattr(request.app.state, "inbound_email_watcher", None)

def check_dashboard_access(lead_id_or_slug: str, user: ClerkUser | None, storage_backend) -> None:
    if user and (
        getattr(user, "is_admin", False)
        or getattr(user, "role", "") == "admin"
        or ClerkAuthService().is_admin_email(getattr(user, "email", ""))
    ):
        return

    env = os.environ.get("ENV", "development").lower()
    is_dev = (
        env in {"development", "dev", "local"}
        or os.environ.get("ALLOW_DEV_ADMIN", "true").lower() == "true"
    ) and os.environ.get("DISABLE_TEST_FALLBACK") != "true"

    # Allow preview access for demo sandboxes, primary-feed anchor, or dev mode
    is_demo = (
        lead_id_or_slug in {"primary-feed", "demo_lead", "prospect-intelligence-feed"}
        or lead_id_or_slug.startswith("demo-")
        or "demo" in lead_id_or_slug
    )
    if user is None:
        if is_demo or is_dev:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is required"
        )

    # Find lead by lead_id or slug
    lead = storage_backend.get_lead(lead_id_or_slug)
    if not lead:
        # Try to get lead by slug
        sandboxes = storage_backend.list_sandboxes()
        for sb in sandboxes:
            if sb.slug == lead_id_or_slug:
                lead = sb.lead
                break
    
    # If primary-feed or demo is requested but not in storage, allow default preview
    if not lead and is_demo:
        return

    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    
    # Check permissions
    user_lead_id = getattr(user, "lead_id", None)
    if user_lead_id:
        if (
            user_lead_id == lead.lead_id
            or f"lead-{user_lead_id}" == lead.lead_id
            or user_lead_id == getattr(lead, "slug", "")
            or getattr(lead, "lead_id", "").endswith(user_lead_id)
        ):
            return
        # If user has a specific assigned lead and tries to access another private lead
        if not is_demo and not lead.lead_id.startswith("demo-"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this dashboard."
            )
    
    # Fallback to email match or auto-claim
    clean_email = user.email.lower().strip() if getattr(user, "email", None) else ""
    lead_email = getattr(lead, "contact_email", "").lower().strip() if getattr(lead, "contact_email", "") else ""
    claimed_by = getattr(lead, "claimed_by", "").lower().strip() if getattr(lead, "claimed_by", "") else ""
    
    if clean_email and clean_email in {lead_email, claimed_by}:
        return
    
    if not claimed_by and clean_email and not any(clean_email.endswith(d) for d in ("@customer.omnileadfeeder.tech", "@customer.leadops.app")):
        lead.claimed_by = clean_email
        storage_backend.save_lead(lead)
        return

    if is_demo or lead.lead_id.startswith("demo-") or is_dev:
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: You do not have permission to access this dashboard."
    )


def verify_internal_token(request: Request, authorization: str = Header(None)) -> bool:
    configured_token = request.app.state.configured_token
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal API token authentication is not configured on server"
        )
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != configured_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token")
    return True


def _csrf_secret(request: Request) -> bytes:
    """Get CSRF secret from Clerk secret key."""
    clerk_secret = os.environ.get("CLERK_SECRET_KEY", "dev-secret-change-in-production")
    return clerk_secret.encode()[:32]


def generate_csrf_token(request: Request, user_id: str) -> str:
    """Generate HMAC-based CSRF token."""
    return hmac.new(
        _csrf_secret(request),
        user_id.encode(),
        hashlib.sha256
    ).hexdigest()[:32]


def verify_csrf_token(request: Request, user: ClerkUser = Depends(get_current_user), x_csrf_token: str = Header(None, alias="X-CSRF-Token")) -> bool:
    """Verify HMAC-based CSRF token for state-changing operations."""
    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required (X-CSRF-Token header)"
        )
    
    expected = generate_csrf_token(request, user.user_id)
    if not hmac.compare_digest(x_csrf_token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )
    return True



