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
    conn.execute(text('DELETE FROM sandboxes WHERE lead_id = :lid OR slug LIKE :pat'), {'lid': target_id, 'pat': '%pahrman%'})
    conn.execute(text('DELETE FROM leads WHERE lead_id = :lid OR lead_id LIKE :pat'), {'lid': target_id, 'pat': '%pahrman%'})
    rows = conn.execute(text('SELECT lead_id, company_name, state FROM leads')).fetchall()
print('DELETED_PAHRMAN. REMAINING_AZURE_LEADS:', [(r[0], r[1], r[2]) for r in rows])
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
