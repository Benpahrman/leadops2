import base64
import subprocess

def main():
    py_code = """
import os
import sqlalchemy
from sqlalchemy import text
from agents.storage import PostgresStorageBackend
from agents.domain import State
from agents.pitcher import PitcherService, PitchMessage
from agents.email.quality_gate import OutreachQualityGatekeeper

db_url = os.environ.get('DATABASE_URL')
storage = PostgresStorageBackend(database_url=db_url)
leads = storage.list_leads()

pending_leads = [l for l in leads if l.state == State.PITCH_PENDING_APPROVAL]
print(f"Total pending leads: {len(pending_leads)}")

gatekeeper = OutreachQualityGatekeeper()

for lead in pending_leads[:3]:
    print(f"\\n--- Testing Quality Gate on Lead: {lead.lead_id} ({lead.company_name})")
    print(f"    Email: {lead.contact_email} | Website: {lead.website or lead.target_url}")
    pitch = PitchMessage(
        subject=lead.outreach_subject or "Sample Data Feed",
        body_text=lead.outreach_body or "Sample body text",
        body_html=lead.outreach_html or "<p>Sample</p>",
        sandbox_url=f"https://www.omnileadfeeder.tech/p/{lead.slug}",
        word_count=len((lead.outreach_body or "").split()),
    )
    try:
        res = gatekeeper.evaluate(lead=lead, pitch=pitch, notify_on_pass=False)
        print(f"    Result Passed: {res.passed}")
        if not res.passed:
            print(f"    Gate Failed: {res.gate_failed}")
            print(f"    Reasons: {res.reasons}")
        else:
            print(f"    Gate Metrics: {res.metrics.get('deliverability_status')}")
    except Exception as e:
        print(f"    Evaluation Exception: {type(e).__name__}: {e}")
"""
    b64 = base64.b64encode(py_code.encode()).decode()

    rep_res = subprocess.run([
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe",
        "-IBm", "azure.cli",
        "containerapp", "replica", "list",
        "--name", "aca-leadops-api-production",
        "--resource-group", "rg-omnileadfeeder-production",
        "--query", "[0].name", "-o", "tsv"
    ], capture_output=True, text=True)
    replica_name = rep_res.stdout.strip()

    cmd = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe",
        "-IBm", "azure.cli",
        "containerapp", "exec",
        "--name", "aca-leadops-api-production",
        "--resource-group", "rg-omnileadfeeder-production",
        "--replica", replica_name,
        "--command", f"python3 -c \"import base64;exec(base64.b64decode('{b64}'))\""
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n", res.stdout)
    if res.stderr:
        print("STDERR:\n", res.stderr)

if __name__ == "__main__":
    main()
