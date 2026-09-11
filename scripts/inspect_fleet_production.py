import base64
import subprocess

def main():
    py_code = """
import os, sqlalchemy, json
from sqlalchemy import text
from agents.storage import PostgresStorageBackend
from agents.email.config import EmailSettings
from agents.email.warmup import WarmupManager

db_url = os.environ.get('DATABASE_URL')
engine = sqlalchemy.create_engine(db_url)
with engine.connect() as conn:
    # 1. Check daily_email_quota_logs
    rows = conn.execute(text("SELECT inbox_id, sent_date, COUNT(*) FROM daily_email_quota_logs GROUP BY inbox_id, sent_date")).fetchall()
    print("=== DAILY EMAIL QUOTA LOGS ===")
    for r in rows:
        print(f"  Inbox: {r[0]}, Date: {r[1]}, Count: {r[2]}")
    
    # 2. Check total leads and count by state
    states = conn.execute(text("SELECT state, COUNT(*) FROM leads GROUP BY state")).fetchall()
    print("\n=== LEADS BY STATE ===")
    for s in states:
        print(f"  State: {s[0]}, Count: {s[1]}")

    # 3. Check inbox_accounts table if exists
    try:
        inbox_rows = conn.execute(text("SELECT inbox_id, email_address, daily_limit, is_active FROM inbox_accounts")).fetchall()
        print("\n=== INBOX_ACCOUNTS TABLE ===")
        for ir in inbox_rows:
            print(f"  {ir[0]}: {ir[1]}, limit={ir[2]}, active={ir[3]}")
    except Exception as e:
        print(f"  inbox_accounts table error: {e}")

# 4. Check WarmupManager evaluation
settings = EmailSettings.from_environment()
storage = PostgresStorageBackend(database_url=db_url)
warmup = WarmupManager(settings=settings, storage_backend=storage)

print("\n=== FLEET CAPACITY SUMMARY ===")
print(json.dumps(warmup.get_fleet_capacity_summary(), indent=2))

print("\n=== CONFIGURED OUTBOUND ACCOUNTS ===")
for acc in warmup.get_all_configured_accounts(outbound_only=True):
    sent = warmup.get_sent_count_today(acc.id)
    can_send, _, quota = warmup.can_send_today(acc.id)
    on_jitter = warmup.is_inbox_on_jitter(acc.id)
    print(f"  {acc.id} ({acc.email_address}): sent_today={sent}, daily_quota={quota}, can_send={can_send}, on_jitter={on_jitter}")

print("\n=== AVAILABLE INBOX ===")
print("  check_jitter=False:", warmup.get_available_inbox(check_jitter=False))
print("  check_jitter=True: ", warmup.get_available_inbox(check_jitter=True))
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
