import base64
import subprocess
import sys

def main():
    py_code = """
import os
import sqlalchemy
from sqlalchemy import text
import json

db_url = os.environ.get('DATABASE_URL')
print("DATABASE_URL present:", bool(db_url))
engine = sqlalchemy.create_engine(db_url)

with engine.connect() as conn:
    tables = [r[0] for r in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()]
    print("Tables in PostgreSQL:", tables)
    
    if 'leads' in tables:
        rows = conn.execute(text("SELECT lead_id, company_name, state, contact_email, outreach_subject, audit_log FROM leads ORDER BY created_at DESC")).fetchall()
        print(f"Total leads in Azure DB: {len(rows)}")
        for r in rows:
            print(f"--- Lead: {r[0]} | Company: {r[1]} | State: {r[2]} | Email: {r[3]}")
            print(f"    Subject: {r[4]}")
            try:
                audit = json.loads(r[5]) if isinstance(r[5], str) else r[5]
                print(f"    Audit ({len(audit)} entries):")
                for a in audit[-3:]:
                    print(f"      {a}")
            except Exception as ex:
                print(f"    Audit parse error: {ex}")

    if 'daily_email_quota_logs' in tables:
        logs = conn.execute(text("SELECT * FROM daily_email_quota_logs ORDER BY dispatched_at DESC LIMIT 10")).fetchall()
        print(f"Daily email quota logs ({len(logs)}):")
        for log in logs:
            print("   ", dict(log._mapping))
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

    print("Executing query on Azure replica...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n", res.stdout)
    if res.stderr:
        print("STDERR:\n", res.stderr)

if __name__ == "__main__":
    main()
