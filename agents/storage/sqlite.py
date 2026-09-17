"""Backward-compatible facade for SqliteStorageBackend.

The implementation lives in agents/storage/sqlite_pkg/.
Import from this module or from agents.storage.sqlite_pkg directly.
"""

from agents.storage.sqlite_pkg import SqliteStorageBackend

__all__ = ["SqliteStorageBackend"]
