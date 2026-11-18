"""SQLite Project & Revision Repository per SAD v1.1 Section 9 (Schema v2).

Implements structured local storage for projects, project settings,
calculation groups, ordered calculation items, draft autosaves,
immutable revisions with provenance snapshots, reference files, and sync history.
"""

from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from core.common.calculation_result import CalculationResult, CalculationStatus, DesignMethod
from storage.migrations.schema_v2 import SCHEMA_VERSION, migrate_to_v2


def _json_default(obj: Any) -> Any:
    """Serialize dataclass or Enum objects nested inside trace/result payloads."""
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "value"):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class ProjectRepository:
    """Manages SQLite Schema v2 storage for structural engineering projects and calculation runs."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        backup_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        root_dir = Path(__file__).resolve().parent.parent.parent
        self._is_memory = False
        self._memory_conn: Optional[sqlite3.Connection] = None

        if db_path is None:
            self.db_path = root_dir / "storage" / "projects" / "structural_app.sqlite3"
        elif str(db_path) == ":memory:":
            self._is_memory = True
            self.db_path = Path(":memory:")
            self._memory_conn = sqlite3.connect(":memory:", timeout=15.0)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            self.db_path = Path(db_path).resolve()

        if backup_dir is None:
            self.backup_dir = root_dir / "storage" / "backups"
        else:
            self.backup_dir = Path(backup_dir).resolve()

        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.last_migration_result: Optional[Dict[str, Any]] = None
        self.last_backup_path: Optional[Path] = None
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Yield a configured SQLite connection, closing non-memory connections on exit."""
        if self._is_memory:
            assert self._memory_conn is not None
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
            yield self._memory_conn
            return

        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def close(self) -> None:
        """Close persistent in-memory connection if open."""
        if self._is_memory and self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None

    def _init_db(self) -> None:
        """Initialize or migrate the SQLite database to Schema v2."""
        if self._is_memory:
            result = migrate_to_v2(":memory:", conn=self._memory_conn)
        else:
            result = migrate_to_v2(self.db_path, backup_dir=self.backup_dir)
        self.last_migration_result = result
        self.last_backup_path = result.get("backup_path")

    def get_schema_version(self) -> int:
        """Return the current SQLite PRAGMA user_version."""
        with self._get_connection() as conn:
            row = conn.execute("PRAGMA user_version;").fetchone()
            return int(row[0]) if row else 0

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_design_method(design_method: Union[str, DesignMethod]) -> str:
        raw = design_method.value if isinstance(design_method, DesignMethod) else str(design_method).strip().upper()
        if raw not in ("ASD", "LRFD"):
            raise ValueError(f"Unsupported design method '{design_method}'. Expected 'ASD' or 'LRFD'.")
        return raw

    @staticmethod
    def _normalize_status(status: Union[str, CalculationStatus]) -> str:
        return status.value if isinstance(status, CalculationStatus) else str(status)

    @staticmethod
    def _serialize_json_or_none(value: Optional[Union[str, Dict[str, Any], List[Any]]]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)

    @staticmethod
    def _row_to_project_settings(row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        raw_registry = data.get("code_registry_json")
        if raw_registry:
            try:
                data["code_registry"] = json.loads(raw_registry)
            except json.JSONDecodeError:
                data["code_registry"] = None
        else:
            data["code_registry"] = None
        return data

    @staticmethod
    def _row_to_group(row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["is_collapsed"] = bool(data.get("is_collapsed", 0))
        return data

    @staticmethod
    def _row_to_calculation(row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        item_num = data.get("item_number")
        data["display_code"] = f"C-{int(item_num):02d}" if item_num is not None else None
        raw_draft = data.get("draft_inputs_json")
        if raw_draft:
            try:
                data["draft_inputs"] = json.loads(raw_draft)
            except json.JSONDecodeError:
                data["draft_inputs"] = {}
        else:
            data["draft_inputs"] = {}
        data["is_deleted"] = bool(data.get("is_deleted", 0))
        return data

    @staticmethod
    def _ensure_project_exists(cursor: sqlite3.Cursor, project_id: str) -> sqlite3.Row:
        cursor.execute("SELECT * FROM projects WHERE project_id = ?;", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Project '{project_id}' not found.")
        return row

    @staticmethod
    def _ensure_group_in_project(cursor: sqlite3.Cursor, group_id: str, project_id: str) -> sqlite3.Row:
        cursor.execute("SELECT * FROM calculation_groups WHERE group_id = ?;", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Calculation group '{group_id}' not found.")
        if row["project_id"] != project_id:
            raise ValueError(
                f"Calculation group '{group_id}' belongs to project '{row['project_id']}', not '{project_id}'."
            )
        return row

    @staticmethod
    def _list_bucket_item_ids(
        cursor: sqlite3.Cursor,
        project_id: str,
        group_id: Optional[str],
    ) -> List[str]:
        if group_id is None:
            cursor.execute(
                """
                SELECT calculation_id
                FROM calculations
                WHERE project_id = ? AND is_deleted = 0 AND group_id IS NULL
                ORDER BY sort_order ASC, item_number ASC, created_at ASC, rowid ASC;
                """,
                (project_id,),
            )
        else:
            cursor.execute(
                """
                SELECT calculation_id
                FROM calculations
                WHERE project_id = ? AND is_deleted = 0 AND group_id = ?
                ORDER BY sort_order ASC, item_number ASC, created_at ASC, rowid ASC;
                """,
                (project_id, group_id),
            )
        return [row["calculation_id"] for row in cursor.fetchall()]

    @staticmethod
    def _next_sort_order_in_bucket(
        cursor: sqlite3.Cursor,
        project_id: str,
        group_id: Optional[str],
    ) -> int:
        if group_id is None:
            cursor.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM calculations
                WHERE project_id = ? AND is_deleted = 0 AND group_id IS NULL;
                """,
                (project_id,),
            )
        else:
            cursor.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0)
                FROM calculations
                WHERE project_id = ? AND is_deleted = 0 AND group_id = ?;
                """,
                (project_id, group_id),
            )
        row = cursor.fetchone()
        return (int(row[0]) if row else 0) + 1

    # --------------------------------------------------------------------------
    # Project CRUD & Project Settings
    # --------------------------------------------------------------------------
    def create_project(
        self,
        name: str,
        code: Optional[str] = None,
        client: str = "",
        engineer: str = "",
        description: str = "",
        project_id: Optional[str] = None,
        default_design_method: Union[str, DesignMethod] = "ASD",
        code_registry_json: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a new project record and initialize default project_settings."""
        p_id = project_id or str(uuid.uuid4())
        now = self._now_iso()
        p_code = code or f"PRJ-{p_id[:8].upper()}"
        method_str = self._normalize_design_method(default_design_method)
        registry_str = self._serialize_json_or_none(code_registry_json)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    """
                    INSERT INTO projects (
                        project_id, name, code, client, engineer, description,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?);
                    """,
                    (p_id, name, p_code, client, engineer, description, now, now),
                )
                cursor.execute(
                    """
                    INSERT INTO project_settings (
                        project_id, default_design_method, code_registry_json, updated_at
                    ) VALUES (?, ?, ?, ?);
                    """,
                    (p_id, method_str, registry_str, now),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_project(p_id)  # type: ignore

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project by project_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE project_id = ?;", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_projects(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all projects."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM projects WHERE status = 'ACTIVE' ORDER BY updated_at DESC;")
            else:
                cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC;")
            return [dict(r) for r in cursor.fetchall()]

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Update project fields."""
        allowed_fields = {"name", "code", "client", "engineer", "description", "status"}
        set_clauses = []
        values = []
        for k, v in updates.items():
            if k in allowed_fields:
                set_clauses.append(f"{k} = ?")
                values.append(v)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        values.append(self._now_iso())
        values.append(project_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE projects SET {', '.join(set_clauses)} WHERE project_id = ?;", tuple(values))
            conn.commit()
            return cursor.rowcount > 0

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all associated calculations/groups/settings via CASCADE."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE project_id = ?;", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_project_settings(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project settings (returning defaults if project exists without a row)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_settings WHERE project_id = ?;", (project_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_project_settings(row)

            cursor.execute("SELECT updated_at FROM projects WHERE project_id = ?;", (project_id,))
            prj = cursor.fetchone()
            if not prj:
                return None
            return {
                "project_id": project_id,
                "default_design_method": "ASD",
                "code_registry_json": None,
                "code_registry": None,
                "updated_at": prj["updated_at"],
            }

    def upsert_project_settings(
        self,
        project_id: str,
        default_design_method: Union[str, DesignMethod] = "ASD",
        code_registry_json: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Insert or update default design method and effective code registry for a project."""
        method_str = self._normalize_design_method(default_design_method)
        registry_str = self._serialize_json_or_none(code_registry_json)
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                self._ensure_project_exists(cursor, project_id)
                cursor.execute(
                    """
                    INSERT INTO project_settings (
                        project_id, default_design_method, code_registry_json, updated_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        default_design_method = excluded.default_design_method,
                        code_registry_json = excluded.code_registry_json,
                        updated_at = excluded.updated_at;
                    """,
                    (project_id, method_str, registry_str, now),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_project_settings(project_id)  # type: ignore

    # --------------------------------------------------------------------------
    # Calculation Groups (WP-1b)
    # --------------------------------------------------------------------------
    def create_group(
        self,
        project_id: str,
        name: str,
        sort_order: Optional[int] = None,
        group_id: Optional[str] = None,
        is_collapsed: bool = False,
    ) -> Dict[str, Any]:
        """Create a calculation group within a project."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Group name must not be empty.")

        g_id = group_id or str(uuid.uuid4())
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                self._ensure_project_exists(cursor, project_id)
                if sort_order is None:
                    cursor.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) FROM calculation_groups WHERE project_id = ?;",
                        (project_id,),
                    )
                    order_val = int(cursor.fetchone()[0]) + 1
                else:
                    order_val = int(sort_order)

                cursor.execute(
                    """
                    INSERT INTO calculation_groups (
                        group_id, project_id, name, sort_order, is_collapsed, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (g_id, project_id, clean_name, order_val, 1 if is_collapsed else 0, now, now),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_group(g_id)  # type: ignore

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single calculation group by group_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculation_groups WHERE group_id = ?;", (group_id,))
            row = cursor.fetchone()
            return self._row_to_group(row) if row else None

    def list_groups(self, project_id: str) -> List[Dict[str, Any]]:
        """List all calculation groups for a project ordered by sort_order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM calculation_groups
                WHERE project_id = ?
                ORDER BY sort_order ASC, created_at ASC, rowid ASC;
                """,
                (project_id,),
            )
            return [self._row_to_group(r) for r in cursor.fetchall()]

    def rename_group(self, group_id: str, name: str) -> Dict[str, Any]:
        """Rename a calculation group."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Group name must not be empty.")
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("SELECT project_id FROM calculation_groups WHERE group_id = ?;", (group_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation group '{group_id}' not found.")

                cursor.execute(
                    "UPDATE calculation_groups SET name = ?, updated_at = ? WHERE group_id = ?;",
                    (clean_name, now, group_id),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, row["project_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_group(group_id)  # type: ignore

    def set_group_collapsed(self, group_id: str, is_collapsed: bool) -> Dict[str, Any]:
        """Persist expanded/collapsed state for a calculation group."""
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM calculation_groups WHERE group_id = ?;", (group_id,))
            if not cursor.fetchone():
                raise ValueError(f"Calculation group '{group_id}' not found.")
            cursor.execute(
                "UPDATE calculation_groups SET is_collapsed = ?, updated_at = ? WHERE group_id = ?;",
                (1 if is_collapsed else 0, now, group_id),
            )
            conn.commit()

        return self.get_group(group_id)  # type: ignore

    def move_group(self, group_id: str, new_index: int) -> List[Dict[str, Any]]:
        """Atomically reorder a calculation group to 0-based position new_index within its project."""
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("SELECT project_id FROM calculation_groups WHERE group_id = ?;", (group_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation group '{group_id}' not found.")
                project_id = row["project_id"]

                cursor.execute(
                    """
                    SELECT group_id FROM calculation_groups
                    WHERE project_id = ?
                    ORDER BY sort_order ASC, created_at ASC, rowid ASC;
                    """,
                    (project_id,),
                )
                group_ids = [r["group_id"] for r in cursor.fetchall() if r["group_id"] != group_id]
                clamped_idx = max(0, min(int(new_index), len(group_ids)))
                group_ids.insert(clamped_idx, group_id)

                for order_idx, g_id in enumerate(group_ids, start=1):
                    cursor.execute(
                        "UPDATE calculation_groups SET sort_order = ?, updated_at = ? WHERE group_id = ?;",
                        (order_idx, now, g_id),
                    )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.list_groups(project_id)

    def delete_group(self, group_id: str) -> bool:
        """Delete a group, moving its member items to ungrouped while preserving item order."""
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("SELECT project_id FROM calculation_groups WHERE group_id = ?;", (group_id,))
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False
                project_id = row["project_id"]

                # Append items in this group to the end of ungrouped items cleanly before group removal
                ungrouped_max = self._next_sort_order_in_bucket(cursor, project_id, None) - 1
                group_item_ids = self._list_bucket_item_ids(cursor, project_id, group_id)
                for offset, c_id in enumerate(group_item_ids, start=1):
                    cursor.execute(
                        "UPDATE calculations SET group_id = NULL, sort_order = ?, updated_at = ? WHERE calculation_id = ?;",
                        (ungrouped_max + offset, now, c_id),
                    )

                cursor.execute("DELETE FROM calculation_groups WHERE group_id = ?;", (group_id,))

                # Re-normalize remaining group sort_orders
                cursor.execute(
                    """
                    SELECT group_id FROM calculation_groups
                    WHERE project_id = ?
                    ORDER BY sort_order ASC, created_at ASC, rowid ASC;
                    """,
                    (project_id,),
                )
                for order_idx, rem_gid in enumerate((r["group_id"] for r in cursor.fetchall()), start=1):
                    cursor.execute(
                        "UPDATE calculation_groups SET sort_order = ? WHERE group_id = ?;",
                        (order_idx, rem_gid),
                    )

                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    # --------------------------------------------------------------------------
    # Calculation Item & Revision Management (SAD v1.1 Sec. 9 & WP-1b)
    # --------------------------------------------------------------------------
    def create_calculation(
        self,
        project_id: str,
        module_id: str,
        title: str,
        code_edition: str,
        design_method: Optional[Union[str, DesignMethod]] = None,
        calculation_id: Optional[str] = None,
        group_id: Optional[str] = None,
        draft_inputs: Optional[Dict[str, Any]] = None,
        sort_order: Optional[int] = None,
        status: Union[str, CalculationStatus] = CalculationStatus.INCOMPLETE,
    ) -> Dict[str, Any]:
        """Create a new calculation item within a project with monotonic item_number."""
        c_id = calculation_id or str(uuid.uuid4())
        status_str = self._normalize_status(status)
        now = self._now_iso()
        draft_json = json.dumps(draft_inputs) if draft_inputs is not None else None
        draft_ts = now if draft_inputs is not None else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                self._ensure_project_exists(cursor, project_id)
                if design_method is None:
                    cursor.execute(
                        "SELECT default_design_method FROM project_settings WHERE project_id = ?;",
                        (project_id,),
                    )
                    ps_row = cursor.fetchone()
                    method_str = self._normalize_design_method(ps_row["default_design_method"] if ps_row else "ASD")
                else:
                    method_str = self._normalize_design_method(design_method)

                if group_id is not None:
                    self._ensure_group_in_project(cursor, group_id, project_id)

                # Monotonic per-project item_number: never reused even after soft delete
                cursor.execute(
                    "SELECT COALESCE(MAX(item_number), 0) FROM calculations WHERE project_id = ?;",
                    (project_id,),
                )
                next_item_num = int(cursor.fetchone()[0]) + 1

                if sort_order is None:
                    order_val = self._next_sort_order_in_bucket(cursor, project_id, group_id)
                else:
                    order_val = int(sort_order)

                cursor.execute(
                    """
                    INSERT INTO calculations (
                        calculation_id, project_id, module_id, title, code_edition,
                        design_method, current_revision, status, created_at, updated_at,
                        group_id, sort_order, item_number, draft_inputs_json,
                        draft_updated_at, last_dcr, last_input_hash, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0);
                    """,
                    (
                        c_id,
                        project_id,
                        module_id,
                        title,
                        code_edition,
                        method_str,
                        status_str,
                        now,
                        now,
                        group_id,
                        order_val,
                        next_item_num,
                        draft_json,
                        draft_ts,
                    ),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_calculation(c_id)  # type: ignore

    def update_draft(
        self,
        calculation_id: str,
        draft_inputs: Dict[str, Any],
        design_method: Optional[Union[str, DesignMethod]] = None,
        code_edition: Optional[str] = None,
        status: Optional[Union[str, CalculationStatus]] = None,
    ) -> Dict[str, Any]:
        """Autosave draft inputs (and optional method/code/status) without creating a revision."""
        now = self._now_iso()
        draft_json = json.dumps(draft_inputs)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    "SELECT project_id, is_deleted FROM calculations WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation '{calculation_id}' not found.")
                if row["is_deleted"]:
                    raise ValueError(f"Calculation '{calculation_id}' is soft-deleted.")

                set_clauses = ["draft_inputs_json = ?", "draft_updated_at = ?", "updated_at = ?"]
                params: List[Any] = [draft_json, now, now]

                if design_method is not None:
                    set_clauses.append("design_method = ?")
                    params.append(self._normalize_design_method(design_method))
                if code_edition is not None:
                    set_clauses.append("code_edition = ?")
                    params.append(code_edition)
                if status is not None:
                    set_clauses.append("status = ?")
                    params.append(self._normalize_status(status))

                params.append(calculation_id)
                cursor.execute(
                    f"UPDATE calculations SET {', '.join(set_clauses)} WHERE calculation_id = ?;",
                    tuple(params),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, row["project_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_calculation(calculation_id)  # type: ignore

    def update_run_state(
        self,
        calculation_id: str,
        last_dcr: Optional[float],
        status: Union[str, CalculationStatus],
        last_input_hash: Optional[str],
    ) -> Dict[str, Any]:
        """Update cached in-memory run metadata on calculations WITHOUT creating a revision."""
        now = self._now_iso()
        status_str = self._normalize_status(status)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    "SELECT project_id, is_deleted FROM calculations WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation '{calculation_id}' not found.")
                if row["is_deleted"]:
                    raise ValueError(f"Calculation '{calculation_id}' is soft-deleted.")

                cursor.execute(
                    """
                    UPDATE calculations
                    SET last_dcr = ?, status = ?, last_input_hash = ?, updated_at = ?
                    WHERE calculation_id = ?;
                    """,
                    (last_dcr, status_str, last_input_hash, now, calculation_id),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, row["project_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_calculation(calculation_id)  # type: ignore

    def duplicate_calculation(
        self,
        source_calculation_id: str,
        new_title: Optional[str] = None,
        group_id: Optional[str] = None,
        calculation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Duplicate a calculation item's settings and draft inputs (or latest revision inputs
        if draft is empty) into a new item with status INCOMPLETE, current_revision=0,
        monotonic item_number, and zero copied revisions.
        """
        new_id = calculation_id or str(uuid.uuid4())
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("SELECT * FROM calculations WHERE calculation_id = ?;", (source_calculation_id,))
                source = cursor.fetchone()
                if not source:
                    raise ValueError(f"Source calculation '{source_calculation_id}' not found.")
                if source["is_deleted"]:
                    raise ValueError(f"Source calculation '{source_calculation_id}' is soft-deleted.")

                project_id = source["project_id"]
                if group_id is None:
                    target_group_id = source["group_id"]
                elif group_id == "":
                    target_group_id = None
                else:
                    target_group_id = group_id

                if target_group_id is not None:
                    self._ensure_group_in_project(cursor, target_group_id, project_id)

                title_val = new_title.strip() if new_title is not None else f"{source['title']} (Copy)"
                if not title_val:
                    raise ValueError("Duplicate calculation title must not be empty.")

                # Resolve draft inputs: prefer non-empty draft, else latest revision inputs
                draft_json: Optional[str] = source["draft_inputs_json"]
                is_draft_empty = True
                if draft_json is not None and draft_json.strip() != "":
                    try:
                        parsed = json.loads(draft_json)
                        is_draft_empty = parsed == {} or parsed is None
                    except json.JSONDecodeError:
                        is_draft_empty = False

                if is_draft_empty:
                    cursor.execute(
                        """
                        SELECT inputs_json
                        FROM calculation_inputs
                        WHERE calculation_id = ?
                        ORDER BY revision_number DESC
                        LIMIT 1;
                        """,
                        (source_calculation_id,),
                    )
                    rev_inp = cursor.fetchone()
                    if rev_inp and rev_inp["inputs_json"]:
                        draft_json = rev_inp["inputs_json"]

                draft_ts = now if draft_json is not None else None

                cursor.execute(
                    "SELECT COALESCE(MAX(item_number), 0) FROM calculations WHERE project_id = ?;",
                    (project_id,),
                )
                next_item_num = int(cursor.fetchone()[0]) + 1
                next_sort_order = self._next_sort_order_in_bucket(cursor, project_id, target_group_id)

                cursor.execute(
                    """
                    INSERT INTO calculations (
                        calculation_id, project_id, module_id, title, code_edition,
                        design_method, current_revision, status, created_at, updated_at,
                        group_id, sort_order, item_number, draft_inputs_json,
                        draft_updated_at, last_dcr, last_input_hash, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0);
                    """,
                    (
                        new_id,
                        project_id,
                        source["module_id"],
                        title_val,
                        source["code_edition"],
                        source["design_method"],
                        CalculationStatus.INCOMPLETE.value,
                        now,
                        now,
                        target_group_id,
                        next_sort_order,
                        next_item_num,
                        draft_json,
                        draft_ts,
                    ),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_calculation(new_id)  # type: ignore

    def rename_calculation(self, calculation_id: str, new_title: str) -> Dict[str, Any]:
        """Rename a calculation item."""
        clean_title = new_title.strip()
        if not clean_title:
            raise ValueError("Calculation title must not be empty.")
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    "SELECT project_id, is_deleted FROM calculations WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation '{calculation_id}' not found.")
                if row["is_deleted"]:
                    raise ValueError(f"Calculation '{calculation_id}' is soft-deleted.")

                cursor.execute(
                    "UPDATE calculations SET title = ?, updated_at = ? WHERE calculation_id = ?;",
                    (clean_title, now, calculation_id),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, row["project_id"]))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.get_calculation(calculation_id)  # type: ignore

    def move_calculation(
        self,
        calculation_id: str,
        target_group_id: Optional[str],
        new_index: int,
    ) -> List[Dict[str, Any]]:
        """
        Atomically move/reorder a calculation item into target_group_id (or None for ungrouped)
        at 0-based position new_index, re-indexing sort_order deterministically.
        """
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    "SELECT project_id, group_id, is_deleted FROM calculations WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation '{calculation_id}' not found.")
                if row["is_deleted"]:
                    raise ValueError(f"Calculation '{calculation_id}' is soft-deleted.")

                project_id = row["project_id"]
                source_group_id = row["group_id"]

                if target_group_id is not None:
                    self._ensure_group_in_project(cursor, target_group_id, project_id)

                target_ids = [
                    cid
                    for cid in self._list_bucket_item_ids(cursor, project_id, target_group_id)
                    if cid != calculation_id
                ]
                clamped_idx = max(0, min(int(new_index), len(target_ids)))
                target_ids.insert(clamped_idx, calculation_id)

                for order_idx, cid in enumerate(target_ids, start=1):
                    cursor.execute(
                        """
                        UPDATE calculations
                        SET group_id = ?, sort_order = ?, updated_at = ?
                        WHERE calculation_id = ?;
                        """,
                        (target_group_id, order_idx, now, cid),
                    )

                if source_group_id != target_group_id:
                    source_ids = [
                        cid
                        for cid in self._list_bucket_item_ids(cursor, project_id, source_group_id)
                        if cid != calculation_id
                    ]
                    for order_idx, cid in enumerate(source_ids, start=1):
                        cursor.execute(
                            "UPDATE calculations SET sort_order = ?, updated_at = ? WHERE calculation_id = ?;",
                            (order_idx, now, cid),
                        )

                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return self.list_calculations_for_project(project_id)

    def soft_delete_calculation(self, calculation_id: str) -> bool:
        """
        Soft-delete a calculation item (is_deleted = 1) while preserving all rows
        in calculation_inputs, calculation_results, and calculation_revisions.
        """
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("SELECT project_id FROM calculations WHERE calculation_id = ?;", (calculation_id,))
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False

                cursor.execute(
                    "UPDATE calculations SET is_deleted = 1, updated_at = ? WHERE calculation_id = ?;",
                    (now, calculation_id),
                )
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, row["project_id"]))
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    def save_calculation_run(
        self,
        calculation_id: str,
        calc_result: CalculationResult,
        change_notes: str = "Initial calculation run",
        engineer: str = "",
        reference_manifest_sha256: Optional[str] = None,
        reference_snapshot: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        input_hash: Optional[str] = None,
    ) -> int:
        """
        Record a calculation execution as an immutable revision per SAD Section 9.4.
        Atomically saves inputs, results, and revision log (with provenance snapshot),
        then increments current_revision. Returns new revision number.
        """
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute(
                    "SELECT current_revision, project_id, is_deleted FROM calculations WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Calculation '{calculation_id}' not found.")
                if row["is_deleted"]:
                    raise ValueError(f"Calculation '{calculation_id}' is soft-deleted.")

                cursor.execute(
                    "SELECT COALESCE(MAX(revision_number), 0) FROM calculation_revisions WHERE calculation_id = ?;",
                    (calculation_id,),
                )
                max_existing_rev = int(cursor.fetchone()[0])
                new_revision = max_existing_rev + 1
                project_id = row["project_id"]

                # 1. Store immutable input snapshot
                cursor.execute(
                    """
                    INSERT INTO calculation_inputs (
                        input_id, calculation_id, revision_number, inputs_json, created_at
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (str(uuid.uuid4()), calculation_id, new_revision, json.dumps(calc_result.input_parameters), now),
                )

                # 2. Serialize full calculation result
                gov_str = calc_result.governing_limit_state.name if calc_result.governing_limit_state else ""
                res_dict: Dict[str, Any] = {
                    "calculation_id": calc_result.calculation_id,
                    "module_id": calc_result.module_id,
                    "code_edition": calc_result.code_edition,
                    "design_method": calc_result.design_method.value,
                    "demand": calc_result.demand,
                    "capacity": calc_result.capacity,
                    "dcr": calc_result.dcr,
                    "status": calc_result.status.value,
                    "assumptions": calc_result.assumptions,
                    "intermediate_results": calc_result.intermediate_results,
                    "limit_states": [
                        {
                            "step_id": ls.step_id,
                            "name": ls.name,
                            "code_clause": ls.code_clause,
                            "equation_latex": ls.equation_latex,
                            "substitution_str": ls.substitution_str,
                            "demand": ls.demand,
                            "capacity": ls.capacity,
                            "units": ls.units,
                            "dcr": ls.dcr,
                            "status": ls.status.value,
                            "notes": ls.notes,
                        }
                        for ls in calc_result.limit_states
                    ],
                    "reference_files": calc_result.reference_files,
                    "software_version": calc_result.software_version,
                    "warnings": calc_result.warnings,
                }
                trace_val = getattr(calc_result, "trace", None)
                if trace_val:
                    res_dict["trace"] = [
                        asdict(step) if is_dataclass(step) else step for step in trace_val
                    ]

                cursor.execute(
                    """
                    INSERT INTO calculation_results (
                        result_id, calculation_id, revision_number, demand, capacity,
                        dcr, status, governing_limit_state, results_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        str(uuid.uuid4()),
                        calculation_id,
                        new_revision,
                        calc_result.demand,
                        calc_result.capacity,
                        calc_result.dcr,
                        calc_result.status.value,
                        gov_str,
                        json.dumps(res_dict, default=_json_default),
                        now,
                    ),
                )

                # 3. Store revision metadata & provenance snapshot
                snapshot_json = self._serialize_json_or_none(reference_snapshot)
                if snapshot_json is None and calc_result.reference_files:
                    snapshot_json = json.dumps({"reference_files": list(calc_result.reference_files)})

                cursor.execute(
                    """
                    INSERT INTO calculation_revisions (
                        revision_id, calculation_id, revision_number, change_notes,
                        created_by, software_version, created_at,
                        code_edition, reference_manifest_sha256, reference_snapshot_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        str(uuid.uuid4()),
                        calculation_id,
                        new_revision,
                        change_notes,
                        engineer,
                        calc_result.software_version,
                        now,
                        calc_result.code_edition,
                        reference_manifest_sha256,
                        snapshot_json,
                    ),
                )

                # 4. Update parent calculation record
                if input_hash is not None:
                    cursor.execute(
                        """
                        UPDATE calculations
                        SET current_revision = ?, status = ?, last_dcr = ?, last_input_hash = ?, updated_at = ?
                        WHERE calculation_id = ?;
                        """,
                        (new_revision, calc_result.status.value, calc_result.dcr, input_hash, now, calculation_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE calculations
                        SET current_revision = ?, status = ?, last_dcr = ?, updated_at = ?
                        WHERE calculation_id = ?;
                        """,
                        (new_revision, calc_result.status.value, calc_result.dcr, now, calculation_id),
                    )

                # 5. Touch project updated_at
                cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return new_revision

    def get_calculation(self, calculation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve calculation record (including Schema v2 metadata and computed display_code)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.*, g.name AS group_name
                FROM calculations c
                LEFT JOIN calculation_groups g ON c.group_id = g.group_id
                WHERE c.calculation_id = ?;
                """,
                (calculation_id,),
            )
            row = cursor.fetchone()
            return self._row_to_calculation(row) if row else None

    def list_calculations_for_project(
        self,
        project_id: str,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """List calculations for a project ordered by group sort_order, item sort_order, and item_number."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            deleted_filter = "" if include_deleted else "AND c.is_deleted = 0"
            cursor.execute(
                f"""
                SELECT c.*, g.name AS group_name
                FROM calculations c
                LEFT JOIN calculation_groups g ON c.group_id = g.group_id
                WHERE c.project_id = ? {deleted_filter}
                ORDER BY
                    CASE WHEN c.group_id IS NULL THEN 1 ELSE 0 END ASC,
                    COALESCE(g.sort_order, 2147483647) ASC,
                    c.sort_order ASC,
                    c.item_number ASC,
                    c.created_at ASC,
                    c.rowid ASC;
                """,
                (project_id,),
            )
            return [self._row_to_calculation(r) for r in cursor.fetchall()]

    def get_calculation_revisions(self, calculation_id: str) -> List[Dict[str, Any]]:
        """Get immutable revision history for a calculation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM calculation_revisions
                WHERE calculation_id = ?
                ORDER BY revision_number ASC;
                """,
                (calculation_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def list_revisions(self, calculation_id: str) -> List[Dict[str, Any]]:
        """Alias for get_calculation_revisions."""
        return self.get_calculation_revisions(calculation_id)

    def get_revision_detail(self, calculation_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific calculation revision (inputs + results + provenance)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    r.revision_number, r.change_notes, r.created_by, r.software_version, r.created_at,
                    r.code_edition, r.reference_manifest_sha256, r.reference_snapshot_json,
                    i.inputs_json,
                    res.demand, res.capacity, res.dcr, res.status, res.governing_limit_state, res.results_json
                FROM calculation_revisions r
                LEFT JOIN calculation_inputs i
                    ON r.calculation_id = i.calculation_id AND r.revision_number = i.revision_number
                LEFT JOIN calculation_results res
                    ON r.calculation_id = res.calculation_id AND r.revision_number = res.revision_number
                WHERE r.calculation_id = ? AND r.revision_number = ?;
                """,
                (calculation_id, revision_number),
            )
            row = cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            if data.get("inputs_json"):
                data["inputs"] = json.loads(data["inputs_json"])
            if data.get("results_json"):
                data["results"] = json.loads(data["results_json"])
            if data.get("reference_snapshot_json"):
                try:
                    data["reference_snapshot"] = json.loads(data["reference_snapshot_json"])
                except json.JSONDecodeError:
                    data["reference_snapshot"] = None
            return data

    def get_revision(self, calculation_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Alias for get_revision_detail."""
        return self.get_revision_detail(calculation_id, revision_number)
