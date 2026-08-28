import json
import pytest

from agents.build_loop import BuildPlan, TeamRole
from agents.job_runner import LocalBuildRunner
from agents.tools.dom_pruner import prune_dom
from agents.tools.waf_prober import generate_browser_headers, probe_waf_signatures
from agents.tools.playwright_runner import ScraperTask, compile_extraction_script
from agents.tools.specialist_handlers import (
    get_default_specialist_handlers,
    network_engineer_handler,
    frontend_dom_specialist_handler,
    systems_architect_handler,
    junior_developer_handler,
)


def test_dom_pruner_strips_scripts_and_extracts_tables():
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head><script>alert('noise');</script><style>.bad{color:red;}</style></head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <h1>Public Filings</h1>
        <table id="permits">
            <tr><th>PermitID</th><th>Applicant</th><th>Date</th></tr>
            <tr><td>P-100</td><td>Acme Corp</td><td>2026-08-20</td></tr>
            <tr><td>P-101</td><td>Beta LLC</td><td>2026-08-21</td></tr>
        </table>
        <form action="/search" method="post">
            <input type="text" name="q" placeholder="Search..." />
        </form>
        <footer><p>Copyright 2026</p></footer>
    </body>
    </html>
    """
    result = prune_dom(raw_html)
    assert "alert('noise')" not in result["clean_text"]
    assert "Copyright 2026" not in result["clean_text"]
    assert len(result["tables"]) == 1
    assert result["tables"][0]["headers"] == ["PermitID", "Applicant", "Date"]
    assert len(result["tables"][0]["rows"]) == 2
    assert result["tables"][0]["rows"][0] == {"PermitID": "P-100", "Applicant": "Acme Corp", "Date": "2026-08-20"}
    assert len(result["forms"]) == 1
    assert result["forms"][0]["inputs"][0]["name"] == "q"


def test_waf_prober_headers_and_detection():
    headers = generate_browser_headers("https://court.example.gov/search")
    assert "User-Agent" in headers
    assert headers["Host"] == "court.example.gov"

    # Cloudflare detection
    cf_headers = {"cf-ray": "887a123bc", "server": "cloudflare"}
    res = probe_waf_signatures(cf_headers, "Access denied. Cloudflare challenge.", 403)
    assert res["detected_waf"] == "Cloudflare"
    assert res["blocked_or_challenged"] is True
    assert res["is_safe_to_scrape"] is False

    # Clean response
    clean_headers = {"server": "nginx/1.24"}
    res_clean = probe_waf_signatures(clean_headers, "Normal portal content", 200)
    assert res_clean["detected_waf"] is None
    assert res_clean["blocked_or_challenged"] is False
    assert res_clean["is_safe_to_scrape"] is True


def test_playwright_compiler():
    task = ScraperTask(
        url="https://portal.gov/cases",
        row_selector=".case-row",
        field_selectors={"title": ".title", "date": ".date"},
    )
    script = compile_extraction_script(task)
    assert "https://portal.gov/cases" in script
    assert ".case-row" in script


def test_specialist_handlers_with_local_build_runner():
    handlers = get_default_specialist_handlers()
    runner = LocalBuildRunner(handlers)
    plan = BuildPlan(
        iteration=1,
        objectives=("Extract court cases",),
        acceptance_criteria=("25 rows present",),
    )
    manifest = runner.run(plan)
    assert manifest is not None
    assert manifest.qa_handoff()["ready_for_qa"] is True
    assert len(manifest.artifacts) == 4
    
    # Check that each role produced valid JSON report
    for artifact in manifest.artifacts:
        data = json.loads(artifact.content)
        assert data["status"] == "PASSED"
