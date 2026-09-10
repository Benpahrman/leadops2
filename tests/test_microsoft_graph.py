"""Automated tests for Microsoft Graph API OAuth2 Client and Admin Integration."""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from agents.email.microsoft_graph import (
    MicrosoftGraphClient,
    MicrosoftTokenData,
    DEFAULT_SCOPES,
)
from agents.email.config import EmailSettings, InboxAccountConfig
from agents.email.client import EmailClient
from agents.api import create_app
app = create_app()


@pytest.fixture
def dummy_graph_client(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SOME_VAR=123\n", encoding="utf-8")
    client = MicrosoftGraphClient(
        client_id="test-client-id-12345",
        client_secret="test-client-secret-67890",
        tenant_id="common",
        redirect_uri="http://localhost:8000/api/admin/oauth/microsoft/callback",
        account_email="omnileadfeeder@outlook.com",
        refresh_token="",
        env_file_path=env_file,
    )
    return client


def test_microsoft_graph_client_init_and_properties(dummy_graph_client):
    """Verify initialization and property flags."""
    assert dummy_graph_client.client_id == "test-client-id-12345"
    assert dummy_graph_client.client_secret == "test-client-secret-67890"
    assert dummy_graph_client.is_configured is True
    assert dummy_graph_client.is_authorized is False


def test_authorization_url_generation(dummy_graph_client):
    """Verify authorization URL contains required parameters and scopes."""
    url = dummy_graph_client.get_authorization_url(state="custom_state_xyz")
    assert "login.microsoftonline.com/common/oauth2/v2.0/authorize" in url
    assert "client_id=test-client-id-12345" in url
    assert "response_type=code" in url
    assert "response_mode=query" in url
    assert "state=custom_state_xyz" in url
    assert "login_hint=omnileadfeeder%40outlook.com" in url
    assert "offline_access" in url
    assert "Mail.Read" in url
    assert "Mail.ReadWrite" in url
    assert "User.Read" in url


def test_exchange_code_for_tokens(dummy_graph_client):
    """Test exchanging auth code for access and refresh tokens."""
    mock_token_resp = {
        "access_token": "mock-access-token-abc",
        "refresh_token": "mock-refresh-token-xyz",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "offline_access Mail.Read",
    }
    mock_profile_resp = {
        "mail": "omnileadfeeder@outlook.com",
        "displayName": "Omni LeadFeeder",
        "userPrincipalName": "omnileadfeeder@outlook.com",
    }

    with patch("httpx.Client.post") as mock_post, patch("httpx.Client.get") as mock_get:
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = mock_token_resp
        mock_post.return_value = mock_post_resp

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_profile_resp
        mock_get.return_value = mock_get_resp

        tokens = dummy_graph_client.exchange_code_for_tokens("auth-code-123")

        assert tokens.access_token == "mock-access-token-abc"
        assert tokens.refresh_token == "mock-refresh-token-xyz"
        assert tokens.account_email == "omnileadfeeder@outlook.com"
        assert dummy_graph_client.is_authorized is True

        # Verify .env persistence
        saved_env = dummy_graph_client.env_file_path.read_text(encoding="utf-8")
        assert 'MICROSOFT_REFRESH_TOKEN="mock-refresh-token-xyz"' in saved_env


def test_silent_refresh_access_token(dummy_graph_client):
    """Test silent access token refresh using stored refresh token."""
    dummy_graph_client.tokens.refresh_token = "stored-refresh-token"
    dummy_graph_client.tokens.expires_at = time.time() - 100  # Expired

    mock_refresh_resp = {
        "access_token": "refreshed-access-token-999",
        "refresh_token": "rotated-refresh-token-111",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_refresh_resp
        mock_post.return_value = mock_resp

        token = dummy_graph_client.acquire_token()

        assert token == "refreshed-access-token-999"
        assert dummy_graph_client.tokens.refresh_token == "rotated-refresh-token-111"
        assert dummy_graph_client.tokens.is_expired is False


def test_fetch_unseen_emails_normalizes_to_leadops_format(dummy_graph_client):
    """Test polling unread emails from Graph API and normalizing to LeadOps format."""
    dummy_graph_client.tokens.access_token = "valid-token"
    dummy_graph_client.tokens.expires_at = time.time() + 3600
    dummy_graph_client.tokens.refresh_token = "valid-refresh"

    mock_graph_messages = {
        "value": [
            {
                "id": "AAMkAD12345",
                "conversationId": "conv_999",
                "subject": "Re: County probate docket update",
                "receivedDateTime": "2026-09-09T14:30:00Z",
                "hasAttachments": False,
                "isRead": False,
                "from": {
                    "emailAddress": {
                        "name": "Sarah Connor",
                        "address": "sarah@austinestateplanning.com",
                    }
                },
                "body": {
                    "contentType": "html",
                    "content": "<p>Yes Alex, we would love to see the daily feed.</p>",
                },
            }
        ]
    }

    with patch("httpx.Client.get") as mock_get, patch("httpx.Client.patch") as mock_patch:
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_graph_messages
        mock_get.return_value = mock_get_resp

        mock_patch_resp = MagicMock()
        mock_patch_resp.status_code = 200
        mock_patch.return_value = mock_patch_resp

        emails = dummy_graph_client.fetch_unseen_emails(mark_as_read=True)

        assert len(emails) == 1
        msg = emails[0]
        assert msg["message_id"] == "AAMkAD12345"
        assert msg["sender_email"] == "sarah@austinestateplanning.com"
        assert msg["sender_name"] == "Sarah Connor"
        assert msg["subject"] == "Re: County probate docket update"
        assert "Yes Alex, we would love to see the daily feed." in msg["body_text"]
        assert msg["provider"] == "microsoft_graph"

        # Verify message was marked as read
        mock_patch.assert_called_once()


def test_test_connection_diagnostics(dummy_graph_client):
    """Test test_connection returns proper diagnostic reporting."""
    # When not authorized
    dummy_graph_client.tokens.refresh_token = ""
    res = dummy_graph_client.test_connection()
    assert res["configured"] is True
    assert res["authorized"] is False
    assert "Connect Outlook Account" in res["message"]

    # When authorized
    dummy_graph_client.tokens.refresh_token = "valid-refresh"
    dummy_graph_client.tokens.access_token = "valid-access"
    dummy_graph_client.tokens.expires_at = time.time() + 3600

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "mail": "omnileadfeeder@outlook.com",
            "displayName": "Omni LeadFeeder",
        }
        mock_get.return_value = mock_resp

        res_authed = dummy_graph_client.test_connection()
        assert res_authed["success"] is True
        assert res_authed["account_email"] == "omnileadfeeder@outlook.com"
        assert "Successfully connected to Microsoft Graph" in res_authed["message"]


def test_disconnect_clears_tokens(dummy_graph_client):
    """Test disconnecting clears local state and removes refresh token."""
    dummy_graph_client.tokens.refresh_token = "existing-token"
    dummy_graph_client.disconnect()
    assert dummy_graph_client.tokens.refresh_token == ""
    assert dummy_graph_client.is_authorized is False


def test_fastapi_admin_oauth_routes():
    """Verify the FastAPI OAuth status, authorize, and disconnect endpoints."""
    client = TestClient(app)

    # 1. Status endpoint
    status_resp = client.get("/api/admin/oauth/microsoft/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["ok"] is True
    assert "status" in status_data

    # 2. Authorize endpoint without client_id gives 400
    with patch.dict("os.environ", {"MICROSOFT_CLIENT_ID": "", "AZURE_CLIENT_ID": ""}):
        from agents.email.microsoft_graph import MicrosoftGraphClient
        with patch("agents.email.microsoft_graph.get_microsoft_graph_client") as mock_gc:
            mock_inst = MagicMock()
            mock_inst.client_id = ""
            mock_gc.return_value = mock_inst
            auth_resp = client.get("/api/admin/oauth/microsoft/authorize")
            assert auth_resp.status_code == 400

    # 3. Authorize endpoint with client_id returns auth_url
    with patch("agents.email.microsoft_graph.get_microsoft_graph_client") as mock_gc:
        mock_inst = MagicMock()
        mock_inst.client_id = "test-client-id"
        mock_inst.get_authorization_url.return_value = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=test-client-id"
        mock_gc.return_value = mock_inst

        auth_resp = client.get("/api/admin/oauth/microsoft/authorize")
        assert auth_resp.status_code == 200
        assert "login.microsoftonline.com" in auth_resp.json()["auth_url"]
