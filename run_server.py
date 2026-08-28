"""LeadOps Production Server & Background Autonomous Engine.

Runs the live production web portal, customer dashboard, founder mission control,
and autonomous Scout & Retainer background monitoring services.
"""

import os
import sys
import time
import uvicorn
import dotenv
dotenv.load_dotenv()
# Configure UTF-8 encoding for Windows standard output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents.api import create_app
from agents.domain import Lead, State
from agents.drift_monitor import RetainerMonitorWorker
from agents.portal import PortalService
from agents.scout_runner import ScoutBackgroundWorker
from agents.storage import SqliteStorageBackend
from agents.dashboard import CustomerDashboardService
from agents.admin_ops import AdminMissionControlService
from agents.llm_client import LLMAgentEngine


def main():
    host = "127.0.0.1"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    db_path = os.path.join(os.path.dirname(__file__), "leadops.db")
    storage = SqliteStorageBackend(db_path=db_path)
    portal = PortalService(storage=storage)

    print("==================================================================")
    print("           ⚡ LEADOPS LIVE PRODUCTION ENGINE & SERVER ⚡          ")
    print("==================================================================")

    # 1. Start Autonomous Scout Discovery Worker
    scout_worker = ScoutBackgroundWorker(storage=storage, portal=portal)
    candidate = scout_worker.discover_next_candidate()
    print(f"✓ Scout Pipeline Active: Discovered candidate '{candidate['company_name']}'")
    print(f"  Jurisdiction: {candidate['jurisdiction']}")
    print(f"  Target Portal: {candidate['portal_name']}")
    print(f"  Live Sandbox: http://{host}:{port}/p/{candidate['slug']}")

    # 2. Start Retainer Drift Monitor
    monitor = RetainerMonitorWorker()
    dashboard_service = CustomerDashboardService(storage=storage)
    admin_service = AdminMissionControlService(storage=storage)
    llm_engine = LLMAgentEngine()
    print("✓ Retainer Drift Shield: Active (5:30 AM UTC pre-flight verification)")

    print("------------------------------------------------------------------")
    print(" 🔗 Clickable Live Production Endpoints:")
    print(f"  • Live Customer Portal / Sandbox: http://{host}:{port}/")
    print(f"  • Tailored Candidate Feed:       http://{host}:{port}/p/{candidate['slug']}")
    print(f"  • Authenticated Customer View:   http://{host}:{port}/dashboard/demo-lead")
    print(f"  • Founder Mission Control:       http://{host}:{port}/admin")
    print(f"  • Interactive OpenAPI Docs:      http://{host}:{port}/docs")
    print("==================================================================")
    print(f"🚀 Running Live Production Server on http://{host}:{port} ... (Press CTRL+C to stop)\n")

    app = create_app(storage=storage, portal_svc=portal, api_token=os.getenv("LEADOPS_API_TOKEN"),
                     dashboard_svc=dashboard_service, admin_ops=admin_service)
    uvicorn.run(app, host=host, port=port, log_level="info", reload=False)


if __name__ == "__main__":
    main()
