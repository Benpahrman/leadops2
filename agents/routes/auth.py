import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import ClerkUser, get_current_user
from .dependencies import get_clerk_auth, get_storage

logger = logging.getLogger("api.auth_claim")

router = APIRouter()

class ClaimAccountRequest(BaseModel):
    user_id: str
    lead_id: str
    email: str

@router.post("/api/auth/claim", tags=["Auth"])
def claim_account(
    req: ClaimAccountRequest,
    user: ClerkUser = Depends(get_current_user),
    clerk_auth=Depends(get_clerk_auth),
    storage_backend=Depends(get_storage),
):
    # Validate that the user is claiming their own account, or is a global admin
    if not user.is_admin:
        if user.user_id != req.user_id or user.email.lower().strip() != req.email.lower().strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot claim a sandbox account for another user."
            )
    res = clerk_auth.claim_sandbox_account(req.user_id, req.lead_id, req.email)

    lead = storage_backend.get_lead(req.lead_id)
    if lead:
        if not lead.claimed_by:
            lead.claimed_by = req.email.lower().strip()
            storage_backend.save_lead(lead)

    return {"ok": True, "account": res}
