"""Tests for Lead Database Tool, CRM Tool, and BDR Manager Qualification Scoring Framework."""

import pytest
from agents.tools.lead_database_tool import (
    calculate_automation_opportunity_score,
    evaluate_buyer_signals,
    is_lead_qualified,
    lead_database_tool,
    crm_tool,
    research_company_tool,
)
from agents.storage import InMemoryStorageBackend


def test_calculate_automation_opportunity_score():
    score_data = calculate_automation_opportunity_score(
        labor_intensive_operations=25,
        portal_usage=15,
        manual_data_entry=15,
        compliance_requirements=15,
        document_processing_volume=10,
        company_size_fit=10,
        growth_signals=10,
    )
    assert score_data["total_score"] == 100
    assert score_data["max_possible"] == 100
    assert score_data["breakdown"]["labor_intensive_operations"]["score"] == 25
    assert score_data["breakdown"]["portal_usage"]["score"] == 15
    assert score_data["breakdown"]["manual_data_entry"]["score"] == 15
    assert score_data["breakdown"]["compliance_requirements"]["score"] == 15
    assert score_data["breakdown"]["document_processing_volume"]["score"] == 10
    assert score_data["breakdown"]["company_size_fit"]["score"] == 10
    assert score_data["breakdown"]["growth_signals"]["score"] == 10


def test_evaluate_buyer_signals():
    text = "We are experiencing rapid growth and hiring operations coordinators to handle court filing compliance."
    signals = evaluate_buyer_signals(intel_text=text, industry="Probate Court")
    
    assert "Hiring Operations Coordinators" in signals["positive_signals"]
    assert "Rapid Growth" in signals["positive_signals"]
    assert "Heavy Compliance Burden" in signals["positive_signals"]
    assert signals["purchase_probability"] >= 50
    assert signals["pain_severity"] >= 7


def test_qualification_criteria_rules():
    # Case 1: High opportunity score (>= 65) qualifies
    assert is_lead_qualified(automation_opportunity_score=75, purchase_probability=30, pain_severity=4) is True
    
    # Case 2: High purchase probability (>= 50%) qualifies
    assert is_lead_qualified(automation_opportunity_score=50, purchase_probability=60, pain_severity=4) is True
    
    # Case 3: High pain severity (>= 7) qualifies
    assert is_lead_qualified(automation_opportunity_score=50, purchase_probability=30, pain_severity=8) is True
    
    # Case 4: None met -> Disqualified
    assert is_lead_qualified(automation_opportunity_score=40, purchase_probability=35, pain_severity=5) is False


def test_lead_database_tool_creation_and_deduplication():
    storage = InMemoryStorageBackend()

    # Step 1: Save first qualified lead
    result = lead_database_tool(
        company_name="Vanguard Builders",
        website="https://vanguardbuilders.com",
        industry="Commercial Construction",
        employee_count="50-100",
        estimated_revenue="$15M",
        location="Austin, TX",
        decision_makers=[{"name": "Robert Vance", "role": "VP of Operations", "email": "robert@vanguardbuilders.com", "phone": "(512) 555-0199"}],
        pain_points=["Checking Austin commercial permits manually every morning delays bids"],
        automation_opportunity_score=85,
        purchase_probability=75,
        pain_severity=9,
        recommended_solution="Automated Daily Austin Permit Extractor",
        outreach_angle="Time-to-lead advantage over regional commercial competitors",
        data_sources=["https://data.austintexas.gov/"],
        confidence_score=0.98,
        storage=storage,
    )

    assert result["status"] == "SAVED"
    lead_id = result["lead_id"]
    assert lead_id is not None
    assert result["record"]["automation_opportunity_score"] == 85
    assert result["record"]["purchase_probability"] == 75
    assert result["record"]["pain_severity"] == 9

    # Step 2: Saving same company deduplicates and updates instead of creating duplicate
    update_result = lead_database_tool(
        company_name="Vanguard Builders",
        website="https://vanguardbuilders.com",
        industry="Commercial Construction",
        automation_opportunity_score=90,
        purchase_probability=80,
        pain_severity=9,
        storage=storage,
    )

    assert update_result["status"] == "UPDATED"
    assert update_result["lead_id"] == lead_id

    # Verify storage has only 1 lead, not 2
    leads = storage.list_leads()
    assert len(leads) == 1
    assert leads[0].company_name == "Vanguard Builders"


def test_lead_database_tool_disqualifies_low_score_lead():
    result = lead_database_tool(
        company_name="Tiny Freelancer Co",
        website="https://tiny.example.com",
        automation_opportunity_score=30,
        purchase_probability=20,
        pain_severity=3,
    )
    assert result["status"] == "DISQUALIFIED"
    assert "Does not meet qualification threshold" in result["reason"]


def test_crm_tool_lookup():
    storage = InMemoryStorageBackend()
    lead_database_tool(
        company_name="Apex Legal Group",
        website="https://apexlegal.com",
        automation_opportunity_score=80,
        purchase_probability=70,
        pain_severity=8,
        storage=storage,
    )

    # Lookup existing
    check = crm_tool(action="check_exists", company_name="Apex Legal Group", storage=storage)
    assert check["exists"] is True
    assert check["company_name"] == "Apex Legal Group"

    # Lookup non-existing
    check_none = crm_tool(action="check_exists", company_name="Non Existent Firm", storage=storage)
    assert check_none["exists"] is False
