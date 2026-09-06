"""Tests for Scraper Catalog and Admin Scraper & Output endpoints."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from agents.api import create_app
from agents.auth import ClerkUser, require_admin
from agents.scraper_catalog import (
    build_catalog,
    get_catalog,
    search_catalog,
    get_scraper_source_code,
    get_scraper_output_data,
    inspect_lead_artifact,
)
from agents.storage import InMemoryStorageBackend


@pytest.fixture
def mock_admin():
    return ClerkUser(
        user_id="user_admin_test",
        email="benpahrman@gmail.com",
        is_admin=True,
    )


@pytest.fixture
def client(mock_admin):
    storage = InMemoryStorageBackend()
    app = create_app(storage=storage, api_token="valid-secret-token")
    app.dependency_overrides[require_admin] = lambda: mock_admin
    return TestClient(app)


def test_build_and_search_catalog():
    catalog = get_catalog(refresh=False)
    assert isinstance(catalog, list)
    assert len(catalog) > 0

    # Ensure each item contains expected schema keys
    sample = catalog[0]
    for key in [
        "lead_id",
        "company_name",
        "has_scraper_code",
        "has_output_data",
        "output_records_count",
        "qa_status",
    ]:
        assert key in sample

    # Test search functionality
    search_results = search_catalog("defense", catalog)
    assert isinstance(search_results, list)
    for r in search_results:
        text = (
            r["company_name"] + " " + r["lead_id"] + " " + r["portal_name"] + " " + r["commercial_pain"]
        ).lower()
        assert "defense" in text


def test_api_list_scrapers(client):
    res = client.get("/api/admin/scrapers")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total"] > 0
    assert "scrapers" in data
    assert data["with_code"] > 0


def test_api_search_scrapers(client):
    res = client.get("/api/admin/scrapers?search=defense")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total"] >= 1
    assert any("defense" in s["company_name"].lower() or "defense" in s["lead_id"].lower() for s in data["scrapers"])


def test_api_get_scraper_code_and_output(client):
    catalog = get_catalog()
    # Find a scraper that has code and output
    candidate = next((c for c in catalog if c["has_scraper_code"] and c["has_output_data"]), None)
    if not candidate:
        pytest.skip("No candidate scraper with code and output found in build_artifacts")

    lead_id = candidate["lead_id"]

    # 1. Fetch code
    code_res = client.get(f"/api/admin/scrapers/{lead_id}/code")
    assert code_res.status_code == 200
    assert ("def " in code_res.text or "import " in code_res.text)

    # 2. Fetch JSON output
    out_res = client.get(f"/api/admin/scrapers/{lead_id}/output?format=json")
    assert out_res.status_code == 200
    out_json = out_res.json()
    assert out_json["ok"] is True
    assert out_json["rows_count"] > 0
    assert isinstance(out_json["data"], list)

    # 3. Fetch CSV output
    csv_res = client.get(f"/api/admin/scrapers/{lead_id}/output?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert len(csv_res.text) > 0
