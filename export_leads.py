"""LeadOps Export Utility: Extract scouted leads, candidate evaluations, and orchestrator data to spreadsheet (CSV)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DOMAINS = {
    "messages.cash.app",
    "notifications.acorns.com",
    "news.mistplay.com",
    "news.temuemail.com",
    "dummy.com",
    "microsoft.com",
}

TEST_COMPANIES = {
    "Alex | OmniLeadFeeder",
    "Olfmailer",
    "Messages",
    "Notifications",
    "News",
}


def get_db_connection():
    """Connect to SQLite database or PostgreSQL if configured."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(db_url)
        return conn, "postgres"

    db_path = os.environ.get("LEADOPS_DB_PATH", "leadops.db")
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def export_leads_to_csv(output_path: str = "scout_leads_export.csv", include_test_data: bool = False) -> str:
    """Export all scouted commercial B2B leads from the database into a clean CSV spreadsheet."""
    conn, engine = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM leads ORDER BY created_at DESC"
        rows = cur.execute(query).fetchall()

        fieldnames = [
            "company_name",
            "contact_name",
            "contact_role",
            "contact_email",
            "contact_phone",
            "decision_maker_linkedin",
            "website",
            "niche",
            "jurisdiction",
            "city",
            "state_code",
            "county",
            "target_portal_name",
            "source_url",
            "discovery_channel",
            "filing_case_number",
            "automation_opportunity_score",
            "deliverability_score",
            "deliverability_status",
            "email_provider",
            "lifecycle_state",
            "deposit_paid",
            "final_paid",
            "subscription_active",
            "tier_key",
            "lead_id",
            "slug",
            "sandbox_url",
            "created_at",
            "updated_at",
        ]

        base_portal_url = os.environ.get("LEADOPS_PORTAL_URL", "http://localhost:5173")

        exported_count = 0
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for r in rows:
                row_dict = dict(r)
                email = (row_dict.get("contact_email") or "").lower()
                domain = email.split("@")[1] if "@" in email else ""
                company = (row_dict.get("company_name") or "").strip()

                # Filter out development test inbox records unless explicitly requested
                if not include_test_data:
                    if domain in TEST_DOMAINS or company in TEST_COMPANIES:
                        continue

                # Parse research JSON field for enriched discovery data
                research = {}
                if row_dict.get("research"):
                    try:
                        research = json.loads(row_dict["research"])
                    except Exception:
                        pass

                slug = row_dict.get("slug") or row_dict.get("lead_id", "")
                sandbox_url = f"{base_portal_url}/sandbox/{slug}" if slug else ""

                row = {
                    "company_name": company,
                    "contact_name": row_dict.get("contact_name") or research.get("decision_maker_name", ""),
                    "contact_role": row_dict.get("contact_role") or research.get("decision_maker_role", ""),
                    "contact_email": row_dict.get("contact_email", ""),
                    "contact_phone": row_dict.get("contact_phone") or research.get("verified_phone", ""),
                    "decision_maker_linkedin": row_dict.get("decision_maker_linkedin") or research.get("linkedin_url", ""),
                    "website": row_dict.get("website", ""),
                    "niche": row_dict.get("niche", ""),
                    "jurisdiction": row_dict.get("jurisdiction", ""),
                    "city": row_dict.get("city", ""),
                    "state_code": row_dict.get("state_code", ""),
                    "county": row_dict.get("county", ""),
                    "target_portal_name": row_dict.get("target_portal_name", ""),
                    "source_url": row_dict.get("source_url", ""),
                    "discovery_channel": row_dict.get("discovery_channel") or research.get("discovery_channel", "CATALOG_SEARCH"),
                    "filing_case_number": row_dict.get("filing_case_number") or research.get("filing_case_number", ""),
                    "automation_opportunity_score": row_dict.get("automation_opportunity_score", 75),
                    "deliverability_score": row_dict.get("deliverability_score", 95),
                    "deliverability_status": row_dict.get("deliverability_status", "DELIVERABLE"),
                    "email_provider": row_dict.get("email_provider", "google"),
                    "lifecycle_state": row_dict.get("state", "REVIEW"),
                    "deposit_paid": bool(row_dict.get("deposit_paid")),
                    "final_paid": bool(row_dict.get("final_paid")),
                    "subscription_active": bool(row_dict.get("subscription_active")),
                    "tier_key": row_dict.get("tier_key", "daily"),
                    "lead_id": row_dict.get("lead_id", ""),
                    "slug": slug,
                    "sandbox_url": sandbox_url,
                    "created_at": row_dict.get("created_at", ""),
                    "updated_at": row_dict.get("updated_at", ""),
                }
                writer.writerow(row)
                exported_count += 1

        print(f" Successfully exported {exported_count} clean commercial B2B leads to '{os.path.abspath(output_path)}'")
        return output_path
    finally:
        conn.close()


def export_orchestrator_to_csv(output_path: str = "national_orchestrator_jurisdictions.csv") -> str:
    """Export all 185 county jurisdictions & lead discoveries from National County Orchestrator."""
    state_file = "data/national_county_orchestrator_state.json"
    if not os.path.exists(state_file):
        print("No national county orchestrator state file found.")
        return ""

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = data.get("jurisdiction_stats", {})
    rows = []
    for key, item in stats.items():
        rows.append({
            "state": item.get("state", ""),
            "county": item.get("county", ""),
            "leads_discovered": item.get("leads_discovered", 0),
            "visited_count": item.get("visited_count", 0),
            "last_visited_at": item.get("last_visited_at", ""),
        })

    rows.sort(key=lambda x: (x["state"], x["county"]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["state", "county", "leads_discovered", "visited_count", "last_visited_at"])
        writer.writeheader()
        writer.writerows(rows)

    print(f" Successfully exported {len(rows)} county jurisdictions to '{os.path.abspath(output_path)}'")
    return output_path


def export_candidate_evaluations_to_csv(output_path: str = "candidate_evaluations_export.csv") -> str:
    """Export evaluated candidate audit trail records into a CSV spreadsheet."""
    conn, engine = get_db_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM candidate_evaluations ORDER BY evaluated_at DESC").fetchall()

        fieldnames = [
            "id",
            "company_name",
            "channel",
            "contact_email",
            "status",
            "reason",
            "jurisdiction",
            "lead_id",
            "evaluated_at",
        ]

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))

        print(f" Successfully exported {len(rows)} candidate evaluations to '{os.path.abspath(output_path)}'")
        return output_path
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export LeadOps scout leads or evaluations to CSV spreadsheet.")
    parser.add_argument("--output", "-o", default="scout_leads_export.csv", help="Output CSV path (default: scout_leads_export.csv)")
    parser.add_argument("--type", "-t", choices=["leads", "orchestrator", "evaluations", "all"], default="leads", help="Data type to export")
    parser.add_argument("--include-test", action="store_true", help="Include internal test inbox records (Cash App, Temu, Acorns)")

    args = parser.parse_args()

    if args.type in ("leads", "all"):
        leads_file = args.output if args.type == "leads" else "scout_leads_export.csv"
        export_leads_to_csv(output_path=leads_file, include_test_data=args.include_test)

    if args.type in ("orchestrator", "all"):
        orch_file = args.output if args.type == "orchestrator" else "national_orchestrator_jurisdictions.csv"
        export_orchestrator_to_csv(output_path=orch_file)

    if args.type in ("evaluations", "all"):
        evals_file = args.output if args.type == "evaluations" else "candidate_evaluations_export.csv"
        export_candidate_evaluations_to_csv(output_path=evals_file)
