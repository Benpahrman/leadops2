#!/usr/bin/env python3
"""Manual or CLI exchange for Microsoft OAuth 2.0 authorization code."""

import argparse
import sys
from pathlib import Path
import urllib.parse

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from agents.email.microsoft_graph import get_microsoft_graph_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Exchange Microsoft OAuth code for tokens")
    parser.add_argument("code_or_url", help="Authorization code or full redirect URL containing code=")
    parser.add_argument(
        "--redirect-uri",
        default="https://omnileadfeeder.tech/api/admin/oauth/microsoft/callback",
        help="Redirect URI that was used during authorization",
    )
    args = parser.parse_args()

    raw_input = args.code_or_url.strip()
    code = raw_input

    # If full URL was pasted, extract the code query param
    if "code=" in raw_input:
        parsed = urllib.parse.urlparse(raw_input)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            code = params["code"][0]

    mg = get_microsoft_graph_client()
    print(f"Exchanging code with Microsoft for tenant '{mg.tenant_id}'...")

    try:
        tokens = mg.exchange_code_for_tokens(code, redirect_uri=args.redirect_uri)
        print(f"\n🎉 [SUCCESS] Authenticated successfully as: {tokens.account_email or mg.account_email}")
        print("Refresh token has been persisted to .env and engine is ready for 2-way Graph monitoring!")
    except Exception as exc:
        print(f"\n❌ Exchange failed: {exc}")
        print("Tip: If the redirect URI used in Azure was different (e.g. localhost), pass --redirect-uri <URI>.")


if __name__ == "__main__":
    main()
