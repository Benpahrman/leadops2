import os

def render_portal_html(slug: str, lead_data: dict | None = None) -> str:
    paypal_client_id = os.environ.get("PAYPAL_CLIENT_ID", "sb")
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    company_name = (lead_data.get("company_name") if lead_data else "") or slug.replace("lead-", "").replace("-", " ").title()
    jurisdiction = (lead_data.get("jurisdiction") if lead_data else "") or "Public Records Registry"
    contact_email = (lead_data.get("contact_email") if lead_data else "") or "team@company.com"
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "portal.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.format(
        company_name=company_name,
        clerk_pk=clerk_pk,
        paypal_client_id=paypal_client_id,
        slug=slug,
        contact_email=contact_email,
        jurisdiction=jurisdiction
    )

def render_dashboard_html(lead_id: str) -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.format(
        lead_id=lead_id,
        clerk_pk=clerk_pk
    )

def render_admin_html() -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "admin.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.format(
        clerk_pk=clerk_pk
    )

def render_operator_bio_html() -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "operator_bio.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.format(
        clerk_pk=clerk_pk
    )
