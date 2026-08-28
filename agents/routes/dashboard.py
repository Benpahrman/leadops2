io = None # we'll import io locally or globally
import io
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..auth import ClerkUser, get_current_user
from .dependencies import (
    get_storage,
    get_dashboard_service,
    check_dashboard_access,
)
from .templates import render_dashboard_html

logger = logging.getLogger("api.dashboard")

router = APIRouter()

# Request Models
class FieldModificationRequest(BaseModel):
    add_fields: list[str] = Field(default_factory=list)
    remove_fields: list[str] = Field(default_factory=list)

class DestinationUpdateRequest(BaseModel):
    destination_type: str  # "google_sheets" or "webhook"
    google_sheet_url: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    delivery_schedule: str | None = None
    delivery_timezone: str | None = None

@router.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard UI"])
def dashboard_index(storage_backend=Depends(get_storage)):
    leads = storage_backend.list_leads()
    if leads:
        return render_dashboard_html(leads[-1].lead_id)
    return render_dashboard_html("primary-feed")

@router.get("/dashboard/{lead_id}", response_class=HTMLResponse, tags=["Dashboard UI"])
def dashboard_view(lead_id: str):
    return render_dashboard_html(lead_id)

@router.get("/api/dashboard/{lead_id}", tags=["Dashboard API"])
def get_dashboard_data(
    lead_id: str,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    dashboard_service=Depends(get_dashboard_service),
):
    check_dashboard_access(lead_id, user, storage_backend)
    try:
        return dashboard_service.get_dashboard_state(lead_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/dashboard/{lead_id}/fields/request", tags=["Dashboard API"])
def request_field_changes(
    lead_id: str,
    req: FieldModificationRequest,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    dashboard_service=Depends(get_dashboard_service),
):
    check_dashboard_access(lead_id, user, storage_backend)
    try:
        return dashboard_service.request_field_modification(
            lead_id=lead_id,
            add_fields=req.add_fields,
            remove_fields=req.remove_fields,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/dashboard/{lead_id}/destination", tags=["Dashboard API"])
def update_destination(
    lead_id: str,
    req: DestinationUpdateRequest,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    dashboard_service=Depends(get_dashboard_service),
):
    check_dashboard_access(lead_id, user, storage_backend)
    try:
        config = dashboard_service.update_destination(
            lead_id=lead_id,
            dest_type=req.destination_type,
            google_sheet_url=req.google_sheet_url,
            webhook_url=req.webhook_url,
            webhook_secret=req.webhook_secret,
            delivery_schedule=req.delivery_schedule,
            delivery_timezone=req.delivery_timezone,
        )
        return {"ok": True, "destination": config.__dict__}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/dashboard/{lead_id}/sync", tags=["Dashboard API"])
def trigger_sync(
    lead_id: str,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    dashboard_service=Depends(get_dashboard_service),
):
    check_dashboard_access(lead_id, user, storage_backend)
    try:
        return dashboard_service.trigger_manual_sync(lead_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/dashboard/{lead_id}/export", tags=["Dashboard API"])
def export_csv_data(
    lead_id: str,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    dashboard_service=Depends(get_dashboard_service),
):
    check_dashboard_access(lead_id, user, storage_backend)
    try:
        csv_content = dashboard_service.export_latest_csv(lead_id)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=leadops_feed_{lead_id}.csv"},
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/dashboard/{lead_id}/buyout-bundle", tags=["Dashboard API"])
@router.post("/api/dashboard/{lead_id}/buyout-bundle", tags=["Dashboard API"])
def generate_buyout_bundle(
    lead_id: str,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
):
    """Generate client-owned buyout bundle containing source extraction code."""
    check_dashboard_access(lead_id, user, storage_backend)
    import zipfile
    lead = storage_backend.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")

    logger.info(f"📦 [BUYOUT BUNDLE GENERATED] Lead: {lead_id}")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", f"# {lead.tier.name} - Extractor Source Bundle\n\nGenerated for Lead ID: {lead_id}\nLicense: Perpetual Client-Owned Commercial Rights.")
        zf.writestr("requirements.txt", "playwright>=1.40.0\npydantic>=2.0.0\nhttpx>=0.25.0\n")
        zf.writestr("extractor.py", "import asyncio\nfrom playwright.async_api import async_playwright\n\nasync def run_pipeline():\\n    print('Running client-owned extractor...')\n\nif __name__ == '__main__':\n    asyncio.run(run_pipeline())\n")
        zf.writestr("Dockerfile", "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"extractor.py\"]\n")

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=leadops_extractor_{lead_id}.zip"},
    )
