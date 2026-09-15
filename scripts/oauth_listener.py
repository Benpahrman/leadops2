#!/usr/bin/env python3
"""Local one-shot OAuth callback listener to capture Microsoft Graph refresh token."""

import http.server
import socketserver
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from agents.email.microsoft_graph import get_microsoft_graph_client

PORT = 8000
REDIRECT_URI = f"http://localhost:{PORT}/api/admin/oauth/microsoft/callback"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/admin/oauth/microsoft/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        error = params.get("error", [None])[0]
        error_desc = params.get("error_description", [None])[0]

        if error:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""
            <html><body style="font-family:sans-serif;background:#0f172a;color:#f87171;padding:40px;text-align:center;">
                <h2>❌ Microsoft Authorization Failed</h2>
                <p><b>{error}:</b> {error_desc}</p>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))
            return

        code = params.get("code", [None])[0]
        if not code:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Missing authorization code</h2>")
            return

        # Exchange code using local credentials
        mg = get_microsoft_graph_client()
        try:
            tokens = mg.exchange_code_for_tokens(code, redirect_uri=REDIRECT_URI)
            account = tokens.account_email or mg.account_email
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""
            <html><body style="font-family:sans-serif;background:#0f172a;color:#4ade80;padding:40px;text-align:center;">
                <h1>🎉 Microsoft Outlook Connected!</h1>
                <p style="color:#e2e8f0;font-size:18px;">Account <b>{account}</b> is now fully authorized for automated unspam & 2-way AI replies.</p>
                <p style="color:#94a3b8;">You can close this browser tab.</p>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))
            print(f"\n✅ [SUCCESS] Captured refresh token for: {account}")
            # Signal server shutdown
            sys.exit(0)
        except Exception as exc:
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""
            <html><body style="font-family:sans-serif;background:#0f172a;color:#f87171;padding:40px;text-align:center;">
                <h2>❌ Code Exchange Error</h2>
                <pre>{exc}</pre>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))
            print(f"\n❌ Exchange error: {exc}")


def main() -> None:
    print("=" * 60)
    print("LEADOPS MICROSOFT OAUTH LOCAL RECEIVER")
    print("=" * 60)
    print(f"Listening on: http://localhost:{PORT}/api/admin/oauth/microsoft/callback")
    print("Waiting for callback from Microsoft...")
    
    server = socketserver.TCPServer(("127.0.0.1", PORT), OAuthCallbackHandler)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        server.server_close()
        print("\nListener closed.")


if __name__ == "__main__":
    main()
