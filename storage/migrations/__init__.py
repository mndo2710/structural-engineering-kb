"""Database schema migrations for SQLite project storage."""

from storage.migrations.schema_v2 import (
    SCHEMA_VERSION,
    create_pre_migration_backup,
    migrate_to_v2,
)

__all__ = [
    "SCHEMA_VERSION",
    "create_pre_migration_backup",
    "migrate_to_v2",
]
