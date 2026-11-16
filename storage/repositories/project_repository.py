"""SQLite Project & Revision Repository per SAD v1.0 Section 9.3 & ADR-05.

Implements structured local storage for projects, calculations, inputs,
results, revisions, reference files, and sync history.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from core.common.calculation_result import CalculationResult, CalculationStatus, DesignMethod


class ProjectRepository:
    """Manages SQLite storage for structural engineering projects and calculation runs."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        if db_path is None:
            # Default to storage/projects/structural_app.sqlite3
            root_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = root_dir / "storage" / "projects" / "structural_app.sqlite3"
        elif str(db_path) == ":memory:":
            self.db_path = Path(":memory:")
        else:
            self.db_path = Path(db_path).resolve()

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Create, configure, and ensure proper closure of a SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the 8 SQLite schema tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. projects
            cursor.execute("""
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

            # 2. calculations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calculations (
                    calculation_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                    module_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    code_edition TEXT NOT NULL,
                    design_method TEXT NOT NULL,
                    current_revision INTEGER DEFAULT 1,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # 3. calculation_inputs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calculation_inputs (
                    input_id TEXT PRIMARY KEY,
                    calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
                    revision_number INTEGER NOT NULL,
                    inputs_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(calculation_id, revision_number)
                );
            """)

            # 4. calculation_results
            cursor.execute("""
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

            # 5. calculation_revisions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calculation_revisions (
                    revision_id TEXT PRIMARY KEY,
                    calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
                    revision_number INTEGER NOT NULL,
                    change_notes TEXT,
                    created_by TEXT,
                    software_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(calculation_id, revision_number)
                );
            """)

            # 6. reference_files
            cursor.execute("""
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

            # 7. sync_history
            cursor.execute("""
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

            # 8. application_settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            conn.commit()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # --------------------------------------------------------------------------
    # Project CRUD
    # --------------------------------------------------------------------------
    def create_project(
        self,
        name: str,
        code: Optional[str] = None,
        client: str = "",
        engineer: str = "",
        description: str = "",
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new project record."""
        p_id = project_id or str(uuid.uuid4())
        now = self._now_iso()
        p_code = code or f"PRJ-{p_id[:8].upper()}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (project_id, name, code, client, engineer, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?);
            """, (p_id, name, p_code, client, engineer, description, now, now))
            conn.commit()

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
        """Delete project and all associated calculations via CASCADE."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE project_id = ?;", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Calculation & Revision Management (SAD Section 9.4)
    # --------------------------------------------------------------------------
    def create_calculation(
        self,
        project_id: str,
        module_id: str,
        title: str,
        code_edition: str,
        design_method: Union[str, DesignMethod],
        calculation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new calculation container within a project."""
        c_id = calculation_id or str(uuid.uuid4())
        method_str = design_method.value if isinstance(design_method, DesignMethod) else str(design_method)
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calculations (
                    calculation_id, project_id, module_id, title, code_edition,
                    design_method, current_revision, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 'INCOMPLETE', ?, ?);
            """, (c_id, project_id, module_id, title, code_edition, method_str, now, now))
            conn.commit()

        return self.get_calculation(c_id)  # type: ignore

    def save_calculation_run(
        self,
        calculation_id: str,
        calc_result: CalculationResult,
        change_notes: str = "Initial calculation run",
        engineer: str = ""
    ) -> int:
        """
        Record a calculation execution as an immutable revision per SAD Section 9.4.
        Atomically saves inputs, results, and revision log, then increments current_revision.
        Returns new revision number.
        """
        now = self._now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_revision, project_id FROM calculations WHERE calculation_id = ?;", (calculation_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Calculation '{calculation_id}' not found.")

            new_revision = row["current_revision"] + 1
            project_id = row["project_id"]

            # 1. Store inputs
            cursor.execute("""
                INSERT INTO calculation_inputs (input_id, calculation_id, revision_number, inputs_json, created_at)
                VALUES (?, ?, ?, ?, ?);
            """, (str(uuid.uuid4()), calculation_id, new_revision, json.dumps(calc_result.input_parameters), now))

            # 2. Serialize full calculation result
            gov_str = calc_result.governing_limit_state.name if calc_result.governing_limit_state else ""
            res_dict = {
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
                        "notes": ls.notes
                    }
                    for ls in calc_result.limit_states
                ],
                "reference_files": calc_result.reference_files,
                "software_version": calc_result.software_version,
                "warnings": calc_result.warnings
            }

            cursor.execute("""
                INSERT INTO calculation_results (
                    result_id, calculation_id, revision_number, demand, capacity,
                    dcr, status, governing_limit_state, results_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(uuid.uuid4()),
                calculation_id,
                new_revision,
                calc_result.demand,
                calc_result.capacity,
                calc_result.dcr,
                calc_result.status.value,
                gov_str,
                json.dumps(res_dict),
                now
            ))

            # 3. Store revision metadata
            cursor.execute("""
                INSERT INTO calculation_revisions (
                    revision_id, calculation_id, revision_number, change_notes,
                    created_by, software_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                str(uuid.uuid4()),
                calculation_id,
                new_revision,
                change_notes,
                engineer,
                calc_result.software_version,
                now
            ))

            # 4. Update parent calculation record
            cursor.execute("""
                UPDATE calculations
                SET current_revision = ?, status = ?, updated_at = ?
                WHERE calculation_id = ?;
            """, (new_revision, calc_result.status.value, now, calculation_id))

            # 5. Touch project updated_at
            cursor.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?;", (now, project_id))

            conn.commit()

        return new_revision

    def get_calculation(self, calculation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve calculation record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculations WHERE calculation_id = ?;", (calculation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_calculations_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List all calculations for a given project."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM calculations WHERE project_id = ? ORDER BY updated_at DESC;
            """, (project_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_calculation_revisions(self, calculation_id: str) -> List[Dict[str, Any]]:
        """Get revision history for a calculation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM calculation_revisions WHERE calculation_id = ? ORDER BY revision_number ASC;
            """, (calculation_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_revision_detail(self, calculation_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific calculation revision (inputs + results + metadata)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    r.revision_number, r.change_notes, r.created_by, r.software_version, r.created_at,
                    i.inputs_json,
                    res.demand, res.capacity, res.dcr, res.status, res.governing_limit_state, res.results_json
                FROM calculation_revisions r
                LEFT JOIN calculation_inputs i 
                    ON r.calculation_id = i.calculation_id AND r.revision_number = i.revision_number
                LEFT JOIN calculation_results res 
                    ON r.calculation_id = res.calculation_id AND r.revision_number = res.revision_number
                WHERE r.calculation_id = ? AND r.revision_number = ?;
            """, (calculation_id, revision_number))
            row = cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            if data.get("inputs_json"):
                data["inputs"] = json.loads(data["inputs_json"])
            if data.get("results_json"):
                data["results"] = json.loads(data["results_json"])
            return data
