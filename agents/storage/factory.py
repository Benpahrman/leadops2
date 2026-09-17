"""Storage backend factory instantiating PostgresStorageBackend or SqliteStorageBackend."""

from __future__ import annotations

import os
from .base import StorageBackend
from .sqlite import SqliteStorageBackend
from .postgres import PostgresStorageBackend


def create_storage_backend(database_url: str | None = None) -> StorageBackend:
    """Factory creating PostgresStorageBackend when DATABASE_URL is set, else SqliteStorageBackend."""
    db_url = database_url or os.environ.get("DATABASE_URL")
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        return PostgresStorageBackend(database_url=db_url)
    return SqliteStorageBackend()
