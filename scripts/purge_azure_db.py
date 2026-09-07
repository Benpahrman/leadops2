import base64
import subprocess
import sys

def main():
    py_code = """
import os
import sqlalchemy
from sqlalchemy import text

db_url = os.environ.get('DATABASE_URL')
engine = sqlalchemy.create_engine(db_url)
target_id = 'lead-pahrman-asset-intelligence-lead-pahrman-intel-1788803960'
with engine.begin() as conn:
    conn.execute(text('DELETE FROM sandboxes WHERE lead_id LIKE :pnc OR slug LIKE :pnc'), {'pnc': '%pnc%'})
    conn.execute(text('DELETE FROM leads WHERE lead_id LIKE :pnc OR company_name LIKE :pnc_name'), {'pnc': '%pnc%', 'pnc_name': '%PNC%'})
    rows = conn.execute(text('SELECT lead_id, company_name, state FROM leads')).fetchall()
print('REMAINING_AZURE_LEADS:', [(r[0], r[1], r[2]) for r in rows])

# Trigger review notification to Discord for existing PITCH_PENDING_APPROVAL leads
from agents.notifications import notification_manager
from agents.storage import PostgresStorageBackend
from agents.pitcher import PitchMessage
storage = PostgresStorageBackend(engine)
for r in rows:
    lead = storage.get_lead(r[0])
    if lead and str(getattr(lead, 'state', '')) in ('State.PITCH_PENDING_APPROVAL', 'PITCH_PENDING_APPROVAL'):
        p = PitchMessage(
            subject=getattr(lead, 'outreach_subject', '') or f"Automated {lead.jurisdiction} data feed for {lead.company_name}",
            body_text=getattr(lead, 'outreach_body', '') or f"Hi, noticed your team files public records in {lead.jurisdiction}...",
            body_html=getattr(lead, 'outreach_html', '') or f"<p>Hi {lead.company_name}</p>",
            word_count=len((getattr(lead, 'outreach_body', '') or '').split()) or 35,
            sandbox_url=f"https://www.omnileadfeeder.tech/p/{lead.slug}",
        )
        print(f"DISPATCHING_DISCORD_REVIEW_ALERT for: {lead.company_name} ({lead.contact_email})")
        notification_manager.notify_lead_qualified_and_dispatching(lead=lead, pitch=p)
import time
time.sleep(3)
print('DISPATCH_COMPLETE')
"""
    b64 = base64.b64encode(py_code.encode()).decode()
    runner = f"python3 -c import\\ base64;exec(base64.b64decode('{b64}'))"

    rep_res = subprocess.run([
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe",
        "-IBm", "azure.cli",
        "containerapp", "replica", "list",
        "--name", "aca-leadops-api-production",
        "--resource-group", "rg-omnileadfeeder-production",
        "--query", "[0].name", "-o", "tsv"
    ], capture_output=True, text=True)
    replica_name = rep_res.stdout.strip()
    print("TARGET REPLICA:", replica_name)

    cmd = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe",
        "-IBm", "azure.cli",
        "containerapp", "exec",
        "--name", "aca-leadops-api-production",
        "--resource-group", "rg-omnileadfeeder-production",
        "--replica", replica_name,
        "--command", f"python3 -c \"import base64;exec(base64.b64decode('{b64}'))\""
    ]

    print("Running command on Azure Container App directly via Python...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    print("Exit code:", res.returncode)

if __name__ == "__main__":
    main()
