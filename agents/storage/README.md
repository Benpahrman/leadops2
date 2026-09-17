# 🗄️ Persistence & Storage Domain (`agents/storage`)

This package provides the durable, production-grade persistence layer for LeadOps domain entities, prospect sandboxes, ticket workflows, webhook idempotency, and deliverability audits.

It supports dual database engines:
1. **SQLite (`SqliteStorageBackend`)**: Embedded, zero-cloud storage with WAL mode, thread-local connections, and atomic transactions for local development and edge worker execution.
2. **PostgreSQL (`PostgresStorageBackend`)**: Enterprise connection-pooled engine using SQLAlchemy for Azure Database for PostgreSQL (Flexible Server).
3. **In-Memory (`InMemoryStorageBackend`)**: Isolated, fast in-memory dictionary store for deterministic unit testing.

Conforms to [ADR-0002: Strangler Fig De-monolithization Protocol](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0002-strangler-fig-modularization-protocol.md).

---

## 🏛️ Architecture & Class Diagram

```mermaid
classDiagram
    class StorageBackend {
        <<Protocol>>
        +check_prospect_deduplication(company, domain, email) tuple
        +save_lead(lead)
        +get_lead(lead_id) Lead
        +list_leads() list~Lead~
        +delete_lead(lead_id) bool
        +save_sandbox(lead_id, slug, ...)
        +get_sandbox(slug) dict
        +record_webhook_event(event_id, payload)
        +save_deliverability_audit(report)
    }

    class InMemoryStorageBackend {
        +dict leads
        +dict sandboxes
        +set webhook_events
        +record_sequence_dispatch()
    }

    class SqliteStorageBackend {
        +str db_path
        +threading.local _local
        +_init_db()
        +_init_new_tables()
        +_get_connection() sqlite3.Connection
    }

    class PostgresStorageBackend {
        +str database_url
        +Engine engine
        +_init_db()
        +execute_query()
    }

    class Factory {
        +create_storage_backend(database_url) StorageBackend
    }

    StorageBackend <|.. InMemoryStorageBackend : implements
    StorageBackend <|.. SqliteStorageBackend : implements
    StorageBackend <|.. PostgresStorageBackend : implements
    Factory ..> StorageBackend : creates
```

---

## 📦 Package Submodules

```
agents/storage/
├── __init__.py      # Re-exports all public interfaces via __all__ (Stable Facade)
├── base.py          # StorageBackend protocol, normalize_company_name, normalize_domain
├── memory.py        # InMemoryStorageBackend (isolated dictionary state for test suites)
├── sqlite.py        # SqliteStorageBackend (embedded, WAL mode, thread-local pooled connections)
├── postgres.py      # PostgresStorageBackend (Azure Flexible Server connection pooling)
├── factory.py       # create_storage_backend dynamic environment factory
└── README.md        # Living architecture documentation
```

---

## 🚀 Usage Examples

### 1. Dynamic Factory (Recommended)
```python
from agents.storage import create_storage_backend

# Automatically detects DATABASE_URL; falls back to SQLite leadops.db
storage = create_storage_backend()
lead = storage.get_lead("lead_12345")
```

### 2. Isolated Unit Testing
```python
from agents.storage import InMemoryStorageBackend
from agents.domain import Lead

test_storage = InMemoryStorageBackend()
test_storage.save_lead(Lead(lead_id="test_1", company_name="Acme Corp"))
```

### 3. Explicit SQLite or PostgreSQL
```python
from agents.storage import SqliteStorageBackend, PostgresStorageBackend

# Local embedded with WAL mode
sqlite_db = SqliteStorageBackend(db_path="leadops.db")

# Azure Cloud PostgreSQL
pg_db = PostgresStorageBackend(database_url="postgresql://user:pass@host:5432/leadops")
```

---

## ⚠️ Invariants & Concurrency Rules

1. **Thread-Safety**: `SqliteStorageBackend` isolates connections per thread using `threading.local()` to prevent SQLite concurrency deadlocks.
2. **Zero-Mock Rule**: In production runtimes, data always persists to durable PostgreSQL or SQLite; synthetic test mocks are never used outside `tests/`.
3. **Idempotency**: Webhook events and PayPal transactions must be recorded via `record_webhook_event` to prevent duplicate processing.
