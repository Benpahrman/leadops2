"""Unit and integration tests for enhanced email discovery waterfall and deliverability engine."""

import os
from unittest.mock import MagicMock, patch
import pytest

from agents.email.verifier import (
    DeliverabilityVerifier,
    DeliverabilityStatus,
    VerificationResult,
    check_domain_auth_records,
)
from agents.tools.email_finder import (
    is_directory_or_portal,
    check_mx_record,
    check_is_catchall,
    construct_email_patterns,
    query_hunter_domain_search,
    query_apollo_people_match,
    extract_whois_and_soa_emails,
    discover_verified_email,
)


def test_directory_portal_detection():
    """Verify aggregator and directory portals are correctly identified and skipped."""
    assert is_directory_or_portal("https://www.loopnet.com/Listing/12345")
    assert is_directory_or_portal("loopnet.com")
    assert is_directory_or_portal("https://yelp.com/biz/some-law-firm")
    assert is_directory_or_portal("yellowpages.com")
    assert is_directory_or_portal("https://www.psychologytoday.com/us/therapists")
    assert is_directory_or_portal("https://www.bbb.org/us/tx/austin")
    assert is_directory_or_portal("https://facebook.com/myroofingco")

    # Legitimate commercial company domains must NOT be flagged as directories
    assert not is_directory_or_portal("https://apexroofingtx.com")
    assert not is_directory_or_portal("lonestarassetrecovery.com")
    assert not is_directory_or_portal("https://acmelegal.com/contact")


def test_construct_email_patterns_comprehensive():
    """Verify common statistical executive email patterns are synthesized correctly."""
    patterns = construct_email_patterns("Sarah", "Connor", "cyberdyne.org")
    assert "sarah.connor@cyberdyne.org" in patterns
    assert "sconnor@cyberdyne.org" in patterns
    assert "sarah@cyberdyne.org" in patterns
    assert "office@cyberdyne.org" in patterns
    assert "contact@cyberdyne.org" in patterns


def test_deliverability_verifier_business_roles():
    """Verify DeliverabilityVerifier allows business inquiry roles when configured."""
    # When allow_business_roles is False (strict default):
    strict_verifier = DeliverabilityVerifier(probe_smtp=False, probe_web=False, allow_business_roles=False)
    res_strict = strict_verifier.verify("office@github.com")
    assert res_strict.is_role_account
    assert res_strict.status == DeliverabilityStatus.RISKY
    assert not res_strict.is_safe_to_send

    # When allow_business_roles is True:
    permissive_verifier = DeliverabilityVerifier(probe_smtp=False, probe_web=False, allow_business_roles=True)
    res_permissive = permissive_verifier.verify("office@github.com")
    assert res_permissive.is_role_account
    assert res_permissive.status == DeliverabilityStatus.DELIVERABLE
    assert res_permissive.is_safe_to_send

    # Disallowed system roles (noreply, postmaster, test) must STILL be rejected even with allow_business_roles=True
    res_noreply = permissive_verifier.verify("noreply@github.com")
    assert res_noreply.is_role_account
    assert res_noreply.status == DeliverabilityStatus.RISKY
    assert not res_noreply.is_safe_to_send

    res_test = permissive_verifier.verify("test@github.com")
    assert res_test.is_role_account
    assert res_test.status == DeliverabilityStatus.RISKY


@patch("httpx.Client.get")
def test_hunter_io_api_connector(mock_get):
    """Verify Hunter.io API connector parses emails and formats correctly."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "domain": "acmeroofing.com",
            "pattern": "{first}.{last}",
            "emails": [
                {
                    "value": "john.smith@acmeroofing.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "position": "Managing Partner",
                    "confidence": 94,
                }
            ],
        }
    }
    mock_get.return_value = mock_resp

    result = query_hunter_domain_search("acmeroofing.com", api_key="test_hunter_key")
    assert result["ok"]
    assert len(result["emails"]) == 1
    assert result["emails"][0]["email"] == "john.smith@acmeroofing.com"
    assert result["emails"][0]["confidence"] == 0.94
    assert result["pattern"] == "{first}.{last}"


@patch("httpx.Client.post")
def test_apollo_io_api_connector(mock_post):
    """Verify Apollo.io API connector parses executive emails correctly."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "people": [
            {
                "id": "123",
                "name": "Jane Doe",
                "title": "President & Founder",
                "email": "jane@apexcapital.com",
            }
        ]
    }
    mock_post.return_value = mock_resp

    result = query_apollo_people_match(company_name="Apex Capital", domain="apexcapital.com", api_key="test_apollo_key")
    assert result["ok"]
    assert len(result["emails"]) == 1
    assert result["emails"][0]["email"] == "jane@apexcapital.com"
    assert result["emails"][0]["title"] == "President & Founder"


def test_check_domain_auth_records():
    """Verify SPF and DMARC inspection retrieves TXT records for live domains."""
    res = check_domain_auth_records("google.com")
    assert res["domain"] == "google.com"
    assert res["has_spf"]
    assert "v=spf1" in res["spf_record"]
    assert res["has_dmarc"]
    assert res["is_ready_for_cold_outreach"]


def test_discover_verified_email_waterfall():
    """Verify full multi-stage discovery waterfall returns best deliverable email."""
    # Test on a known domain with contact name pattern synthesis
    res = discover_verified_email(
        company_name="GitHub Inc",
        website_url="https://github.com",
        contact_name="Thomas Dohmke",
        contact_role="CEO",
    )
    assert res["ok"]
    assert "@github.com" in res["email"]
    assert res["deliverable"]
    assert res["mx_domain"]
