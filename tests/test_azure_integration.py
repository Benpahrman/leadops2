"""Tests for Azure cloud migration components: storage factory, blob storage, and queue broker."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.blob_storage import BlobStorageManager
from agents.domain import Lead, State
from agents.service_bus import (
    JobPayload,
    JobType,
    LocalQueueBroker,
    create_queue_broker,
)
from agents.storage import (
    PostgresStorageBackend,
    SqliteStorageBackend,
    StorageBackend,
    create_storage_backend,
)
from agents.worker import AutonomousSwarmWorker


def test_storage_factory_defaults_to_sqlite():
    with patch.dict(os.environ, {}, clear=True):
        backend = create_storage_backend()
        assert isinstance(backend, SqliteStorageBackend)


def test_storage_factory_detects_postgres_url():
    pg_url = "postgresql://leadopsadmin:secret123@psql-server.postgres.database.azure.com:5432/leadops?sslmode=require"
    with patch("sqlalchemy.create_engine") as mock_engine:
        backend = create_storage_backend(database_url=pg_url)
        assert isinstance(backend, PostgresStorageBackend)
        assert backend.database_url == pg_url
        mock_engine.assert_called_once()


def test_postgres_storage_backend_normalizes_postgres_prefix():
    legacy_url = "postgres://user:pass@host:5432/db"
    with patch("sqlalchemy.create_engine") as mock_engine:
        backend = PostgresStorageBackend(database_url=legacy_url)
        assert backend.database_url.startswith("postgresql://")


def test_blob_storage_local_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BlobStorageManager(connection_string=None, local_dir=tmpdir)
        assert not manager.is_cloud_enabled

        # Test upload_text and download_text
        url = manager.upload_text("Hello Azure Blob", "traces/01_trace.txt")
        assert Path(url).exists()
        content = manager.download_text("traces/01_trace.txt")
        assert content == "Hello Azure Blob"

        # Test upload_bytes and download_bytes
        data = b"\x00\x01\x02\x03"
        manager.upload_bytes(data, "dom_dumps/page.bin")
        assert manager.download_bytes("dom_dumps/page.bin") == data
        assert manager.exists("dom_dumps/page.bin")
        assert not manager.exists("nonexistent.bin")


def test_queue_broker_local_publish_and_receive():
    broker = LocalQueueBroker()
    payload = JobPayload(
        job_type=JobType.SCOUT_EVALUATION,
        lead_id="test_lead_123",
        slug="harris-county-tx",
        params={"source_url": "https://example.com/records"},
    )

    job_id = broker.publish_job("leadops-jobs", payload)
    assert job_id == payload.job_id

    received = broker.receive_jobs("leadops-jobs", max_messages=5)
    assert len(received) == 1
    assert received[0].job_id == payload.job_id
    assert received[0].job_type == JobType.SCOUT_EVALUATION
    assert received[0].lead_id == "test_lead_123"


def test_job_payload_serialization_roundtrip():
    payload = JobPayload(
        job_type=JobType.BUILD_PLAN_EXECUTION,
        lead_id="lead_abc",
        slug="bexar-civil",
        params={"retry_count": 2, "priority": "high"},
    )
    json_str = payload.to_json()
    reconstructed = JobPayload.from_json(json_str)

    assert reconstructed.job_id == payload.job_id
    assert reconstructed.job_type == JobType.BUILD_PLAN_EXECUTION
    assert reconstructed.lead_id == "lead_abc"
    assert reconstructed.params["retry_count"] == 2


def test_autonomous_worker_job_routing():
    worker = AutonomousSwarmWorker(queue_name="test-queue")
    worker.storage = MagicMock()
    worker.broker = MagicMock()

    # Verify handler dispatch doesn't crash on unrecognized job
    worker.process_job(JobPayload(job_type=JobType.DRIFT_CHECK, lead_id="lead_1"))
