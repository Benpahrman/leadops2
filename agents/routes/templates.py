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
    
    replacements = {
        "{company_name}": company_name,
        "{clerk_pk}": clerk_pk,
        "{paypal_client_id}": paypal_client_id,
        "{slug}": slug,
        "{contact_email}": contact_email,
        "{jurisdiction}": jurisdiction
    }
    for k, v in replacements.items():
        html = html.replace(k, str(v))
    return html

def render_dashboard_html(lead_id: str) -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    paypal_client_id = os.environ.get("PAYPAL_CLIENT_ID", "BAAG2_UJT4CA2NwILo-DEMXNRsmwUQxfE8JDUOTMIynLP5Zg4bbOSefutaIQ_Zkd7aBP2yXC7fhYgbR6J0")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    replacements = {
        "{lead_id}": lead_id,
        "{clerk_pk}": clerk_pk,
        "{paypal_client_id}": paypal_client_id,
    }
    for k, v in replacements.items():
        html = html.replace(k, str(v))
    return html

def render_admin_html() -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "admin.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    return html.replace("{clerk_pk}", clerk_pk)

def render_operator_bio_html() -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "operator_bio.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace("{clerk_pk}", clerk_pk)

def render_landing_html() -> str:
    clerk_pk = os.environ.get("CLERK_PUBLISHABLE_KEY", "pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA")
    paypal_client_id = os.environ.get("PAYPAL_CLIENT_ID", "sb")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "landing.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    return html.replace("{clerk_pk}", clerk_pk).replace("{paypal_client_id}", paypal_client_id)

def render_terms_html() -> str:
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "terms.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()
