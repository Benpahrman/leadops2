import pytest

from agents.domain import Lead, PaymentEvent, State
from agents.portal import PortalService
from agents.progress import ProgressStatus
from agents.storage import InMemoryStorageBackend, SqliteStorageBackend
from agents.payments import PaymentEventProcessor


def test_sqlite_storage_lead_persistence(tmp_path):
    db_path = str(tmp_path / "test_leads.db")
    storage = SqliteStorageBackend(db_path=db_path)
    lead = Lead("lead-123", "weekly")
    
    lead.transition(State.REVIEW, "prospect approved")
    lead.select_fields(["case_number", "filing_date"])
    storage.save_lead(lead)

    # Reload from fresh storage instance
    storage_reloaded = SqliteStorageBackend(db_path=db_path)
    loaded_lead = storage_reloaded.get_lead("lead-123")
    assert loaded_lead is not None
    assert loaded_lead.lead_id == "lead-123"
    assert loaded_lead.state == State.REVIEW
    assert loaded_lead.selected_fields == ["case_number", "filing_date"]
    assert len(loaded_lead.audit_log) == 1


def test_sqlite_storage_sandbox_lifecycle(tmp_path):
    db_path = str(tmp_path / "test_sandbox.db")
    storage = SqliteStorageBackend(db_path=db_path)
    portal = PortalService(storage=storage)
    lead = Lead("lead-456", "daily")
    slug = portal.publish_sandbox(
        lead=lead,
        company_name="Acme Legal",
        rows=[{"case": "1", "date": "2026-08-27"}],
        source_url="https://court.example.gov",
    )
    portal.publish_build_progress(slug, "planner", ProgressStatus.ACTIVE, "Planning data intake")
    portal.select_fields(slug, ["case", "date"])

    # Reload portal with a new instance using the same database
    portal_reloaded = PortalService(storage=SqliteStorageBackend(db_path=db_path))
    reloaded_sandbox = portal_reloaded.get_sandbox(slug)
    assert reloaded_sandbox.slug == slug
    assert reloaded_sandbox.lead.lead_id == "lead-456"
    assert reloaded_sandbox.lead.state == State.CONVERSATIONAL_INTAKE
    assert reloaded_sandbox.rows == [{"case": "1", "date": "2026-08-27"}]
    assert len(portal_reloaded.build_progress(slug)) == 1


def test_sqlite_storage_webhook_idempotency(tmp_path):
    db_path = str(tmp_path / "test_idempotency.db")
    storage = SqliteStorageBackend(db_path=db_path)
    processor = PaymentEventProcessor(storage=storage)
    lead = Lead("lead-789", "weekly", state=State.SOW_GENERATED)

    # First event application succeeds
    assert processor.apply(lead, "evt-100", PaymentEvent.DEPOSIT_PAID) is True
    assert lead.state == State.DEPOSIT_PAID

    # Duplicate event on reloaded instance is rejected
    storage_reloaded = SqliteStorageBackend(db_path=db_path)
    processor_reloaded = PaymentEventProcessor(storage=storage_reloaded)
    assert processor_reloaded.apply(lead, "evt-100", PaymentEvent.DEPOSIT_PAID) is False


def test_sqlite_storage_backup_db(tmp_path):
    db_path = str(tmp_path / "original.db")
    backup_path = str(tmp_path / "backup.db")
    storage = SqliteStorageBackend(db_path=db_path)
    
    lead = Lead("lead-backup-test", "daily", company_name="Backup Test Inc")
    storage.save_lead(lead)
    
    # Trigger online backup
    result_path = storage.backup_db(target_path=backup_path)
    assert result_path == backup_path
    
    # Verify backup database contains the data
    backup_storage = SqliteStorageBackend(db_path=backup_path)
    loaded = backup_storage.get_lead("lead-backup-test")
    assert loaded is not None
    assert loaded.company_name == "Backup Test Inc"


def test_sqlite_storage_deposit_and_backlog_persistence(tmp_path):
    db_path = str(tmp_path / "test_pricing.db")
    storage = SqliteStorageBackend(db_path=db_path)
    lead = Lead("lead-pricing-test", "daily", company_name="Pricing Corp")
    lead.deposit_amount_usd = 99.00
    lead.unlocked_30d_backlog = True
    storage.save_lead(lead)

    # Reload from fresh storage instance
    storage_reloaded = SqliteStorageBackend(db_path=db_path)
    reloaded = storage_reloaded.get_lead("lead-pricing-test")
    assert reloaded is not None
    assert reloaded.deposit_amount_usd == 99.00
    assert reloaded.unlocked_30d_backlog is True


