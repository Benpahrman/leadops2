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

for t in ['sandboxes', 'leads', 'tickets', 'cancellation_requests', 'chat_messages']:
    try:
        with engine.begin() as conn:
            cnt = conn.execute(text(f'SELECT count(*) FROM {t}')).scalar()
            conn.execute(text(f'TRUNCATE TABLE {t} CASCADE'))
            print(f'TRUNCATED {t}: was {cnt}')
    except Exception as e:
        print(f'Error on {t}: {e}')

with engine.connect() as conn:
    l_cnt = conn.execute(text('SELECT count(*) FROM leads')).scalar()
    s_cnt = conn.execute(text('SELECT count(*) FROM sandboxes')).scalar()
print(f'FINAL_REMAINING_LEADS: {l_cnt}')
print(f'FINAL_REMAINING_SANDBOXES: {s_cnt}')
"""
    b64 = base64.b64encode(py_code.encode()).decode()
    runner = f"python3 -c import\\ base64;exec(base64.b64decode('{b64}'))"

    cmd = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe",
        "-IBm", "azure.cli",
        "containerapp", "exec",
        "--name", "aca-leadops-api-production",
        "--resource-group", "rg-omnileadfeeder-production",
        "--command", f"python3 -c \"import base64;exec(base64.b64decode('{b64}'))\""
    ]

    print("Running command on Azure Container App directly via Python...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    print("Exit code:", res.returncode)

if __name__ == "__main__":
    main()
