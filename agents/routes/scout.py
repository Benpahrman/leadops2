import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .dependencies import get_scout_pipeline, verify_internal_token

logger = logging.getLogger("api.scout")

router = APIRouter()

class ScoutCandidateRequest(BaseModel):
    company_name: str
    lead_id: str
    evidence: list[dict[str, Any]]
    source_url: str
    sample_rows: list[dict[str, Any]]
    research: dict[str, Any]
    tier_key: str = "weekly"

@router.post("/api/scout/candidate", tags=["Scout Ingestion"])
def publish_scout_candidate(
    req: ScoutCandidateRequest,
    _=Depends(verify_internal_token),
    scout_pipe=Depends(get_scout_pipeline),
):
    try:
        candidate = scout_pipe.publish_candidate(
            company_name=req.company_name,
            lead_id=req.lead_id,
            evidence=req.evidence,
            source_url=req.source_url,
            sample_rows=req.sample_rows,
            research=req.research,
            tier_key=req.tier_key,
        )
        return {
            "ok": True,
            "lead_id": candidate.lead_id,
            "slug": candidate.slug,
            "portal_url": f"/p/{candidate.slug}",
            "intake": {
                "slug": candidate.intake.slug,
                "assumptions": [a.__dict__ for a in candidate.intake.assumptions],
            },
        }
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error publishing scout candidate: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to publish candidate: {str(e)}")
