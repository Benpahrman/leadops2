"""
agents.storage
~~~~~~~~~~~~~~

Durable persistence layer for LeadOps domain, portal, and sandbox state.
Provides concrete implementations for SQLite (local embedded) and PostgreSQL (Azure Flexible Server),
as well as InMemoryStorageBackend for unit testing.

Conforms to ADR-0002 Strangler Fig De-monolithization Protocol.
"""

from __future__ import annotations

from .base import StorageBackend, normalize_company_name, normalize_domain
from .memory import InMemoryStorageBackend
from .sqlite import SqliteStorageBackend
from .postgres import PostgresStorageBackend
from .factory import create_storage_backend

# Re-export domain and progress models for 100% backward compatibility
from ..domain import Lead, State
from ..progress import ProgressFeed, ProgressStatus
from ..logging_config import get_logger

logger = get_logger("storage")

__all__ = [
    "StorageBackend",
    "InMemoryStorageBackend",
    "SqliteStorageBackend",
    "PostgresStorageBackend",
    "create_storage_backend",
    "normalize_company_name",
    "normalize_domain",
    "Lead",
    "State",
    "ProgressFeed",
    "ProgressStatus",
    "logger",
]
