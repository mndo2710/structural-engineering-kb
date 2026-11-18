"""SQLite Schema v2 migration and automatic pre-migration backup (WP-1a).

Upgrades v1 SQLite databases (PRAGMA user_version < 2) to Schema v2
(PRAGMA user_version = 2) transactionally and idempotently while creating
a pre-migration backup in storage/backups/ and preserving 100% of existing
projects, calculations, inputs, results, and revisions.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


SCHEMA_VERSION = 2

V2_CALCULATIONS_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("group_id", "TEXT REFERENCES calculation_groups(group_id) ON DELETE SET NULL"),
    ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
    ("item_number", "INTEGER"),
    ("draft_inputs_json", "TEXT"),
    ("draft_updated_at", "TEXT"),
    ("last_dcr", "REAL"),
    ("last_input_hash", "TEXT"),
    ("is_deleted", "INTEGER NOT NULL DEFAULT 0"),
)

V2_REVISIONS_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("code_edition", "TEXT"),
    ("reference_manifest_sha256", "TEXT"),
    ("reference_snapshot_json", "TEXT"),
)


def _default_backup_dir() -> Path:
    root_dir = Path(__file__).resolve().parent.parent.parent
    return root_dir / "storage" / "backups"


def _utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_pre_migration_backup(
    db_path: Path,
    backup_dir: Path,
    from_version: int,
) -> Path:
    """Copy the existing SQLite database into backup_dir before Schema v2 migration."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = _utc_timestamp_compact()
    candidate = backup_dir / f"{db_path.stem}_v{from_version}_backup_{ts}.sqlite3"
    counter = 1
    while candidate.exists():
        candidate = backup_dir / f"{db_path.stem}_v{from_version}_backup_{ts}_{counter}.sqlite3"
        counter += 1

    wal_path = Path(f"{db_path}-wal")
    if wal_path.exists() and wal_path.stat().st_size > 0:
        src = sqlite3.connect(str(db_path), timeout=15.0)
        dst = sqlite3.connect(str(candidate), timeout=15.0)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
    else:
        shutil.copy2(db_path, candidate)

    return candidate


def _inspect_existing_db(db_path: Path) -> Tuple[int, List[str]]:
    """Read user_version and existing non-internal table names without creating writes."""
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    try:
        version_row = conn.execute("PRAGMA user_version;").fetchone()
        version = int(version_row[0]) if version_row else 0
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        ]
        return version, tables
    finally:
        conn.close()


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    return [row[1] for row in rows]


def _create_base_and_v2_tables(conn: sqlite3.Connection) -> None:
    """Create all v1 and v2 tables if missing (new DBs get current_revision DEFAULT 0)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            client TEXT,
            engineer TEXT,
            description TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calculation_groups (
            group_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            is_collapsed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_settings (
            project_id TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
            default_design_method TEXT NOT NULL DEFAULT 'ASD',
            code_registry_json TEXT,
            updated_at TEXT NOT NULL
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            calculation_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            module_id TEXT NOT NULL,
            title TEXT NOT NULL,
            code_edition TEXT NOT NULL,
            design_method TEXT NOT NULL,
            current_revision INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            group_id TEXT REFERENCES calculation_groups(group_id) ON DELETE SET NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            item_number INTEGER,
            draft_inputs_json TEXT,
            draft_updated_at TEXT,
            last_dcr REAL,
            last_input_hash TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calculation_inputs (
            input_id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL,
            inputs_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(calculation_id, revision_number)
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calculation_results (
            result_id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL,
            demand REAL NOT NULL,
            capacity REAL NOT NULL,
            dcr REAL NOT NULL,
            status TEXT NOT NULL,
            governing_limit_state TEXT,
            results_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(calculation_id, revision_number)
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calculation_revisions (
            revision_id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL,
            change_notes TEXT,
            created_by TEXT,
            software_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            code_edition TEXT,
            reference_manifest_sha256 TEXT,
            reference_snapshot_json TEXT,
            UNIQUE(calculation_id, revision_number)
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reference_files (
            reference_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            code TEXT,
            edition TEXT,
            sha256 TEXT,
            last_verified TEXT,
            verification_status TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            sync_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            direction TEXT NOT NULL,
            files_synced INTEGER DEFAULT 0,
            conflicts INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            details_json TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS application_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)


def _alter_missing_columns(conn: sqlite3.Connection) -> List[str]:
    """Add missing v2 columns to existing calculations and calculation_revisions tables."""
    added_columns: List[str] = []

    calc_cols = set(_get_table_columns(conn, "calculations"))
    for col_name, col_def in V2_CALCULATIONS_COLUMNS:
        if col_name not in calc_cols:
            conn.execute(f"ALTER TABLE calculations ADD COLUMN {col_name} {col_def};")
            added_columns.append(f"calculations.{col_name}")

    rev_cols = set(_get_table_columns(conn, "calculation_revisions"))
    for col_name, col_def in V2_REVISIONS_COLUMNS:
        if col_name not in rev_cols:
            conn.execute(f"ALTER TABLE calculation_revisions ADD COLUMN {col_name} {col_def};")
            added_columns.append(f"calculation_revisions.{col_name}")

    return added_columns


def _backfill_v1_calculations(conn: sqlite3.Connection) -> int:
    """Assign monotonic per-project item_number and default sort_order to v1 rows."""
    project_rows = conn.execute(
        "SELECT DISTINCT project_id FROM calculations WHERE item_number IS NULL;"
    ).fetchall()

    updated_count = 0
    for (project_id,) in project_rows:
        max_row = conn.execute(
            "SELECT COALESCE(MAX(item_number), 0) FROM calculations WHERE project_id = ?;",
            (project_id,),
        ).fetchone()
        next_num = (int(max_row[0]) if max_row else 0) + 1

        pending_rows = conn.execute(
            """
            SELECT calculation_id, sort_order
            FROM calculations
            WHERE project_id = ? AND item_number IS NULL
            ORDER BY created_at ASC, rowid ASC;
            """,
            (project_id,),
        ).fetchall()

        for calc_id, current_sort_order in pending_rows:
            conn.execute(
                """
                UPDATE calculations
                SET item_number = ?,
                    sort_order = CASE
                        WHEN sort_order = 0 OR sort_order IS NULL THEN ?
                        ELSE sort_order
                    END
                WHERE calculation_id = ?;
                """,
                (next_num, next_num, calc_id),
            )
            next_num += 1
            updated_count += 1

    return updated_count


def _backfill_project_settings(conn: sqlite3.Connection) -> None:
    """Ensure every existing project has a default project_settings record."""
    now = _utc_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO project_settings (project_id, default_design_method, code_registry_json, updated_at)
        SELECT project_id, 'ASD', NULL, COALESCE(updated_at, ?)
        FROM projects;
        """,
        (now,),
    )


def _create_v2_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_calc_project_order
        ON calculations(project_id, is_deleted, group_id, sort_order);
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_groups_project_order
        ON calculation_groups(project_id, sort_order);
    """)


def _run_migration_on_connection(
    conn: sqlite3.Connection,
    from_version: int,
    had_existing_tables: bool,
    backup_path: Optional[Path],
) -> Dict[str, Any]:
    """Execute transactional Schema v2 setup/migration on an open SQLite connection."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("BEGIN IMMEDIATE;")
    try:
        _create_base_and_v2_tables(conn)
        added_columns = _alter_missing_columns(conn)
        backfilled_calcs = _backfill_v1_calculations(conn)
        _backfill_project_settings(conn)
        _create_v2_indexes(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return {
        "migrated": had_existing_tables,
        "initialized": not had_existing_tables,
        "from_version": from_version,
        "to_version": SCHEMA_VERSION,
        "backup_path": backup_path,
        "added_columns": added_columns,
        "backfilled_calculations": backfilled_calcs,
    }


def migrate_to_v2(
    db_path: Union[str, Path],
    backup_dir: Optional[Union[str, Path]] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Ensure the SQLite database is at Schema v2 (PRAGMA user_version = 2).

    - If already at user_version >= 2, returns immediately as a no-op.
    - If an existing non-:memory: DB has user_version < 2 and existing tables/size > 0,
      copies a pre-migration backup into backup_dir (default: storage/backups/) first.
    - Runs DDL, column additions, backfills, indexes, and PRAGMA user_version = 2
      inside a single atomic transaction with rollback on error.
    """
    is_memory = str(db_path) == ":memory:"

    if is_memory:
        if conn is None:
            raise ValueError("An open connection must be provided when migrating an :memory: database.")
        version_row = conn.execute("PRAGMA user_version;").fetchone()
        current_version = int(version_row[0]) if version_row else 0
        if current_version >= SCHEMA_VERSION:
            return {
                "migrated": False,
                "initialized": False,
                "from_version": current_version,
                "to_version": current_version,
                "backup_path": None,
                "added_columns": [],
                "backfilled_calculations": 0,
            }
        existing_tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        ]
        # Temporarily ensure manual transaction control for transactional DDL
        prev_isolation = conn.isolation_level
        conn.isolation_level = None
        try:
            return _run_migration_on_connection(
                conn=conn,
                from_version=current_version,
                had_existing_tables=len(existing_tables) > 0,
                backup_path=None,
            )
        finally:
            conn.isolation_level = prev_isolation

    resolved_db = Path(db_path).resolve()
    resolved_db.parent.mkdir(parents=True, exist_ok=True)
    resolved_backup_dir = Path(backup_dir).resolve() if backup_dir is not None else _default_backup_dir()

    current_version = 0
    existing_tables: List[str] = []
    file_has_content = resolved_db.exists() and resolved_db.stat().st_size > 0
    if file_has_content:
        current_version, existing_tables = _inspect_existing_db(resolved_db)

    if current_version >= SCHEMA_VERSION:
        return {
            "migrated": False,
            "initialized": False,
            "from_version": current_version,
            "to_version": current_version,
            "backup_path": None,
            "added_columns": [],
            "backfilled_calculations": 0,
        }

    backup_path: Optional[Path] = None
    had_existing_tables = len(existing_tables) > 0
    if file_has_content and had_existing_tables:
        backup_path = create_pre_migration_backup(
            db_path=resolved_db,
            backup_dir=resolved_backup_dir,
            from_version=current_version,
        )

    mig_conn = sqlite3.connect(str(resolved_db), timeout=15.0, isolation_level=None)
    try:
        return _run_migration_on_connection(
            conn=mig_conn,
            from_version=current_version,
            had_existing_tables=had_existing_tables,
            backup_path=backup_path,
        )
    finally:
        mig_conn.close()
