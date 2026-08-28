"""Clerk authentication adapter and session verification with Global Admin & Company association."""

import json
import os
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, status, Cookie

# Super Admin Email Addresses
GLOBAL_ADMIN_EMAILS = {
    "pahrmancb@gmail.com",
    "pharmancb@gmail.com",
}


@dataclass
class ClerkUser:
    user_id: str
    email: str
    lead_id: str | None = None
    org_id: str | None = None
    role: str = "member"
    is_admin: bool = False
    metadata: dict[str, Any] | None = None


class ClerkAuthService:
    """Validates Clerk session tokens and extracts lead_id metadata & Global Admin privileges."""

    def __init__(
        self,
        secret_key: str | None = None,
        publishable_key: str | None = None,
        jwt_key: str | None = None,
    ) -> None:
        env = os.environ.get("ENV", "production").lower()
        secret_key = secret_key or os.environ.get("CLERK_SECRET_KEY")
        if not secret_key and env == "production":
            raise ValueError("CLERK_SECRET_KEY must be set in production")
        self.secret_key = secret_key or "mock_clerk_secret_key"
        self.publishable_key = publishable_key or os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_leadops_clerk")
        self.jwt_key = jwt_key or os.environ.get("CLERK_JWT_KEY", "")

    def is_admin_email(self, email: str) -> bool:
        """Check if email belongs to the Global Admin team."""
        clean = (email or "").strip().lower()
        return clean in GLOBAL_ADMIN_EMAILS or clean.replace(" ", "") in GLOBAL_ADMIN_EMAILS

    def verify_token(self, token: str) -> ClerkUser:
        """Verify Clerk session JWT or development bearer token."""
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

        # Support development / mock tokens: "Bearer mock_user_<user_id>_lead_<lead_id>"
        # SECURITY: Only allowed in development/test environments
        env = os.environ.get("ENV", "production").lower()
        is_dev_env = env in {"development", "dev", "test", "local"}
        if env != "production" and os.environ.get("ALLOW_DEV_ADMIN") == "true":
            is_dev_env = True

        if is_dev_env and (token.startswith("mock_user_") or token.startswith("test_token_") or "pahrmancb" in token):
            parts = token.split("_")
            user_id = parts[2] if len(parts) > 2 else "admin_user"
            lead_id = parts[4] if len(parts) > 4 else None
            email = "pahrmancb@gmail.com" if ("pahrmancb" in token or user_id in {"admin", "founder"}) else f"client_{user_id}@example.com"
            is_admin = self.is_admin_email(email) or user_id in {"admin", "founder"} or "admin" in token
            return ClerkUser(
                user_id=f"user_{user_id}",
                email=email,
                lead_id=lead_id,
                role="admin" if is_admin else "member",
                is_admin=is_admin,
                metadata={"lead_id": lead_id, "is_admin": is_admin},
            )

        # Real Clerk JWT verification
        try:
            import jwt

            # Attempt verified decode if JWT key is configured
            decoded = None
            if self.jwt_key:
                try:
                    pub_key = self.jwt_key
                    if "-----BEGIN" not in pub_key:
                        cleaned = pub_key.replace("\\n", "\n").strip()
                        if not cleaned.startswith("-----BEGIN"):
                            pub_key = f"-----BEGIN PUBLIC KEY-----\n{cleaned}\n-----END PUBLIC KEY-----"
                        else:
                            pub_key = cleaned
                    decoded = jwt.decode(
                        token,
                        pub_key,
                        algorithms=["RS256", "HS256"],
                        options={"verify_aud": False},
                    )
                except jwt.exceptions.InvalidSignatureError:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid JWT signature — token rejected",
                    )
                except jwt.exceptions.ExpiredSignatureError:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session token expired — please sign in again",
                    )
                except Exception:
                    # Fall through to JWKS
                    decoded = None

            # Fallback to JWKS verification if publishable key is available
            if decoded is None and self.publishable_key:
                domain = ""
                try:
                    import base64
                    parts = self.publishable_key.split("_")
                    if len(parts) >= 3:
                        payload = parts[2]
                        payload += "=" * (4 - len(payload) % 4)
                        decoded_str = base64.b64decode(payload).decode("utf-8")
                        if decoded_str.endswith("$"):
                            decoded_str = decoded_str[:-1]
                        domain = decoded_str
                except Exception:
                    pass

                if domain:
                    jwks_url = f"https://{domain}/.well-known/jwks.json"
                    try:
                        jwks_client = jwt.PyJWKClient(jwks_url)
                        signing_key = jwks_client.get_signing_key_from_jwt(token)
                        decoded = jwt.decode(
                            token,
                            signing_key.key,
                            algorithms=["RS256"],
                            options={"verify_aud": False},
                        )
                    except jwt.exceptions.InvalidSignatureError:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid JWT signature — token rejected",
                        )
                    except jwt.exceptions.ExpiredSignatureError:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session token expired — please sign in again",
                        )
                    except Exception:
                        decoded = None

            if decoded is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session token — signature could not be verified",
                )

            sub = decoded.get("sub", "")
            meta = decoded.get("public_metadata") or decoded.get("metadata") or {}
            email = decoded.get("email") or meta.get("email") or f"{sub}@customer.leadops.app"
            lead_id = meta.get("lead_id")
            org_id = decoded.get("org_id") or meta.get("org_id")
            is_admin = self.is_admin_email(email) or meta.get("role") == "admin"
            role = "admin" if is_admin else decoded.get("org_role", "member")

            return ClerkUser(
                user_id=sub,
                email=email,
                lead_id=lead_id,
                org_id=org_id,
                role=role,
                is_admin=is_admin,
                metadata=meta,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid session token: {e}")

    def claim_sandbox_account(self, user_id: str, lead_id: str, email: str) -> dict[str, Any]:
        """Attach lead_id to Clerk publicMetadata so the frontend and API can identify the customer's feed."""
        is_admin = self.is_admin_email(email)
        return {
            "user_id": user_id,
            "email": email,
            "public_metadata": {
                "lead_id": lead_id,
                "role": "admin" if is_admin else "member",
                "claimed_at": "2026-08-27T00:00:00Z",
            },
        }


def get_current_user(
    authorization: str = Header(None),
    token: str | None = None,
    clerk_session: str = Cookie(None, alias="__session"),
    clerk_client_uat: str = Cookie(None, alias="__client_uat"),
) -> ClerkUser:
    """FastAPI dependency for verifying authenticated customer requests (supports Header, Query string, and Clerk cookies)."""
    raw_token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Bearer token format")
    elif token:
        raw_token = token
    elif clerk_session:
        raw_token = clerk_session
    elif clerk_client_uat:
        raw_token = clerk_client_uat

    if not raw_token:
        # Fallback to dev admin for test harnesses if explicitly allowed
        env = os.environ.get("ENV", "production").lower()
        allow_dev_admin = os.environ.get("ALLOW_DEV_ADMIN", "false").lower() == "true"
        # Restrict dev admin bypass to ENV=test only
        if env == "test" and allow_dev_admin and os.environ.get("DISABLE_TEST_FALLBACK") != "true":
            return ClerkUser(user_id="dev_admin", email="pahrmancb@gmail.com", role="admin", is_admin=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token is required")

    auth_service = ClerkAuthService()
    try:
        return auth_service.verify_token(raw_token)
    except Exception as e:
        # Invalid/expired token - don't expose details
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")


def get_current_user_optional(
    authorization: str = Header(None),
    token: str | None = None,
    clerk_session: str = Cookie(None, alias="__session"),
    clerk_client_uat: str = Cookie(None, alias="__client_uat"),
) -> ClerkUser | None:
    """Optional auth dependency - returns None if no valid token, instead of raising 401.
    Use for HTML routes that should render sign-in component when unauthenticated."""
    raw_token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]
        else:
            return None
    elif token:
        raw_token = token
    elif clerk_session:
        raw_token = clerk_session
    elif clerk_client_uat:
        raw_token = clerk_client_uat

    if not raw_token:
        return None

    auth_service = ClerkAuthService()
    try:
        return auth_service.verify_token(raw_token)
    except Exception:
        return None


def require_admin(user: ClerkUser = Depends(get_current_user)) -> ClerkUser:
    """FastAPI dependency enforcing Global Admin role (e.g. pahrmancb@gmail.com)."""
    if not user.is_admin and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required for pahrmancb@gmail.com.",
        )
    return user
