import base64
import subprocess

def main():
    py_code = """
import os, sqlalchemy, json
from sqlalchemy import text

db_url = os.environ.get('DATABASE_URL')
engine = sqlalchemy.create_engine(db_url)
with engine.connect() as conn:
    row = conn.execute(text("SELECT lead_id, company_name, state, audit_log, contact_email FROM leads WHERE state = 'OUTREACH_SENT'")).fetchone()
    if row:
        print("OUTREACH_SENT row:", row[0], row[1], row[2], row[4])
        print("Audit:", row[3])
    else:
        print("No lead with state OUTREACH_SENT")
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
