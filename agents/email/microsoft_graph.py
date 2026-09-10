"""Microsoft Graph API Client & OAuth2 Manager for LeadOps watched inbox integration.

Handles OAuth 2.0 authorization code flow, silent refresh token rotation,
and polling unread emails directly from Microsoft Graph v1.0.
"""

import json
import logging
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("leadops.email.microsoft_graph")

# Microsoft OAuth2 & Graph Endpoints
MICROSOFT_OAUTH_AUTHORIZE_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_OAUTH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
MICROSOFT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

DEFAULT_SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]


@dataclass
class MicrosoftTokenData:
    """Represents an active OAuth2 token state for Microsoft Graph."""

    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0
    token_type: str = "Bearer"
    scope: str = ""
    account_email: str = ""
    account_name: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if access token has expired (with a 5-minute safety buffer)."""
        return time.time() >= (self.expires_at - 300)


class MicrosoftGraphClient:
    """Production client for Microsoft Graph API & Outlook Mailbox operations."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        tenant_id: str | None = None,
        refresh_token: str | None = None,
        redirect_uri: str | None = None,
        account_email: str | None = None,
        env_file_path: Path | None = None,
    ) -> None:
        self.client_id = (
            client_id
            if client_id is not None
            else (os.environ.get("MICROSOFT_CLIENT_ID") or os.environ.get("AZURE_CLIENT_ID") or "")
        ).strip().strip('"\'')

        self.client_secret = (
            client_secret
            if client_secret is not None
            else (os.environ.get("MICROSOFT_CLIENT_SECRET") or os.environ.get("AZURE_CLIENT_SECRET") or "")
        ).strip().strip('"\'')

        self.tenant_id = (
            tenant_id
            if tenant_id is not None
            else (os.environ.get("MICROSOFT_TENANT_ID") or "common")
        ).strip().strip('"\'')

        default_redirect = os.environ.get("MICROSOFT_REDIRECT_URI")
        if not default_redirect:
            pub = os.environ.get("LEADOPS_PUBLIC_BASE_URL", "").strip().rstrip("/")
            if pub and "localhost" not in pub and "127.0.0.1" not in pub:
                default_redirect = f"{pub}/api/admin/oauth/microsoft/callback"
            elif os.environ.get("ENV") == "production" or os.environ.get("CONTAINER_APP_NAME"):
                default_redirect = "https://omnileadfeeder.tech/api/admin/oauth/microsoft/callback"
            else:
                default_redirect = "http://localhost:8000/api/admin/oauth/microsoft/callback"

        self.redirect_uri = (
            redirect_uri
            if redirect_uri is not None
            else default_redirect
        ).strip().strip('"\'')

        self.account_email = (
            account_email
            if account_email is not None
            else (os.environ.get("INBOX_WATCHER_EMAIL") or os.environ.get("OUTLOOK_USER") or "omnileadfeeder@outlook.com")
        ).strip().strip('"\'')

        raw_refresh = (
            refresh_token
            if refresh_token is not None
            else (os.environ.get("MICROSOFT_REFRESH_TOKEN") or "")
        ).strip().strip('"\'')

        self.env_file_path = env_file_path or (Path(__file__).parent.parent.parent / ".env")
        self.tokens = MicrosoftTokenData(
            refresh_token=raw_refresh,
            account_email=self.account_email,
        )

    @property
    def is_configured(self) -> bool:
        """Return True if Azure App Registration credentials exist."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_authorized(self) -> bool:
        """Return True if a valid refresh token exists for silent background access."""
        return bool(self.tokens.refresh_token)

    def get_authorization_url(self, state: str = "leadops_ms_auth", redirect_uri: str | None = None) -> str:
        """Construct the Microsoft OAuth 2.0 authorization URL for human 1-click consent."""
        if not self.client_id:
            raise ValueError("MICROSOFT_CLIENT_ID is not configured. Please set it in .env.")

        base_url = MICROSOFT_OAUTH_AUTHORIZE_URL.format(tenant=self.tenant_id)
        effective_redirect = redirect_uri or self.redirect_uri

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": effective_redirect,
            "response_mode": "query",
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "prompt": "select_account",
        }
        if self.account_email:
            params["login_hint"] = self.account_email

        return f"{base_url}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str | None = None) -> MicrosoftTokenData:
        """Exchange authorization code from OAuth callback for access and refresh tokens."""
        if not self.is_configured:
            raise ValueError("MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET are required for token exchange.")

        token_url = MICROSOFT_OAUTH_TOKEN_URL.format(tenant=self.tenant_id)
        effective_redirect = redirect_uri or self.redirect_uri

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": effective_redirect,
            "grant_type": "authorization_code",
            "scope": " ".join(DEFAULT_SCOPES),
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"❌ Failed to exchange Microsoft auth code: {resp.status_code} - {resp.text}")
                try:
                    err_json = resp.json()
                    desc = err_json.get("error_description", resp.text)
                except Exception:
                    desc = resp.text
                raise RuntimeError(f"Microsoft OAuth code exchange failed ({resp.status_code}): {desc}")

            data = resp.json()

        access_token = data.get("access_token", "")
        refresh_token = data.get("refresh_token") or self.tokens.refresh_token
        expires_in = int(data.get("expires_in", 3600))
        expires_at = time.time() + expires_in

        self.tokens.access_token = access_token
        self.tokens.refresh_token = refresh_token
        self.tokens.expires_at = expires_at
        self.tokens.token_type = data.get("token_type", "Bearer")
        self.tokens.scope = data.get("scope", "")

        # Automatically fetch user profile to capture verified email & display name
        try:
            profile = self.get_user_profile()
            self.tokens.account_email = profile.get("mail") or profile.get("userPrincipalName") or self.account_email
            self.tokens.account_name = profile.get("displayName") or ""
        except Exception as e:
            logger.warning(f"Could not retrieve user profile during token exchange: {e}")

        # Persist refresh token to .env so LeadOps stays authorized across restarts
        self._persist_refresh_token(self.tokens.refresh_token, self.tokens.account_email)

        logger.info(f"✅ [MICROSOFT OAUTH] Successfully authenticated account '{self.tokens.account_email}'. Token valid for {expires_in}s.")
        return self.tokens

    def refresh_access_token(self) -> str:
        """Silently refresh the access token using the stored refresh token."""
        if not self.tokens.refresh_token:
            raise ValueError("No refresh token available. User must authorize via /api/admin/oauth/microsoft/authorize first.")

        token_url = MICROSOFT_OAUTH_TOKEN_URL.format(tenant=self.tenant_id)
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.tokens.refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(DEFAULT_SCOPES),
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"❌ Failed to refresh Microsoft access token: {resp.status_code} - {resp.text}")
                raise RuntimeError(f"Microsoft OAuth refresh failed ({resp.status_code}): {resp.text}")

            data = resp.json()

        self.tokens.access_token = data.get("access_token", "")
        new_refresh = data.get("refresh_token")
        if new_refresh and new_refresh != self.tokens.refresh_token:
            self.tokens.refresh_token = new_refresh
            self._persist_refresh_token(new_refresh, self.tokens.account_email)

        expires_in = int(data.get("expires_in", 3600))
        self.tokens.expires_at = time.time() + expires_in
        logger.debug(f"🔄 [MICROSOFT OAUTH] Silently refreshed access token. Expires in {expires_in}s.")
        return self.tokens.access_token

    def acquire_token(self) -> str:
        """Acquire a valid access token, automatically refreshing if expired."""
        if self.tokens.access_token and not self.tokens.is_expired:
            return self.tokens.access_token

        if self.tokens.refresh_token:
            return self.refresh_access_token()

        raise ValueError("Microsoft Graph client is not authorized. Please initiate OAuth flow.")

    def get_user_profile(self) -> dict[str, Any]:
        """Fetch the authenticated Microsoft account profile from /v1.0/me."""
        token = self.acquire_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{MICROSOFT_GRAPH_BASE_URL}/me"

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Graph API /me failed ({resp.status_code}): {resp.text}")
            return resp.json()

    def fetch_unseen_emails(self, mark_as_read: bool = True, max_results: int = 20) -> list[dict[str, Any]]:
        """Fetch unread emails from the inbox folder using Microsoft Graph API.

        Normalizes messages into the standard LeadOps email structure used by InboundEmailWatcher.
        """
        if not self.is_authorized:
            logger.debug("Microsoft Graph client has no refresh token. Skipping Graph polling.")
            return []

        token = self.acquire_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": 'outlook.body-content-type="html"',
        }

        # Query unread messages ordered by receivedDateTime descending
        url = (
            f"{MICROSOFT_GRAPH_BASE_URL}/me/mailFolders/inbox/messages"
            f"?$filter=isRead eq false"
            f"&$top={max_results}"
            f"&$select=id,conversationId,subject,from,toRecipients,receivedDateTime,hasAttachments,body,isRead"
        )

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"❌ Graph API fetch messages failed ({resp.status_code}): {resp.text}")
                return []

            data = resp.json()

        messages_raw = data.get("value", [])
        normalized: list[dict[str, Any]] = []

        for msg in messages_raw:
            msg_id = msg.get("id", "")
            subject = msg.get("subject", "") or ""
            received_time = msg.get("receivedDateTime", "")

            # Sender extraction
            from_obj = msg.get("from", {}).get("emailAddress", {})
            sender_email = from_obj.get("address", "").strip().lower()
            sender_name = from_obj.get("name", "").strip()

            # Body extraction
            body_obj = msg.get("body", {})
            content_type = body_obj.get("contentType", "text").lower()
            body_content = body_obj.get("content", "") or ""

            if content_type == "html":
                body_html = body_content
                # Strip basic tags for text preview
                body_text = re.sub(r"<[^>]+>", " ", body_content).strip()
            else:
                body_text = body_content
                body_html = f"<p>{body_content.replace(chr(10), '<br>')}</p>"

            norm_msg = {
                "message_id": msg_id,
                "sender_email": sender_email,
                "sender_name": sender_name,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
                "date": received_time,
                "headers": {},
                "raw_bytes": b"",
                "provider": "microsoft_graph",
            }
            normalized.append(norm_msg)

            if mark_as_read and msg_id:
                try:
                    self.mark_as_read(msg_id)
                except Exception as e:
                    logger.warning(f"Could not mark Graph message {msg_id} as read: {e}")

        if normalized:
            logger.info(f"📥 [GRAPH INBOUND] Retrieved {len(normalized)} unread emails via Microsoft Graph API.")

        return normalized

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read in Microsoft Graph."""
        token = self.acquire_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{MICROSOFT_GRAPH_BASE_URL}/me/messages/{message_id}"
        payload = {"isRead": True}

        with httpx.Client(timeout=10.0) as client:
            resp = client.patch(url, headers=headers, json=payload)
            return resp.status_code in (200, 204)

    def test_connection(self) -> dict[str, Any]:
        """Verify Microsoft Graph credentials and token validity."""
        result = {
            "configured": self.is_configured,
            "authorized": self.is_authorized,
            "account_email": self.tokens.account_email or self.account_email,
            "client_id_present": bool(self.client_id),
            "client_secret_present": bool(self.client_secret),
            "success": False,
            "message": "",
        }

        if not self.is_configured:
            result["message"] = "Microsoft OAuth2 is not configured. Missing MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET in .env."
            return result

        if not self.is_authorized:
            result["message"] = "Azure App Registered, but Outlook account is not authorized yet. Please click 'Connect Outlook Account' to authorize."
            return result

        try:
            profile = self.get_user_profile()
            email = profile.get("mail") or profile.get("userPrincipalName") or self.account_email
            display_name = profile.get("displayName", "")
            result["success"] = True
            result["account_email"] = email
            result["account_name"] = display_name
            result["message"] = f"Successfully connected to Microsoft Graph as {display_name} <{email}>."
        except Exception as e:
            result["message"] = f"Microsoft Graph authentication failed: {e}"

        return result

    def disconnect(self) -> None:
        """Clear the refresh token and reset authorization state."""
        self.tokens = MicrosoftTokenData(account_email=self.account_email)
        self._persist_refresh_token("", self.account_email)
        logger.info("🔒 [MICROSOFT OAUTH] Disconnected Outlook account and removed refresh token.")

    def _persist_refresh_token(self, token: str, email: str = "") -> None:
        """Save MICROSOFT_REFRESH_TOKEN into .env and runtime environment."""
        os.environ["MICROSOFT_REFRESH_TOKEN"] = token
        if email:
            os.environ["INBOX_WATCHER_EMAIL"] = email
            os.environ["OUTLOOK_USER"] = email

        if not self.env_file_path.exists():
            logger.warning(f".env file not found at {self.env_file_path}")
            return

        try:
            content = self.env_file_path.read_text(encoding="utf-8")

            # Update or append MICROSOFT_REFRESH_TOKEN
            if "MICROSOFT_REFRESH_TOKEN=" in content:
                content = re.sub(
                    r"MICROSOFT_REFRESH_TOKEN=.*",
                    f'MICROSOFT_REFRESH_TOKEN="{token}"',
                    content,
                )
            else:
                content += f'\nMICROSOFT_REFRESH_TOKEN="{token}"\n'

            # Ensure watcher email is set
            if email:
                if "INBOX_WATCHER_EMAIL=" in content:
                    content = re.sub(
                        r"INBOX_WATCHER_EMAIL=.*",
                        f'INBOX_WATCHER_EMAIL="{email}"',
                        content,
                    )
                if "OUTLOOK_USER=" in content:
                    content = re.sub(
                        r"OUTLOOK_USER=.*",
                        f'OUTLOOK_USER="{email}"',
                        content,
                    )

            self.env_file_path.write_text(content, encoding="utf-8")
            logger.info("💾 [PERSISTENCE] Successfully updated MICROSOFT_REFRESH_TOKEN in .env.")
        except Exception as err:
            logger.error(f"Failed to persist MICROSOFT_REFRESH_TOKEN to .env: {err}")


# Global Singleton Client Instance
_graph_client: MicrosoftGraphClient | None = None


def get_microsoft_graph_client() -> MicrosoftGraphClient:
    """Return or initialize the singleton MicrosoftGraphClient instance."""
    global _graph_client
    if _graph_client is None:
        _graph_client = MicrosoftGraphClient()
    return _graph_client
