from fastapi import Request, Depends
from ..storage import StorageBackend
from ..portal import PortalService
from ..dashboard import CustomerDashboardService
from ..admin_ops import AdminMissionControlService
from ..auth import ClerkAuthService
from ..scout_pipeline import ScoutPortalPipeline
from ..llm_client import LLMAgentEngine

from fastapi import HTTPException, status
from ..auth import ClerkUser, get_current_user

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

def check_dashboard_access(lead_id_or_slug: str, user: ClerkUser, storage_backend: StorageBackend):
    if user.is_admin:
        return
    
    # Find lead by lead_id or slug
    lead = storage_backend.get_lead(lead_id_or_slug)
    if not lead:
        # Try to get lead by slug
        sandboxes = storage_backend.list_sandboxes()
        for sb in sandboxes:
            if sb.slug == lead_id_or_slug:
                lead = sb.lead
                break
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    
    # Check permissions
    if user.lead_id and user.lead_id == lead.lead_id:
        return
    
    # Fallback to email match
    clean_email = user.email.lower().strip()
    lead_email = getattr(lead, "contact_email", "").lower().strip() if getattr(lead, "contact_email", "") else ""
    claimed_by = getattr(lead, "claimed_by", "").lower().strip() if getattr(lead, "claimed_by", "") else ""
    if clean_email in {lead_email, claimed_by} and clean_email:
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: You do not have permission to access this dashboard."
    )

from fastapi import Header
from ..auth import ClerkUser

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


def verify_csrf_token(request: Request, user: ClerkUser = Depends(get_current_user), x_csrf_token: str = Header(None, alias="X-CSRF-Token")) -> bool:
    """Verify CSRF token for state-changing operations.
    
    The CSRF token is derived from the user's session ID (sub claim) to prevent
    cross-site request forgery attacks. The frontend should include this header
    with all POST/PUT/DELETE requests.
    """
    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required (X-CSRF-Token header)"
        )
    
    # Simple token validation: token should contain the user's sub claim
    # In production, use a proper HMAC-based CSRF token
    expected_prefix = f"csrf-{user.user_id}"
    if not x_csrf_token.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )
    return True


