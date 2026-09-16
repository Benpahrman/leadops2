#!/usr/bin/env python3
"""Send a live test email to TestMail.app and retrieve the full deliverability payload."""

import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from agents.email.client import EmailClient
from agents.email.config import EmailSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("leadops.testmail")

TESTMAIL_API_KEY = "f5c19aa2-97d5-4efc-84b3-30fa59e87c80"
TESTMAIL_NAMESPACE = "kgddj"
TEST_TAG = "test"
TEST_RECIPIENT = f"{TESTMAIL_NAMESPACE}.{TEST_TAG}@inbox.testmail.app"

def send_and_retrieve():
    settings = EmailSettings.from_environment()
    client = EmailClient(settings=settings)

    subject = f"Deliverability Verification - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    body = (
        "Hi Team,\n\n"
        "This is an automated deliverability verification probe from the LeadOps Swarm.\n\n"
        "Testing SPF, DKIM, DMARC, and SpamAssassin score for olfmailer.com.\n\n"
        "Best regards,\n"
        "Alex | LeadOps Deliverability"
    )

    logger.info(f"📤 Dispatching test email to: {TEST_RECIPIENT}...")
    dispatch_res = client.send_email(
        to_email=TEST_RECIPIENT,
        to_name="TestMail QA Ingestion",
        subject=subject,
        text_body=body,
        is_transactional=True,
    )
    logger.info(f"Dispatch Result: {dispatch_res}")

    logger.info("⏳ Waiting 10 seconds for TestMail SMTP ingestion...")
    time.sleep(10)

    # Query TestMail JSON API
    api_url = f"https://api.testmail.app/api/json?apikey={TESTMAIL_API_KEY}&namespace={TESTMAIL_NAMESPACE}&tag={TEST_TAG}&pretty=true"
    logger.info(f"🔍 Fetching email from TestMail API: {api_url}")

    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "LeadOps-Swarm/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
                emails = data.get("emails", [])
                if emails:
                    logger.info(f"✅ Found {len(emails)} email(s) in TestMail inbox!")
                    latest = emails[0]
                    print("\n" + "=" * 60)
                    print("TESTMAIL LIVE DELIVERABILITY REPORT")
                    print("=" * 60)
                    print(f"Subject       : {latest.get('subject')}")
                    print(f"From          : {latest.get('from')}")
                    print(f"To            : {latest.get('to')}")
                    print(f"Date Received : {latest.get('date')}")
                    print(f"SPF Status    : {latest.get('SPF', 'Unknown')}")
                    print(f"DKIM Status   : {latest.get('dkim', 'Unknown')}")
                    print(f"Spam Score    : {latest.get('spam', 'N/A')}")
                    print(f"Spam Report   : {latest.get('spam_report', 'N/A')}")
                    print("-" * 60)
                    print("Email Text Content:\n")
                    print(latest.get("text", ""))
                    print("=" * 60)
                    return latest
                else:
                    logger.info(f"Attempt {attempt}/5: No emails received yet. Retrying in 5 seconds...")
        except Exception as err:
            logger.error(f"Error querying TestMail API (attempt {attempt}): {err}")
        time.sleep(5)

    print("⚠️ Timed out waiting for email to arrive in TestMail.app.")
    return None

if __name__ == "__main__":
    send_and_retrieve()
