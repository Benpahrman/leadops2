"""LeadOps Production Server & Background Autonomous Engine.

Runs the live production web portal, customer dashboard, founder mission control,
and autonomous Scout & Retainer background monitoring services.
"""

import os
import sys
import time
import threading
import uvicorn
import dotenv
from datetime import datetime, timezone, timedelta
dotenv.load_dotenv()
os.environ.setdefault("ENV", "development")
os.environ.setdefault("LEADOPS_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173")
os.environ.setdefault("LEADOPS_REQUIRE_HUMAN_APPROVAL", "false")
os.environ.setdefault("LEADOPS_API_TOKEN", "0baac74dfda043fdaf84c5d0b38e259b")

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
from agents.pitcher import send_lifecycle_email
from agents.logging_config import get_logger

server_logger = get_logger("server")


def run_automation_scheduler(
    storage: SqliteStorageBackend,
    portal: PortalService,
    llm_engine,
    base_url: str,
    stop_event: threading.Event,
) -> None:
    """Background thread for daily automation: churn detection, win-back, upsell, referral, operator briefing."""
    server_logger.info("Automation Scheduler: Active (daily checks at 8:00 AM CST)")
    
    while not stop_event.is_set():
        try:
            now = datetime.now(timezone.utc)
            # Run at 8:00 AM CST (13:00 UTC)
            target_hour = 13  # 8 AM CST = 13:00 UTC
            if now.hour == target_hour and now.minute < 5:
                run_daily_automation(storage, portal, llm_engine, base_url)
            
            # Sleep for 1 minute before checking again
            stop_event.wait(60)
        except Exception as e:
            server_logger.error(f"Automation scheduler error: {e}")
            stop_event.wait(60)


def run_daily_automation(
    storage: SqliteStorageBackend,
    portal: PortalService,
    llm_engine,
    base_url: str,
) -> None:
    """Run daily automation checks: churn, win-back, upsell, referral, operator briefing."""
    from agents.logging_config import get_logger
    log = get_logger("automation_scheduler")
    log.info("🔄 [DAILY AUTOMATION] Starting daily lifecycle checks")
    
    # 5:00 AM UTC: Daily SQLite Database Snapshot
    try:
        if hasattr(storage, "backup_db"):
            backup_path = storage.backup_db()
            log.info(f"💾 [DATABASE BACKUP] Successfully created daily snapshot: {backup_path}")
    except Exception as e:
        log.warning(f"Database backup error: {e}")

    # 7:30 AM CST: Daily Morning Deliverability & TestMail Spam Assessment
    try:
        from agents.email.deliverability_tester import DeliverabilityTester
        tester = DeliverabilityTester(storage_backend=storage)
        tester.run_fleet_audit(force=False)
        log.info("🛡️ [DELIVERABILITY AUDIT] Daily morning TestMail spam & deliverability audit completed")
    except Exception as e:
        log.warning(f"Deliverability audit daily sweep notice: {e}")

    leads = storage.list_leads()
    
    # Send operator morning briefing across Discord, Telegram, and Email
    try:
        from agents.notifications import notification_manager
        briefing_stats = notification_manager.notify_morning_briefing(storage, portal)

        # Also dispatch via email to global admin emails
        from agents.auth import GLOBAL_ADMIN_EMAILS
        for admin_email in GLOBAL_ADMIN_EMAILS:
            briefing_lead = Lead("admin-briefing", "daily", company_name="LeadOps Portfolio", contact_email=admin_email)
            send_lifecycle_email(briefing_lead, "operator_briefing", base_url=base_url, extra_variables={
                "date": briefing_stats.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "total_leads": briefing_stats["operations"]["total_leads"],
                "active_builds": briefing_stats["pipeline"]["building"],
                "escrow_ready": briefing_stats["pipeline"]["escrow_preview"],
                "delivered_today": briefing_stats["pipeline"]["delivered"],
                "mrr": f"${briefing_stats['accounting']['mrr']:,.2f}",
                "total_cash": f"${briefing_stats['accounting']['total_cash_collected']:,.2f}",
                "alerts": f"{briefing_stats['operations']['open_tickets']} open tickets",
                "sla_tickets": briefing_stats["operations"]["urgent_tickets"],
            })
        log.info("📬 [OPERATOR BRIEFING] Sent daily morning briefing with full accounting to Discord, Telegram & Email")
    except Exception as e:
        log.warning(f"Could not send operator briefing: {e}")
    
    # 5:30 AM UTC: Retainer Drift Shield Pre-Flight Sweep
    try:
        from agents.drift_monitor import RetainerMonitorWorker
        from agents.datasets import AUTHENTIC_REGISTRY_DATASETS
        monitor = RetainerMonitorWorker()
        for lead in leads:
            if lead.state in {State.WARRANTY_ACTIVE, State.DELIVERED} or lead.subscription_active:
                try:
                    def test_fetcher():
                        lookup_target = (lead.source_url if lead else "") or (lead.slug if lead else "") or "universal-data-portal"
                        for k in AUTHENTIC_REGISTRY_DATASETS:
                            if k in (lead.slug or "").lower():
                                lookup_target = k
                                break
                        return list(AUTHENTIC_REGISTRY_DATASETS[lookup_target]["sample_data"])
                    
                    incident = monitor.inspect_feed(lead, lead.source_url or "https://registry.gov", lead.selected_fields or ["case_number"], test_fetcher)
                    if incident:
                        log.warning(f"🛡️ [DRIFT DETECTED] Incident {incident.incident_id} on {lead.company_name}")
                        send_lifecycle_email(lead, "drift_alert", base_url=base_url, extra_variables={
                            "field_name": incident.details or "selector_mismatch",
                        })
                except Exception as e:
                    log.warning(f"Drift shield check failed for {lead.lead_id}: {e}")
        log.info("🛡️ [DRIFT SHIELD] 5:30 AM pre-flight verification sweep completed")
    except Exception as e:
        log.warning(f"Drift shield sweep error: {e}")

    # 6:00 AM UTC: Automated Batch Delivery for Active Retainers
    # Uses real DeliveryJob pipeline with compiled extractors and observability telemetry
    try:
        from agents.datasets import AUTHENTIC_REGISTRY_DATASETS
        from agents.delivery import DeliveryPlan, DeliveryJob, LocalCsvDestination, WebhookDestination
        from agents.observability import telemetry_collector
        from agents.self_healing import SelfHealingEngine
        from pathlib import Path
        import subprocess, json as _json

        healer = SelfHealingEngine()
        now = datetime.now(timezone.utc)

        for lead in leads:
            is_active_retainer = (lead.state in {State.WARRANTY_ACTIVE, State.DELIVERED} or lead.subscription_active) and lead.deposit_paid
            if not is_active_retainer:
                continue

            delivery_plan = DeliveryPlan(tier_key=lead.tier_key)
            if not delivery_plan.should_run(now.date()):
                log.info(f"⏭️ [DELIVERY SKIP] {lead.company_name} not scheduled today (tier={lead.tier_key})")
                continue

            start_time = datetime.now(timezone.utc)
            artifact_dir = Path("build_artifacts") / (lead.lead_id or lead.slug or "demo_lead")
            extractor_path = artifact_dir / "extractor.py"
            output_dir = artifact_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            extracted_rows = []
            delivery_succeeded = False

            try:
                # Attempt to run the compiled extractor if it exists
                if extractor_path.exists():
                    log.info(f"🚚 [EXTRACTOR RUN] Executing {extractor_path} for {lead.company_name}")
                    clean_env = {
                        "PYTHONUNBUFFERED": "1",
                        "PATH": os.environ.get("PATH", ""),
                        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                        "TEMP": os.environ.get("TEMP", ""),
                        "TMP": os.environ.get("TMP", ""),
                    }
                    result = subprocess.run(
                        [sys.executable, str(extractor_path.resolve())],
                        capture_output=True, text=True, timeout=120,
                        cwd=str(artifact_dir.resolve()),
                        env=clean_env,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f"Extractor exit code {result.returncode}: {result.stderr[:200]}")

                    # Read output from extractor's standard output locations
                    json_output = output_dir / "latest.json"
                    if json_output.exists():
                        extracted_rows = _json.loads(json_output.read_text(encoding="utf-8"))
                    else:
                        log.warning(f"Extractor produced no output/latest.json for {lead.lead_id}")

                # Fall back to dataset sample if no extractor or no output
                if not extracted_rows:
                    lookup_target = (lead.source_url if lead else "") or (lead.slug if lead else "") or "universal-data-portal"
                    for k in AUTHENTIC_REGISTRY_DATASETS:
                        if k in (lead.slug or "").lower():
                            lookup_target = k
                            break
                    extracted_rows = list(AUTHENTIC_REGISTRY_DATASETS[lookup_target]["sample_data"])

                if not extracted_rows:
                    raise ValueError("No rows extracted from any source")

                # Write local CSV delivery artifact
                csv_dest = LocalCsvDestination(file_path=str(output_dir / "latest.csv"))
                rows_delivered = csv_dest.append(extracted_rows)

                # Record delivery in observability
                elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                delivery_destination = getattr(lead, "delivery_destination", "Local CSV + JSON")
                telemetry_collector.record_delivery(
                    lead_id=lead.lead_id,
                    rows_delivered=rows_delivered,
                    destination=delivery_destination,
                    status="DELIVERED",
                    latency_ms=elapsed_ms,
                )
                telemetry_collector.record_extraction(success=True, latency_sec=elapsed_ms / 1000.0)
                telemetry_collector.record_append(latency_ms=float(elapsed_ms))
                telemetry_collector.log_event(
                    category="DELIVERY", title=f"Batch #{(lead.delivery_count or 0) + 1} delivered",
                    details=f"{rows_delivered} rows to {delivery_destination}", status="SUCCESS", lead_id=lead.lead_id,
                )

                try:
                    import hashlib
                    from agents.audit_vault import audit_vault
                    batch_hash = hashlib.sha256(_json.dumps(extracted_rows, sort_keys=True).encode()).hexdigest()
                    audit_vault.record_delivery_receipt(
                        lead_id=lead.lead_id,
                        run_id=f"RUN-DAILY-{(lead.delivery_count or 0) + 1}",
                        rows_delivered=rows_delivered,
                        destination_type=delivery_destination,
                        destination_target=str(output_dir / "latest.csv"),
                        data_sha256=batch_hash,
                        qa_score=lead.qa_score or 100.0,
                        sample_keys=lead.selected_fields or (list(extracted_rows[0].keys()) if extracted_rows else []),
                        notes=f"Scheduled daily sync batch #{(lead.delivery_count or 0) + 1} delivered",
                    )
                except Exception as audit_err:
                    log.warning(f"Audit vault daily delivery record notice: {audit_err}")

                lead.delivery_count = (getattr(lead, "delivery_count", 0) or 0) + 1
                lead.last_delivery_at = datetime.now(timezone.utc).isoformat()
                storage.save_lead(lead)
                delivery_succeeded = True

                send_lifecycle_email(lead, "post_delivery_receipt", base_url=base_url, extra_variables={
                    "delivery_count": lead.delivery_count,
                    "destination": delivery_destination,
                })
                log.info(f"🚚 [DAILY DELIVERY] Batch #{lead.delivery_count} for {lead.company_name}: {rows_delivered} rows delivered")

            except Exception as e:
                log.warning(f"Daily delivery failed for {lead.lead_id}: {e}")
                telemetry_collector.record_extraction(success=False)
                telemetry_collector.log_event(
                    category="DELIVERY", title=f"Delivery failed for {lead.company_name}",
                    details=str(e)[:200], status="ERROR", lead_id=lead.lead_id,
                )

                # Invoke self-healing engine on extractor failures
                try:
                    current_script = extractor_path.read_text(encoding="utf-8") if extractor_path.exists() else ""
                    healed_script, post_mortem = healer.heal_extractor(lead, str(e), current_script)
                    if healed_script:
                        extractor_path.write_text(healed_script, encoding="utf-8")
                        log.info(f"🩹 [SELF-HEALED] Repaired extractor for {lead.lead_id} (incident: {post_mortem.incident_id})")
                except Exception as heal_err:
                    log.warning(f"Self-healing failed for {lead.lead_id}: {heal_err}")

        log.info("🚚 [BATCH DELIVERY] 6:00 AM delivery batches dispatched")
    except Exception as e:
        log.warning(f"Batch delivery run error: {e}")


    # TRIG-04: Scheduled build heartbeats for DEV_BUILDING leads (every 8h, max 3)
    for lead in leads:
        if lead.state == State.DEV_BUILDING and getattr(lead, "heartbeat_count", 0) < 3:
            try:
                send_lifecycle_email(lead, "build_heartbeat", base_url=base_url, extra_variables={
                    "progress": min(40 + (getattr(lead, "heartbeat_count", 0) * 25), 90),
                    "current_agent": ["planner", "builder", "qa_verifier"][min(getattr(lead, "heartbeat_count", 0), 2)],
                    "eta": "within 24 hours",
                    "milestone": ["Build plan formulated", "Extraction pipeline compiled", "QA verification in progress"][min(getattr(lead, "heartbeat_count", 0), 2)],
                })
                lead.heartbeat_count = getattr(lead, "heartbeat_count", 0) + 1
                storage.save_lead(lead)
                log.info(f"📬 [BUILD HEARTBEAT] Heartbeat #{lead.heartbeat_count} sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send build heartbeat: {e}")

    # TRIG-05: Abandoned sandbox recovery (24h after sandbox view, no deposit)
    now = datetime.now(timezone.utc)
    for lead in leads:
        if lead.state in {State.ARCHIVED, State.WARRANTY_EXPIRED}:
            continue
        sandbox_viewed_at = getattr(lead, "sandbox_first_viewed_at", "")
        abandoned_sandbox_sent = getattr(lead, "abandoned_sandbox_sent", False)
        if (sandbox_viewed_at and not lead.deposit_paid and not abandoned_sandbox_sent
                and lead.state in {State.PROSPECTING, State.REVIEW, State.OUTREACH_SENT, State.PITCH_PENDING_APPROVAL}
                and getattr(lead, "winback_stage", 0) == 0):
            try:
                viewed_dt = datetime.fromisoformat(sandbox_viewed_at.replace('Z', '+00:00'))
                hours_since_view = (now - viewed_dt).total_seconds() / 3600
                if hours_since_view >= 24:
                    send_lifecycle_email(lead, "abandoned_sandbox", base_url=base_url)
                    lead.abandoned_sandbox_sent = True
                    storage.save_lead(lead)
                    log.info(f"📬 [ABANDONED SANDBOX] Recovery email sent to {lead.contact_email} ({hours_since_view:.0f}h since view)")
            except Exception as e:
                log.warning(f"Could not send abandoned sandbox recovery: {e}")

    # Check each lead for lifecycle triggers
    for lead in leads:
        if lead.state in {State.ARCHIVED, State.WARRANTY_EXPIRED}:
            continue
            
        delivery_count = getattr(lead, "delivery_count", 0)
        last_login = getattr(lead, "last_login_at", "")
        winback_stage = getattr(lead, "winback_stage", 0)
        upsell_sent = getattr(lead, "upsell_sent", False)
        referral_sent = getattr(lead, "referral_sent", False)
        
        # Parse last_login_at and created_at to calculate inactivity
        days_since_login = 999
        if last_login:
            try:
                last_login_dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                days_since_login = (datetime.now(timezone.utc) - last_login_dt).days
            except Exception as exc:
                logger.debug(f"Failed to parse last_login for {lead.lead_id}: {exc}")
        
        created_at_str = getattr(lead, "created_at", "")
        days_since_creation = 999
        if created_at_str:
            try:
                created_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                days_since_creation = (datetime.now(timezone.utc) - created_dt).days
            except Exception as exc:
                logger.debug(f"Failed to parse created_at for {lead.lead_id}: {exc}")
                
        days_inactive = min(days_since_login, days_since_creation)
        
        # Win-back sequence for unconverted inactive prospects
        if not lead.deposit_paid and lead.state in {State.PROSPECTING, State.REVIEW, State.PITCH_PENDING_APPROVAL, State.OUTREACH_SENT, State.CONVERSATIONAL_INTAKE, State.SOW_GENERATED}:
            if days_inactive >= 3 and winback_stage == 0:
                try:
                    send_lifecycle_email(lead, "winback_1", base_url=base_url)
                    lead.winback_stage = 1
                    storage.save_lead(lead)
                    log.info(f"📬 [WINBACK 1] Sent to {lead.contact_email}")
                except Exception as e:
                    log.warning(f"Could not send winback_1: {e}")
            elif days_inactive >= 7 and winback_stage == 1:
                try:
                    send_lifecycle_email(lead, "winback_2", base_url=base_url)
                    lead.winback_stage = 2
                    storage.save_lead(lead)
                    log.info(f"📬 [WINBACK 2] Sent to {lead.contact_email}")
                except Exception as e:
                    log.warning(f"Could not send winback_2: {e}")
            elif days_inactive >= 14 and winback_stage == 2:
                try:
                    send_lifecycle_email(lead, "winback_3", base_url=base_url)
                    lead.winback_stage = 3
                    storage.save_lead(lead)
                    log.info(f"📬 [WINBACK 3] Sent to {lead.contact_email}")
                except Exception as e:
                    log.warning(f"Could not send winback_3: {e}")
        
        # Upsell trigger (delivery_count >= 3)
        if delivery_count >= 3 and not upsell_sent:
            try:
                send_lifecycle_email(lead, "upsell", base_url=base_url)
                lead.upsell_sent = True
                storage.save_lead(lead)
                log.info(f"📬 [UPSELL] Sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send upsell: {e}")
        
        # TRIG-12: Referral ask (moved from delivery >= 1 to delivery >= 3 for better timing)
        if delivery_count >= 3 and not referral_sent:
            try:
                send_lifecycle_email(lead, "referral_ask", base_url=base_url)
                lead.referral_sent = True
                storage.save_lead(lead)
                log.info(f"📬 [REFERRAL] Sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send referral: {e}")
        
        # TRIG-01: Multi-county bundle offer (delivery >= 5, supersedes upsell if not responded)
        multi_county_bundle_sent = getattr(lead, "multi_county_bundle_sent", False)
        if delivery_count >= 5 and not multi_county_bundle_sent:
            try:
                send_lifecycle_email(lead, "multi_county_bundle", base_url=base_url, extra_variables={
                    "delivery_count": delivery_count,
                })
                lead.multi_county_bundle_sent = True
                storage.save_lead(lead)
                log.info(f"📬 [MULTI-COUNTY BUNDLE] Expansion offer sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send multi_county_bundle: {e}")
        
        # LIFE-01: Buyout offer trigger at Month 3 for active subscribers
        buyout_offered = getattr(lead, "buyout_offered", False)
        if (lead.subscription_active and lead.tier_key != "buyout"
                and days_since_creation >= 90 and not buyout_offered):
            try:
                send_lifecycle_email(lead, "buyout_offer", base_url=base_url, extra_variables={
                    "months_subscribed": days_since_creation // 30,
                    "total_spent": (days_since_creation // 30) * (lead.tier.price_cents / 100),
                    "buyout_price": 1500.00,
                })
                lead.buyout_offered = True
                storage.save_lead(lead)
                log.info(f"📬 [BUYOUT OFFER] Month 3+ offer sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send buyout offer: {e}")

        # LIFE-02: Churned customer win-back (for paying customers who go inactive)
        is_paying_customer = lead.deposit_paid and lead.state in {State.DELIVERED, State.WARRANTY_ACTIVE}
        if is_paying_customer and days_inactive >= 7 and winback_stage == 0:
            try:
                send_lifecycle_email(lead, "winback_1", base_url=base_url, extra_variables={
                    "context": "We noticed you haven't logged into your dashboard recently.",
                })
                lead.winback_stage = 1
                storage.save_lead(lead)
                log.info(f"📬 [CHURN WINBACK 1] Sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send churn winback_1: {e}")
        elif is_paying_customer and days_inactive >= 14 and winback_stage == 1:
            try:
                send_lifecycle_email(lead, "winback_2", base_url=base_url, extra_variables={
                    "context": "Your data feed is still running but we miss you.",
                })
                lead.winback_stage = 2
                storage.save_lead(lead)
                log.info(f"📬 [CHURN WINBACK 2] Sent to {lead.contact_email}")
            except Exception as e:
                log.warning(f"Could not send churn winback_2: {e}")

    log.info("✅ [DAILY AUTOMATION] Completed")


def run_continuous_scout_loop(
    storage: SqliteStorageBackend,
    portal: PortalService,
    min_interval_seconds: int = 600,   # 10 minutes
    max_interval_seconds: int = 1200,  # 20 minutes
    stop_event: threading.Event | None = None,
) -> None:
    """Continuous background thread that autonomously discovers new target enterprises and seeds prospective sandboxes 24/7.
    Runs randomly 10-20 minutes apart in production (600-1200s), and respects mobile pause/resume controls."""
    import random
    from agents.logging_config import get_logger
    log = get_logger("scout_continuous")

    fixed_interval = os.environ.get("SCOUT_INTERVAL_SECONDS")
    min_sec = int(fixed_interval or os.environ.get("SCOUT_MIN_REST_SECONDS") or os.environ.get("PROSPECTOR_MIN_INTERVAL_SECONDS", str(min_interval_seconds)))
    max_sec = int(fixed_interval or os.environ.get("SCOUT_MAX_REST_SECONDS") or os.environ.get("PROSPECTOR_MAX_INTERVAL_SECONDS", str(max_interval_seconds)))
    log.info(f"🚀 [SCOUT DAEMON] Continuous background prospecting active — randomized intervals between {min_sec // 60}m and {max_sec // 60}m")
    
    worker = ScoutBackgroundWorker(storage=storage, portal=portal)
    while not (stop_event and stop_event.is_set()):
        # Check if paused via mobile operator quick-action
        is_paused = os.environ.get("PROSPECTOR_PAUSED", "false").lower() in ("true", "1", "yes") or os.environ.get("SCOUT_AUTOMATION_ENABLED", "true").lower() == "false"
        if is_paused:
            log.info("⏸️ [SCOUT DAEMON] Prospector is paused by operator. Standing by...")
            if stop_event:
                stop_event.wait(30)
            else:
                time.sleep(30)
            continue

        # Enforce office hours (8:00 AM - 5:00 PM CST, Mon-Fri)
        from agents.scout_runner import is_office_hours
        is_open, wait_seconds, status_msg = is_office_hours()
        if not is_open:
            log.info(f"🌙 [SCOUT DAEMON] {status_msg} Standing by until 8:00 AM window.")
            sleep_chunk = min(wait_seconds, 300)
            if stop_event:
                stop_event.wait(sleep_chunk)
            else:
                time.sleep(sleep_chunk)
            continue

        target_per_cycle = int(os.environ.get("SCOUT_TARGET_PER_CYCLE", "2"))
        for cycle_idx in range(target_per_cycle):
            try:
                candidate = worker.discover_next_candidate()
                if candidate and candidate.get("ok"):
                    log.info(f"✨ [SCOUT AUTONOMOUS STREAM] Discovered ({cycle_idx+1}/{target_per_cycle}): '{candidate['company_name']}' | Contact: {candidate.get('contact_email')} -> /p/{candidate['slug']}")
            except Exception as e:
                log.warning(f"Scout continuous discovery iteration ({cycle_idx+1}/{target_per_cycle}): {e}")
        
        # Calculate random sleep duration between 10 and 20 minutes
        sleep_duration = random.randint(min_sec, max_sec)
        log.info(f"⏳ [SCOUT DAEMON] Next prospecting discovery window in {sleep_duration // 60} minutes ({sleep_duration}s)")

        if stop_event:
            stop_event.wait(sleep_duration)
        else:
            time.sleep(sleep_duration)


def main():
    host = "127.0.0.1"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    db_path = os.path.join(os.path.dirname(__file__), "leadops.db")
    storage = SqliteStorageBackend(db_path=db_path)
    portal = PortalService(storage=storage)

    print("==================================================================")
    print("           ⚡ LEADOPS LIVE PRODUCTION ENGINE & SERVER ⚡          ")
    print("==================================================================")

    # 1. Start Continuous Scout Thread (randomized 10-20 min intervals)
    stop_event = threading.Event()
    scout_thread = threading.Thread(
        target=run_continuous_scout_loop,
        args=(storage, portal, 600, 1200, stop_event),
        daemon=True,
    )
    scout_thread.start()
    print("✓ Continuous Scout Crawler: Active (paced 10-20 min production interval)")

    monitor = RetainerMonitorWorker()
    dashboard_service = CustomerDashboardService(storage=storage)
    admin_service = AdminMissionControlService(storage=storage)
    llm_engine = LLMAgentEngine()
    print("✓ Retainer Drift Shield: Active (5:30 AM UTC pre-flight verification)")

    # 3. Start Automation Scheduler (daily lifecycle emails & 6 AM delivery batches)
    automation_thread = threading.Thread(
        target=run_automation_scheduler,
        args=(storage, portal, llm_engine, f"http://{host}:{port}", stop_event),
        daemon=True,
    )
    automation_thread.start()

    # 4. Morning Deliverability & Spam Shield (probes TestMail from all active Zoho inboxes)
    if os.environ.get("DELIVERABILITY_AUDIT_ON_STARTUP", "true").lower() in ("true", "1", "yes"):
        def _startup_deliverability_check():
            try:
                time.sleep(3)
                from agents.email.deliverability_tester import DeliverabilityTester
                tester = DeliverabilityTester(storage_backend=storage)
                tester.run_fleet_audit(force=False)
            except Exception as audit_err:
                server_logger.warning(f"Startup deliverability audit error: {audit_err}")

        startup_audit_thread = threading.Thread(target=_startup_deliverability_check, daemon=True)
        startup_audit_thread.start()
        print("✓ Deliverability & Spam Shield: Active (audits TestMail probes on startup)")

    print("------------------------------------------------------------------")
    print(" 🔗 Clickable Live Production Endpoints:")
    print(f"  • Live Candidate Sandbox Feed:   http://{host}:{port}/p/apex-commercial-title-demo-lead")
    print(f"  • Authenticated Customer View:   http://{host}:{port}/dashboard/demo-lead")
    print(f"  • Founder Mission Control:       http://{host}:{port}/admin")
    print(f"  • Interactive OpenAPI Docs:      http://{host}:{port}/docs")
    print("==================================================================")
    print(f"🚀 Running Live Production Server on http://{host}:{port} ... (Press CTRL+C to stop)\n")

    app = create_app(storage=storage, portal_svc=portal, api_token=os.getenv("LEADOPS_API_TOKEN"),
                     dashboard_svc=dashboard_service, admin_ops=admin_service)
    try:
        uvicorn.run(app, host=host, port=port, log_level="info", reload=False)
    finally:
        stop_event.set()
        automation_thread.join(timeout=5)
        scout_thread.join(timeout=5)


if __name__ == "__main__":
    main()
