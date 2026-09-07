import os
import re

DEFAULT_DEV_PAYPAL_ID = "BAAG2_UJT4CA2NwILo-DEMXNRsmwUQxfE8JDUOTMIynLP5Zg4bbOSefutaIQ_Zkd7aBP2yXC7fhYgbR6J0"
DEFAULT_DEV_CLERK_PK = "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA"

SPA_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend",
    "dist",
    "index.html"
)

def render_react_spa(lead_data: dict | None = None, slug: str | None = None) -> str:
    """Returns compiled React Single Page App index.html with environment keys injected."""
    paypal_mode = os.environ.get("PAYPAL_MODE", "sandbox").lower()
    paypal_client_id = (
        (os.environ.get("PAYPAL_LIVE_CLIENT_ID") if paypal_mode == "live" else None)
        or os.environ.get("PAYPAL_CLIENT_ID")
        or DEFAULT_DEV_PAYPAL_ID
    )
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY") or DEFAULT_DEV_CLERK_PK

    if not os.path.exists(SPA_INDEX_PATH):
        # Fallback minimal bootstrap if dist has not been compiled yet
        return f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OmniLeadFeeder</title>
    <script>
        window.__CLERK_PUBLISHABLE_KEY__ = "{clerk_pk}";
        window.__PAYPAL_CLIENT_ID__ = "{paypal_client_id}";
    </script>
</head>
<body style="background:#030712; color:#fff; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; margin:0;">
    <div style="text-align:center;">
        <h2>⚡ OmniLeadFeeder React SPA</h2>
        <p style="color:#9ca3af;">Frontend assets compiling. Please run <code>npm run build</code> in /frontend.</p>
    </div>
</body>
</html>"""

    with open(SPA_INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace hardcoded dev PayPal client ID with environment key
    html = html.replace(DEFAULT_DEV_PAYPAL_ID, paypal_client_id)
    html = html.replace("{paypal_client_id}", paypal_client_id)
    html = html.replace("{clerk_pk}", clerk_pk)

    # Inject runtime window variables
    injection = f"""<script>
    window.__CLERK_PUBLISHABLE_KEY__ = "{clerk_pk}";
    window.__PAYPAL_CLIENT_ID__ = "{paypal_client_id}";
    window.__ACTIVE_SLUG__ = "{slug or ''}";
  </script>
</head>"""
    html = re.sub(r"</head>", injection, html, count=1)
    return html

# Exported route renderers pointing directly to the React SPA
def render_portal_html(slug: str, lead_data: dict | None = None) -> str:
    return render_react_spa(lead_data=lead_data, slug=slug)

def render_dashboard_html(lead_id: str) -> str:
    return render_react_spa(slug=lead_id)

def render_admin_html() -> str:
    return render_react_spa()

def render_landing_html() -> str:
    return render_react_spa()

def render_terms_html() -> str:
    return render_react_spa()

def render_operator_bio_html() -> str:
    return render_react_spa()
