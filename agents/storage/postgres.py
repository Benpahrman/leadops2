"""Backward-compatible facade for PostgresStorageBackend.

The implementation lives in agents/storage/postgres_pkg/.
"""

from agents.storage.postgres_pkg import PostgresStorageBackend

__all__ = ["PostgresStorageBackend"]
