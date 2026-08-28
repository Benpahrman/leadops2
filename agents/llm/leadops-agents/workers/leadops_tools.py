"""Narrow tools exposed to the LeadOps LLM agents."""

from typing import Any
import re


def record_research_evidence(
    company_name: str,
    source_url: str,
    niche: str,
    jurisdiction: str,
    portal_name: str,
    portal_url: str,
    suggested_fields: list[str],
) -> dict[str, Any]:
    """Store a structured research result for a prospect."""
    if not company_name.strip() or not source_url.strip():
        return {"ok": False, "error": "company_name and source_url are required"}
    if not suggested_fields:
        return {"ok": False, "error": "at least one suggested field is required"}
    return {
        "ok": True,
        "company_name": company_name.strip(),
        "source_url": source_url.strip(),
        "assumptions": {
            "niche": niche.strip(),
            "jurisdiction": jurisdiction.strip(),
            "portal_name": portal_name.strip(),
            "portal_url": portal_url.strip(),
            "suggested_fields": list(dict.fromkeys(suggested_fields)),
        },
        "requires_customer_confirmation": True,
    }


def publish_sandbox_candidate(
    company_name: str,
    lead_id: str,
    source_url: str,
    sample_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare a read-only portal sandbox from permitted sample data."""
    if not company_name.strip() or not lead_id.strip() or not source_url.strip():
        return {"ok": False, "error": "company_name, lead_id, and source_url are required"}
    if not sample_rows or not all(isinstance(row, dict) and row for row in sample_rows):
        return {"ok": False, "error": "sample_rows must contain non-empty objects"}
    normalized = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    slug = f"{normalized or 'prospect'}-{lead_id.lower()}"
    return {
        "ok": True,
        "portal_path": f"/p/{slug}",
        "slug": slug,
        "source_url": source_url,
        "sample_rows": sample_rows,
        "read_only": True,
        "requires_customer_confirmation": True,
    }


def prepare_confirmation_intake(
    research: dict[str, Any],
    confidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Convert research into editable assumptions for the customer portal."""
    assumptions = research.get("assumptions")
    if not isinstance(assumptions, dict):
        return {"ok": False, "error": "research assumptions are required"}
    confidence = confidence or {}
    labels = {
        "niche": "Business type",
        "jurisdiction": "Primary jurisdiction",
        "portal_name": "Likely data portal",
        "portal_url": "Portal URL",
        "suggested_fields": "Suggested fields",
    }
    fields = [
        {
            "key": key,
            "label": label,
            "value": assumptions.get(key),
            "confidence": confidence.get(key, "medium"),
            "source": research.get("source_url", "Scout research"),
            "requires_confirmation": True,
        }
        for key, label in labels.items()
    ]
    return {
        "ok": True,
        "company_name": research.get("company_name"),
        "fields": fields,
        "primary_action": "confirm_assumptions",
        "optional_questions_deferred": True,
    }


def prepare_provisioning_plan(
    lead_id: str,
    lifecycle_state: str,
    provider: str = "azure",
    environment: str = "production",
) -> dict[str, Any]:
    """Prepare a paid-project plan without creating cloud resources or secrets."""
    if lifecycle_state != "DEPOSIT_PAID":
        return {"ok": False, "error": "verified deposit payment is required"}
    if provider not in {"azure", "digitalocean"}:
        return {"ok": False, "error": "provider must be azure or digitalocean"}
    if environment not in {"staging", "production"}:
        return {"ok": False, "error": "environment must be staging or production"}
    if provider == "digitalocean" and environment == "production":
        return {"ok": False, "error": "digitalocean production requires explicit review"}
    return {
        "ok": True,
        "lead_id": lead_id,
        "provider": provider,
        "environment": environment,
        "jobs": ["build", "qa", "delivery"],
        "required_secret_references": [
            "PAYPAL_CLIENT_ID",
            "PAYPAL_CLIENT_SECRET",
            "PAYPAL_WEBHOOK_ID",
        ],
        "cloud_resources_created": False,
        "approval_required": True,
    }


def create_build_plan(
    objectives: list[str],
    acceptance_criteria: list[str],
    iteration: int = 1,
) -> dict[str, Any]:
    """Create a testable build plan for the Dev Lead and Builder Team."""
    if not objectives or not acceptance_criteria:
        return {"ok": False, "error": "objectives and acceptance_criteria are required"}
    return {
        "ok": True,
        "iteration": iteration,
        "objectives": objectives,
        "acceptance_criteria": acceptance_criteria,
        "next_role": "dev_lead",
    }


def evaluate_qa_gate(score: float, feedback: list[str] | None = None) -> dict[str, Any]:
    """Apply the independent 95% QA gate and route failures back to planning."""
    if not 0 <= score <= 100:
        return {"ok": False, "error": "score must be between 0 and 100"}
    passed = score >= 95
    return {
        "ok": True,
        "score": score,
        "feedback": feedback or [],
        "gate": "passed" if passed else "failed",
        "next_phase": "escrow_ready" if passed else "replan",
        "next_role": "escrow" if passed else "planner",
    }


def evaluate_build_evidence(
    checks: list[dict[str, Any]],
    feedback: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate QA from criterion evidence and route failures to Planner."""
    if not checks:
        return {"ok": False, "error": "at least one acceptance check is required"}
    invalid = [check for check in checks if not isinstance(check.get("passed"), bool)]
    if invalid:
        return {"ok": False, "error": "every acceptance check needs a boolean passed value"}
    passed = sum(check["passed"] for check in checks)
    score = round((passed / len(checks)) * 100, 2)
    failed_checks = [check.get("criterion", "unnamed criterion") for check in checks if not check["passed"]]
    combined_feedback = list(feedback or []) + failed_checks
    gate = evaluate_qa_gate(score, combined_feedback)
    gate["checks"] = checks
    return gate


def assign_builder_team() -> dict[str, Any]:
    """Return fixed Builder Team ownership; QA is deliberately excluded."""
    return {
        "ok": True,
        "roles": {
            "network_engineer": "network_and_access",
            "frontend_dom_specialist": "portal_structure_and_dom_mapping",
            "systems_architect": "data_contracts_and_runtime_design",
            "junior_developer": "bounded_implementation_and_tests",
        },
        "qa_outside_team": True,
        "approval_required_before_execution": True,
    }


def create_team_work_items(
    objectives: list[str],
    acceptance_criteria: list[str],
) -> dict[str, Any]:
    """Create role-owned work items for Dev Lead coordination."""
    if not objectives or not acceptance_criteria:
        return {"ok": False, "error": "objectives and acceptance_criteria are required"}
    return {
        "ok": True,
        "work_items": [
            {"role": "systems_architect", "task": "define data and runtime contracts"},
            {"role": "network_engineer", "task": "validate permitted source connectivity"},
            {"role": "frontend_dom_specialist", "task": "map portal structure and DOM fields"},
            {"role": "junior_developer", "task": "implement bounded tasks and tests"},
        ],
        "objectives": objectives,
        "acceptance_criteria": acceptance_criteria,
        "qa_owner": "qa_gatekeeper",
    }


def collect_team_evidence(
    work_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Package role evidence for independent QA without accepting a QA score."""
    required_roles = {
        "systems_architect",
        "network_engineer",
        "frontend_dom_specialist",
        "junior_developer",
    }
    actual_roles = {item.get("role") for item in work_items}
    missing_roles = sorted(required_roles - actual_roles)
    if missing_roles:
        return {"ok": False, "error": "missing role evidence", "missing_roles": missing_roles}
    if any(not item.get("evidence") for item in work_items):
        return {"ok": False, "error": "every role must provide evidence"}
    return {
        "ok": True,
        "evidence": work_items,
        "next_role": "qa_gatekeeper",
        "qa_score": None,
    }