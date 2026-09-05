"""Tests for LeadOps AI Specialist Tools: Web Search, Web Fetcher, and AI Tool Registry."""

import pytest
from agents.tools.web_search import search_web, search_company_intelligence, search_public_data_portals
from agents.tools.web_fetcher import fetch_page_content, extract_contact_info_from_url
from agents.tools.ai_tools_registry import AI_TOOL_DEFINITIONS, execute_tool_call
from agents.llm_client import LLMAgentEngine


def test_web_search_tool_returns_structured_results():
    results = search_web("Austin commercial building permits", max_results=3)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "title" in results[0]
    assert "url" in results[0]
    assert "snippet" in results[0]


def test_search_company_intelligence():
    intel = search_company_intelligence("DPR Construction", domain_hint="https://www.dpr.com")
    assert intel["company_name"] == "DPR Construction"
    assert "dpr.com" in intel["website"]
    assert len(intel["search_hits"]) > 0


def test_search_public_data_portals():
    portals = search_public_data_portals("building permits", "Austin TX")
    assert isinstance(portals, list)
    assert len(portals) > 0


def test_web_fetcher_content_and_contacts():
    res = fetch_page_content("https://data.austintexas.gov/")
    assert "ok" in res
    assert "status_code" in res
    assert "emails" in res
    assert "phones" in res


def test_extract_contact_info_from_url():
    contacts = extract_contact_info_from_url("https://www.dpr.com")
    assert "website" in contacts
    assert "verified_email" in contacts
    assert "@" in contacts["verified_email"]


def test_ai_tools_registry_definitions_and_execution():
    assert len(AI_TOOL_DEFINITIONS) >= 8
    
    # Test search_web execution via registry
    res = execute_tool_call("search_web", {"query": "SAM.gov defense contract RFPs", "max_results": 2})
    assert isinstance(res, list)
    assert len(res) > 0

    # Test lead_database_tool execution via registry
    db_res = execute_tool_call("lead_database_tool", {
        "company_name": "Acme Qualification Corp",
        "automation_opportunity_score": 85,
        "purchase_probability": 70,
        "pain_severity": 8,
    })
    assert db_res["status"] == "QUALIFIED_AND_READY"
    assert db_res["record"]["company_name"] == "Acme Qualification Corp"
    
    # Test unknown tool handling
    err = execute_tool_call("non_existent_tool", {})
    assert "error" in err


def test_llm_agent_run_scout_discovery_agent():
    engine = LLMAgentEngine()
    datasets = {"austin-commercial-permits": {}, "sam-gov-defense-rfps": {}}
    res = engine.run_scout_discovery_agent("Commercial Construction", datasets)
    assert isinstance(res, dict)


def test_llm_agent_run_pitcher_agent():
    engine = LLMAgentEngine()
    lead_info = {
        "company_name": "DPR Construction",
        "contact_name": "Mark Vance",
        "contact_role": "VP Preconstruction",
        "niche": "Commercial Construction",
        "portal_name": "Austin Building Permits",
        "pain_point": "Needs daily permit feeds",
    }
    pitch = engine.run_pitcher_agent(lead_info, "https://leadops.app/p/demo")
    assert isinstance(pitch, dict)


def test_llm_agent_run_lead_enrichment_agent():
    engine = LLMAgentEngine()
    sample_rows = [{"permit_id": "P-101", "val": "$500k"}, {"permit_id": "P-102", "val": "$1.2M"}]
    enrichment = engine.run_lead_enrichment_agent("DPR Construction", "https://www.dpr.com", "Commercial Construction", sample_rows)
    assert "data_quality_score" in enrichment
    assert "qa_verdict" in enrichment
    assert "cleaned_sample_records" in enrichment
    assert len(enrichment["cleaned_sample_records"]) == 2


def test_two_react_loop_architecture():
    from agents.build_loop import BuildLoop, BuildPhase, TeamRole
    engine = LLMAgentEngine()
    
    # 1. Outer Loop: Start Plan (Dev Lead AI)
    loop = BuildLoop()
    plan = loop.start_plan(["Extract Austin commercial building permits"], ["Verify non-null permit number", "HTTP 200 OK"], llm_engine=engine)
    assert loop.phase == BuildPhase.DEV_LEAD
    assert plan.iteration == 1
    
    # 2. Outer Loop: Transition to Team Build
    loop.start_team_build(plan)
    assert loop.phase == BuildPhase.TEAM_BUILD
    
    # 3. Inner Swarm ReAct Loop: Execute Specialist Iteration
    target_url = "https://data.austintexas.gov/Building-and-Development/Issued-Construction-Permits/3syk-w9eu"
    selected_fields = ["permit_number", "issue_date", "valuation", "contractor_name"]
    swarm_summary = loop.run_inner_swarm_build(target_url, selected_fields, llm_engine=engine)
    assert swarm_summary["is_complete"] is True
    assert len(swarm_summary["roles_executed"]) == 4
    
    # 4. Outer Loop: Independent QA Gatekeeper AI
    sample_records = [{"permit_number": "BP-2024-001", "valuation": "$1,250,000"}]
    passed = loop.evaluate_qa_with_ai(list(plan.objectives), sample_records, llm_engine=engine)
    assert passed is True
    assert loop.phase == BuildPhase.ESCROW_READY


