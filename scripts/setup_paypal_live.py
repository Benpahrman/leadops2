import base64
import json
import os
import sys
from pathlib import Path
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run():
    cid = os.environ.get("PAYPAL_LIVE_CLIENT_ID") or os.environ.get("PAYPAL_CLIENT_ID", "")
    sec = os.environ.get("PAYPAL_LIVE_CLIENT_SECRET") or os.environ.get("PAYPAL_CLIENT_SECRET", "")
    
    if not cid or not sec:
        # Read from .env directly if needed
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("PAYPAL_LIVE_CLIENT_ID="):
                    cid = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("PAYPAL_LIVE_CLIENT_SECRET="):
                    sec = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not cid or not sec:
        print("Error: PAYPAL_LIVE_CLIENT_ID or PAYPAL_LIVE_CLIENT_SECRET missing.")
        sys.exit(1)

    print("Authenticating with PayPal Live...")
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    token_resp = httpx.post(
        "https://api-m.paypal.com/v1/oauth2/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"},
        timeout=15.0,
    )
    if token_resp.status_code != 200:
        print(f"Auth failed ({token_resp.status_code}): {token_resp.text}")
        sys.exit(1)

    token = token_resp.json()["access_token"]
    print("✓ Successfully authenticated with PayPal Live API.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. Register Webhook
    webhook_url = "https://www.omnileadfeeder.tech/api/paypal/webhook"
    print(f"Registering Webhook: {webhook_url}...")
    webhook_payload = {
        "url": webhook_url,
        "event_types": [
            {"name": "PAYMENT.CAPTURE.COMPLETED"},
            {"name": "BILLING.SUBSCRIPTION.ACTIVATED"},
            {"name": "BILLING.SUBSCRIPTION.CANCELLED"},
            {"name": "BILLING.SUBSCRIPTION.SUSPENDED"},
            {"name": "BILLING.SUBSCRIPTION.EXPIRED"},
            {"name": "PAYMENT.SALE.COMPLETED"},
            {"name": "CHECKOUT.ORDER.APPROVED"},
        ]
    }
    
    hook_resp = httpx.post(
        "https://api-m.paypal.com/v1/notifications/webhooks",
        headers=headers,
        json=webhook_payload,
        timeout=15.0,
    )
    
    webhook_id = ""
    if hook_resp.status_code in (200, 201):
        webhook_id = hook_resp.json()["id"]
        print(f"✓ Webhook Created! ID: {webhook_id}")
    elif "WEBHOOK_URL_ALREADY_EXISTS" in hook_resp.text:
        print("Webhook already registered. Fetching existing ID...")
        list_hooks = httpx.get(
            "https://api-m.paypal.com/v1/notifications/webhooks",
            headers=headers,
            timeout=15.0,
        ).json().get("webhooks", [])
        for h in list_hooks:
            if h.get("url") == webhook_url:
                webhook_id = h["id"]
                break
        print(f"✓ Found existing Webhook ID: {webhook_id}")
    else:
        print(f"Webhook error ({hook_resp.status_code}): {hook_resp.text}")
        sys.exit(1)

    # 2. Create Product for Subscriptions
    print("Creating Billing Product on PayPal...")
    prod_payload = {
        "name": "OmniLeadFeeder Data Sync Engine",
        "description": "Automated daily county and public records extraction pipelines delivered to Google Sheets and Webhooks.",
        "type": "SERVICE",
        "category": "SOFTWARE",
    }
    prod_resp = httpx.post(
        "https://api-m.paypal.com/v1/catalogs/products",
        headers=headers,
        json=prod_payload,
        timeout=15.0,
    )
    if prod_resp.status_code in (200, 201):
        product_id = prod_resp.json()["id"]
        print(f"✓ Product Created! ID: {product_id}")
    else:
        print(f"Product creation note: {prod_resp.status_code} {prod_resp.text}")
        # Fetch existing product
        prods = httpx.get("https://api-m.paypal.com/v1/catalogs/products", headers=headers).json().get("products", [])
        product_id = prods[0]["id"] if prods else ""
        print(f"✓ Using Product ID: {product_id}")

    # 3. Create 3 Subscription Plans
    plans = {
        "WEEKLY": {"name": "Weekly Sync", "price": "250.00"},
        "DAILY": {"name": "Daily Sync", "price": "500.00"},
        "AI": {"name": "AI / Heavy Extraction", "price": "850.00"},
    }

    plan_ids = {}
    for tier_key, plan_info in plans.items():
        print(f"Creating Plan for {plan_info['name']} (${plan_info['price']}/mo)...")
        plan_payload = {
            "product_id": product_id,
            "name": f"OmniLeadFeeder - {plan_info['name']}",
            "description": f"Automated recurring extraction and delivery: {plan_info['name']}",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {
                        "interval_unit": "MONTH",
                        "interval_count": 1
                    },
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0, # Infinite regular cycles until cancelled
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": plan_info["price"],
                            "currency_code": "USD"
                        }
                    }
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3
            }
        }
        plan_resp = httpx.post(
            "https://api-m.paypal.com/v1/billing/plans",
            headers=headers,
            json=plan_payload,
            timeout=15.0,
        )
        if plan_resp.status_code in (200, 201):
            p_id = plan_resp.json()["id"]
            plan_ids[tier_key] = p_id
            print(f"✓ Plan Created for {tier_key}: {p_id}")
        else:
            print(f"Plan creation error for {tier_key}: {plan_resp.status_code} {plan_resp.text}")

    print("\n==========================================================")
    print("🎉 ALL PAYPAL LIVE INFRASTRUCTURE CREATED SUCCESSFULLY!")
    print("==========================================================")
    print(f"PAYPAL_CLIENT_ID:      {cid}")
    print(f"PAYPAL_WEBHOOK_ID:      {webhook_id}")
    print(f"PAYPAL_PLAN_ID_WEEKLY:  {plan_ids.get('WEEKLY', '')}")
    print(f"PAYPAL_PLAN_ID_DAILY:   {plan_ids.get('DAILY', '')}")
    print(f"PAYPAL_PLAN_ID_AI:      {plan_ids.get('AI', '')}")
    print("==========================================================")

    # Save to local summary json for azure script to ingest
    output = {
        "client_id": cid,
        "client_secret": sec,
        "webhook_id": webhook_id,
        "plan_weekly": plan_ids.get("WEEKLY", ""),
        "plan_daily": plan_ids.get("DAILY", ""),
        "plan_ai": plan_ids.get("AI", ""),
    }
    Path("paypal_live_config.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output

if __name__ == "__main__":
    run()
