from workers.leadops_tools import (
    prepare_confirmation_intake,
    assign_builder_team,
    collect_team_evidence,
    create_team_work_items,
    prepare_provisioning_plan,
    publish_sandbox_candidate,
    create_build_plan,
    evaluate_qa_gate,
    evaluate_build_evidence,
    record_research_evidence,
)


def test_research_tool_requires_evidence_and_confirmation():
    result = record_research_evidence(
        company_name="Acme Research",
        source_url="https://example.gov/cases",
        niche="Probate research",
        jurisdiction="Cook County, IL",
        portal_name="Cook County Probate",
        portal_url="https://example.gov/cases",
        suggested_fields=["case_number", "case_number", "filing_date"],
    )

    assert result["ok"] is True
    assert result["assumptions"]["suggested_fields"] == ["case_number", "filing_date"]
    assert result["requires_customer_confirmation"] is True


def test_scout_publishes_read_only_sandbox_candidate():
    result = publish_sandbox_candidate(
        "Acme Research",
        "lead-42",
        "https://example.gov/cases",
        [{"case_number": "A-1"}],
    )

    assert result["ok"] is True
    assert result["portal_path"] == "/p/acme-research-lead-42"
    assert result["read_only"] is True
    assert result["requires_customer_confirmation"] is True


def test_sandbox_candidate_rejects_empty_sample():
    result = publish_sandbox_candidate("Acme", "lead-42", "https://example.gov", [])
    assert result["ok"] is False


def test_intake_tool_defers_optional_questions():
    result = prepare_confirmation_intake({
        "company_name": "Acme Research",
        "source_url": "https://example.gov/cases",
        "assumptions": {"niche": "Probate research"},
    })

    assert result["ok"] is True
    assert result["primary_action"] == "confirm_assumptions"
    assert result["optional_questions_deferred"] is True
    assert all(field["requires_confirmation"] for field in result["fields"])


def test_provisioning_tool_requires_paid_state_and_creates_no_resources():
    unpaid = prepare_provisioning_plan("lead-1", "SOW_GENERATED")
    assert unpaid["ok"] is False

    plan = prepare_provisioning_plan("lead-1", "DEPOSIT_PAID")
    assert plan["ok"] is True
    assert plan["provider"] == "azure"
    assert plan["environment"] == "production"
    assert plan["cloud_resources_created"] is False
    assert plan["approval_required"] is True


def test_qa_gatekeeper_routes_failure_back_to_planner():
    plan = create_build_plan(["map portal"], ["95 percent valid"])
    assert plan["next_role"] == "dev_lead"

    result = evaluate_qa_gate(91, ["filing date is missing"])
    assert result["gate"] == "failed"
    assert result["next_phase"] == "replan"
    assert result["next_role"] == "planner"


def test_qa_gatekeeper_unlocks_escrow_at_threshold():
    result = evaluate_qa_gate(95)
    assert result["gate"] == "passed"
    assert result["next_phase"] == "escrow_ready"


def test_qa_score_is_computed_from_acceptance_evidence():
    result = evaluate_build_evidence([
        {"criterion": "portal loads", "passed": True},
        {"criterion": "rows validate", "passed": False},
    ])
    assert result["score"] == 50.0
    assert result["gate"] == "failed"
    assert result["next_role"] == "planner"
    assert "rows validate" in result["feedback"]


def test_builder_team_has_four_roles_and_excludes_qa():
    result = assign_builder_team()
    assert set(result["roles"]) == {
        "network_engineer",
        "frontend_dom_specialist",
        "systems_architect",
        "junior_developer",
    }
    assert result["qa_outside_team"] is True


def test_dev_lead_creates_role_work_items_and_hands_evidence_to_qa():
    work = create_team_work_items(["build feed"], ["rows validate"])
    assert work["ok"] is True
    assert work["qa_owner"] == "qa_gatekeeper"
    roles = {item["role"] for item in work["work_items"]}
    assert roles == {
        "systems_architect",
        "network_engineer",
        "frontend_dom_specialist",
        "junior_developer",
    }

    evidence = collect_team_evidence([
        {"role": role, "evidence": f"{role} complete"} for role in roles
    ])
    assert evidence["ok"] is True
    assert evidence["next_role"] == "qa_gatekeeper"
    assert evidence["qa_score"] is None