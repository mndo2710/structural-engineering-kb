"""Unit and migration tests for SQLite ProjectRepository (Schema v2), ProjectService, and HistoryService."""

import hashlib
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest

from app.services.history_service import HistoryService
from app.services.project_service import ProjectService
from core.common.calculation_result import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
import storage.migrations.schema_v2 as schema_v2
from storage.migrations.schema_v2 import SCHEMA_VERSION, migrate_to_v2
from storage.repositories.project_repository import ProjectRepository


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _create_v1_fixture_db(db_path: Path, user_version: int = 0) -> dict:
    """Create a realistic v1 SQLite database matching the legacy Day 12-14 DDL."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    # Legacy v1 DDL (including legacy DEFAULT 1 on current_revision and user_version = 0/1)
    conn.executescript("""
        CREATE TABLE projects (
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

        CREATE TABLE calculations (
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

        CREATE TABLE calculation_inputs (
            input_id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL,
            inputs_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(calculation_id, revision_number)
        );

        CREATE TABLE calculation_results (
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

        CREATE TABLE calculation_revisions (
            revision_id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL REFERENCES calculations(calculation_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL,
            change_notes TEXT,
            created_by TEXT,
            software_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(calculation_id, revision_number)
        );

        CREATE TABLE reference_files (
            reference_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            code TEXT,
            edition TEXT,
            sha256 TEXT,
            last_verified TEXT,
            verification_status TEXT
        );

        CREATE TABLE sync_history (
            sync_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            direction TEXT NOT NULL,
            files_synced INTEGER DEFAULT 0,
            conflicts INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            details_json TEXT
        );

        CREATE TABLE application_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Seed two projects and calculations with timestamps and Unicode engineering JSON payloads
    conn.execute(
        """
        INSERT INTO projects (project_id, name, code, client, engineer, description, status, created_at, updated_at)
        VALUES
            ('p1', 'Hillside Residence', 'PRJ-01', 'Acme', 'Jane Doe, PE', 'V1 project 1', 'ACTIVE', '2026-11-10T10:00:00+00:00', '2026-11-12T10:00:00+00:00'),
            ('p2', 'Commercial Canopy', 'PRJ-02', 'Beta LLC', 'John Smith, PE', 'V1 project 2', 'ACTIVE', '2026-11-11T10:00:00+00:00', '2026-11-12T11:00:00+00:00');
        """
    )

    conn.execute(
        """
        INSERT INTO calculations (calculation_id, project_id, module_id, title, code_edition, design_method, current_revision, status, created_at, updated_at)
        VALUES
            ('c1', 'p1', 'asce7_parapet_wind', 'Parapet North', 'ASCE 7-22', 'ASD', 2, 'PASS', '2026-11-10T10:01:00+00:00', '2026-11-10T12:00:00+00:00'),
            ('c2', 'p1', 'wood_bolt_lateral', 'Ledger Bolt', 'NDS 2024', 'ASD', 1, 'FAIL', '2026-11-10T10:02:00+00:00', '2026-11-10T12:05:00+00:00'),
            ('c3', 'p1', 'wood_shear_wall_sdpws', 'Shear Wall SW-1', 'SDPWS 2021', 'LRFD', 0, 'INCOMPLETE', '2026-11-10T10:03:00+00:00', '2026-11-10T10:03:00+00:00'),
            ('c4', 'p2', 'asce7_awning_canopy', 'Awning South', 'ASCE 7-22', 'ASD', 1, 'PASS', '2026-11-11T10:01:00+00:00', '2026-11-11T10:05:00+00:00');
        """
    )

    inputs_c1_r1 = json.dumps({"V_mph": 115.0, "h_roof_ft": 25.0, "h_par_ft": 3.5, "symbol": "φ/Ω ≤ 1.0"})
    inputs_c1_r2 = json.dumps({"V_mph": 130.0, "h_roof_ft": 25.0, "h_par_ft": 4.0, "symbol": "φ/Ω ≤ 1.0"})
    inputs_c2_r1 = json.dumps({"bolt_dia_in": 0.5, "species": "Douglas Fir-Larch"})
    inputs_c4_r1 = json.dumps({"V_mph": 110.0, "proj_ft": 6.0})

    results_c1_r1 = json.dumps({"demand": 38.4, "capacity": 50.0, "dcr": 0.768, "status": "PASS", "note": "φ·Rn ≥ Ru"})
    results_c1_r2 = json.dumps({"demand": 48.2, "capacity": 50.0, "dcr": 0.964, "status": "PASS", "note": "Updated V=130"})
    results_c2_r1 = json.dumps({"demand": 1800.0, "capacity": 1500.0, "dcr": 1.2, "status": "FAIL"})
    results_c4_r1 = json.dumps({"demand": 22.0, "capacity": 40.0, "dcr": 0.55, "status": "PASS"})

    conn.executemany(
        "INSERT INTO calculation_inputs (input_id, calculation_id, revision_number, inputs_json, created_at) VALUES (?, ?, ?, ?, ?);",
        [
            ("in-1", "c1", 1, inputs_c1_r1, "2026-11-10T11:00:00+00:00"),
            ("in-2", "c1", 2, inputs_c1_r2, "2026-11-10T12:00:00+00:00"),
            ("in-3", "c2", 1, inputs_c2_r1, "2026-11-10T12:05:00+00:00"),
            ("in-4", "c4", 1, inputs_c4_r1, "2026-11-11T10:05:00+00:00"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO calculation_results (
            result_id, calculation_id, revision_number, demand, capacity, dcr, status,
            governing_limit_state, results_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            ("res-1", "c1", 1, 38.4, 50.0, 0.768, "PASS", "Parapet Wind Pressure", results_c1_r1, "2026-11-10T11:00:00+00:00"),
            ("res-2", "c1", 2, 48.2, 50.0, 0.964, "PASS", "Parapet Wind Pressure", results_c1_r2, "2026-11-10T12:00:00+00:00"),
            ("res-3", "c2", 1, 1800.0, 1500.0, 1.2, "FAIL", "Mode IV Yielding", results_c2_r1, "2026-11-10T12:05:00+00:00"),
            ("res-4", "c4", 1, 22.0, 40.0, 0.55, "PASS", "Canopy Uplift", results_c4_r1, "2026-11-11T10:05:00+00:00"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO calculation_revisions (
            revision_id, calculation_id, revision_number, change_notes, created_by, software_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        [
            ("rev-1", "c1", 1, "Initial V1 run", "Jane Doe, PE", "1.0.0", "2026-11-10T11:00:00+00:00"),
            ("rev-2", "c1", 2, "Risk Cat III bump", "Jane Doe, PE", "1.0.0", "2026-11-10T12:00:00+00:00"),
            ("rev-3", "c2", 1, "Bolt check", "Jane Doe, PE", "1.0.0", "2026-11-10T12:05:00+00:00"),
            ("rev-4", "c4", 1, "Awning baseline", "John Smith, PE", "1.0.0", "2026-11-11T10:05:00+00:00"),
        ],
    )

    conn.execute(f"PRAGMA user_version = {user_version};")
    conn.commit()
    conn.close()

    return {
        "db_sha256": _sha256_bytes(db_path.read_bytes()),
        "inputs": {
            ("c1", 1): inputs_c1_r1,
            ("c1", 2): inputs_c1_r2,
            ("c2", 1): inputs_c2_r1,
            ("c4", 1): inputs_c4_r1,
        },
        "results": {
            ("c1", 1): results_c1_r1,
            ("c1", 2): results_c1_r2,
            ("c2", 1): results_c2_r1,
            ("c4", 1): results_c4_r1,
        },
        "revisions": [
            ("rev-1", "c1", 1, "Initial V1 run", "Jane Doe, PE", "1.0.0", "2026-11-10T11:00:00+00:00"),
            ("rev-2", "c1", 2, "Risk Cat III bump", "Jane Doe, PE", "1.0.0", "2026-11-10T12:00:00+00:00"),
            ("rev-3", "c2", 1, "Bolt check", "Jane Doe, PE", "1.0.0", "2026-11-10T12:05:00+00:00"),
            ("rev-4", "c4", 1, "Awning baseline", "John Smith, PE", "1.0.0", "2026-11-11T10:05:00+00:00"),
        ],
    }


@pytest.fixture
def temp_repo(tmp_path):
    db_file = tmp_path / f"test_struct_{uuid.uuid4().hex}.sqlite3"
    backup_dir = tmp_path / "backups"
    repo = ProjectRepository(db_path=db_file, backup_dir=backup_dir)
    yield repo
    repo.close()


@pytest.fixture
def sample_result():
    ls1 = LimitStateResult(
        step_id="S1",
        name="Flexural Yielding",
        code_clause="AISC 360-22 Sec. F2.1",
        equation_latex="M_n = F_y \\cdot Z_x",
        substitution_str="50 ksi * 10 in^3",
        demand=300.0,
        capacity=500.0,
        units="kip-in.",
        dcr=0.60,
        status=CalculationStatus.PASS,
    )
    return CalculationResult(
        calculation_id="calc-001",
        module_id="steel_beam",
        code_edition="AISC 360-22",
        design_method=DesignMethod.ASD,
        input_parameters={"span_ft": 15.0, "section": "W10x30", "fy_ksi": 50.0},
        assumptions=["Fully braced lateral torsional buckling"],
        intermediate_results={"Zx_in3": 36.6},
        limit_states=[ls1],
        governing_limit_state=ls1,
        demand=300.0,
        capacity=500.0,
        dcr=0.60,
        status=CalculationStatus.PASS,
        reference_files=["database/aisc_360/v16th_ed/aisc_w_shapes.csv"],
        software_version="1.0.0",
    )


class TestProjectRepository:
    def test_create_and_get_project(self, temp_repo):
        prj = temp_repo.create_project(
            name="Hillside Residence",
            code="PRJ-HILL-01",
            client="Acme Builders",
            engineer="Jane Doe, PE",
            description="2-story custom residential home",
        )
        assert prj["name"] == "Hillside Residence"
        assert prj["code"] == "PRJ-HILL-01"
        assert prj["status"] == "ACTIVE"

        fetched = temp_repo.get_project(prj["project_id"])
        assert fetched is not None
        assert fetched["engineer"] == "Jane Doe, PE"

    def test_list_and_update_project(self, temp_repo):
        prj = temp_repo.create_project(name="Commercial Awning", code="PRJ-AWN-01")
        assert len(temp_repo.list_projects()) == 1

        updated = temp_repo.update_project(prj["project_id"], {"description": "Updated canopy"})
        assert updated is True
        fetched = temp_repo.get_project(prj["project_id"])
        assert fetched["description"] == "Updated canopy"

    def test_delete_project_cascade(self, temp_repo, sample_result):
        prj = temp_repo.create_project(name="To Delete", code="PRJ-DEL-01")
        calc = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="steel_beam",
            title="Beam Calc",
            code_edition="AISC 360-22",
            design_method=DesignMethod.ASD,
        )
        temp_repo.save_calculation_run(calc["calculation_id"], sample_result)

        assert len(temp_repo.list_calculations_for_project(prj["project_id"])) == 1
        deleted = temp_repo.delete_project(prj["project_id"])
        assert deleted is True
        assert temp_repo.get_project(prj["project_id"]) is None
        assert temp_repo.get_calculation(calc["calculation_id"]) is None

    def test_revision_management(self, temp_repo, sample_result):
        prj = temp_repo.create_project(name="Parapet Design", code="PRJ-PAR-01")
        calc = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="cc_parapet",
            title="Parapet Wind Load",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.ASD,
        )

        # Revision 1
        rev1 = temp_repo.save_calculation_run(
            calc["calculation_id"],
            sample_result,
            change_notes="Initial calc run",
            engineer="John Smith, PE",
        )
        assert rev1 == 1

        # Revision 2 with updated inputs and result
        sample_result.input_parameters["span_ft"] = 20.0
        sample_result.demand = 450.0
        sample_result.dcr = 0.90
        rev2 = temp_repo.save_calculation_run(
            calc["calculation_id"],
            sample_result,
            change_notes="Increased span to 20 ft",
            engineer="John Smith, PE",
        )
        assert rev2 == 2

        # Check revision history
        revisions = temp_repo.get_calculation_revisions(calc["calculation_id"])
        assert len(revisions) == 2
        assert revisions[0]["revision_number"] == 1
        assert revisions[1]["revision_number"] == 2
        assert len(temp_repo.list_revisions(calc["calculation_id"])) == 2

        # Verify revision 1 details preserved
        detail_rev1 = temp_repo.get_revision_detail(calc["calculation_id"], 1)
        assert detail_rev1["inputs"]["span_ft"] == 15.0
        assert detail_rev1["dcr"] == pytest.approx(0.60)

        # Verify revision 2 details via alias get_revision
        detail_rev2 = temp_repo.get_revision(calc["calculation_id"], 2)
        assert detail_rev2["inputs"]["span_ft"] == 20.0
        assert detail_rev2["dcr"] == pytest.approx(0.90)


class TestProjectAndHistoryServices:
    def test_project_service_workflow(self, temp_repo, sample_result):
        svc = ProjectService(repository=temp_repo)
        prj = svc.create_project(name="Active Project", engineer="Alice, PE")
        assert svc.active_project_id == prj["project_id"]

        calc = svc.create_calculation(
            module_id="cc_wind",
            title="Roof Overhang",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.LRFD,
        )
        rev = svc.save_calculation_run(calc["calculation_id"], sample_result, change_notes="First run")
        assert rev == 1

        calcs = svc.list_calculations()
        assert len(calcs) == 1
        assert calcs[0]["calculation_id"] == calc["calculation_id"]

    def test_history_service_comparison(self, temp_repo, sample_result):
        prj_svc = ProjectService(repository=temp_repo)
        prj_svc.create_project(name="Comparison Test")
        calc = prj_svc.create_calculation(
            module_id="steel_beam",
            title="Beam Check",
            code_edition="AISC 360-22",
            design_method=DesignMethod.ASD,
        )

        # Rev 1
        sample_result.input_parameters["depth_in"] = 12.0
        sample_result.dcr = 0.75
        prj_svc.save_calculation_run(calc["calculation_id"], sample_result, "Baseline")

        # Rev 2
        sample_result.input_parameters["depth_in"] = 14.0
        sample_result.dcr = 0.55
        prj_svc.save_calculation_run(calc["calculation_id"], sample_result, "Increased beam depth")

        hist_svc = HistoryService(repository=temp_repo)
        diff = hist_svc.compare_revisions(calc["calculation_id"], 1, 2)

        assert diff["from_revision"] == 1
        assert diff["to_revision"] == 2
        assert "depth_in" in diff["input_diffs"]
        assert diff["input_diffs"]["depth_in"]["previous"] == 12.0
        assert diff["input_diffs"]["depth_in"]["current"] == 14.0
        assert diff["result_diffs"]["previous_dcr"] == pytest.approx(0.75)
        assert diff["result_diffs"]["current_dcr"] == pytest.approx(0.55)
        assert diff["result_diffs"]["dcr_delta"] == pytest.approx(-0.20)


class TestSchemaV2Migration:
    """WP-1a: SQLite Schema v2 creation, v1->v2 migration, backup, preservation, idempotence, rollback."""

    def test_new_database_schema_v2_and_default_current_revision(self, tmp_path):
        db_file = tmp_path / "fresh_v2.sqlite3"
        backup_dir = tmp_path / "backups"

        repo = ProjectRepository(db_path=db_file, backup_dir=backup_dir)
        assert repo.get_schema_version() == SCHEMA_VERSION == 2
        assert repo.last_backup_path is None
        assert not backup_dir.exists() or list(backup_dir.iterdir()) == []

        conn = sqlite3.connect(str(db_file))
        try:
            tables = {
                r[0]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            }
            assert {
                "projects",
                "calculation_groups",
                "project_settings",
                "calculations",
                "calculation_inputs",
                "calculation_results",
                "calculation_revisions",
                "reference_files",
                "sync_history",
                "application_settings",
            }.issubset(tables)

            indexes = {
                r[0]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()
            }
            assert {"idx_calc_project_order", "idx_groups_project_order"}.issubset(indexes)

            calc_info = {row[1]: row for row in conn.execute("PRAGMA table_info(calculations);").fetchall()}
            # column tuple: (cid, name, type, notnull, dflt_value, pk)
            assert calc_info["current_revision"][4] == "0"
            for expected_col in (
                "group_id",
                "sort_order",
                "item_number",
                "draft_inputs_json",
                "draft_updated_at",
                "last_dcr",
                "last_input_hash",
                "is_deleted",
            ):
                assert expected_col in calc_info

            rev_info = {row[1]: row for row in conn.execute("PRAGMA table_info(calculation_revisions);").fetchall()}
            for expected_col in (
                "code_edition",
                "reference_manifest_sha256",
                "reference_snapshot_json",
            ):
                assert expected_col in rev_info

            assert conn.execute("PRAGMA foreign_key_check;").fetchall() == []
        finally:
            conn.close()

    def test_v1_to_v2_migration_backup_preservation_and_idempotence(self, tmp_path):
        db_file = tmp_path / "legacy_v1.sqlite3"
        backup_dir = tmp_path / "backups"
        fixture = _create_v1_fixture_db(db_file, user_version=0)

        repo = ProjectRepository(db_path=db_file, backup_dir=backup_dir)

        # 1. Backup created BEFORE migration and matches pre-migration file byte-for-byte
        backups = list(backup_dir.glob("legacy_v1_v0_backup_*.sqlite3"))
        assert len(backups) == 1
        assert repo.last_backup_path == backups[0]
        assert _sha256_bytes(backups[0].read_bytes()) == fixture["db_sha256"]

        # 2. Schema version updated to 2
        assert repo.get_schema_version() == 2
        assert repo.last_migration_result["migrated"] is True
        assert repo.last_migration_result["from_version"] == 0
        assert repo.last_migration_result["to_version"] == 2

        # 3. Backfill monotonic item_number & sort_order per project
        p1_calcs = repo.list_calculations_for_project("p1")
        assert [(c["calculation_id"], c["item_number"], c["sort_order"], c["display_code"]) for c in p1_calcs] == [
            ("c1", 1, 1, "C-01"),
            ("c2", 2, 2, "C-02"),
            ("c3", 3, 3, "C-03"),
        ]
        p2_calcs = repo.list_calculations_for_project("p2")
        assert [(c["calculation_id"], c["item_number"], c["sort_order"], c["display_code"]) for c in p2_calcs] == [
            ("c4", 1, 1, "C-01"),
        ]

        # 4. Project settings initialized for existing v1 projects
        assert repo.get_project_settings("p1")["default_design_method"] == "ASD"
        assert repo.get_project_settings("p2")["default_design_method"] == "ASD"

        # 5. Byte-for-byte preservation of calculation_inputs, calculation_results, and calculation_revisions
        conn = sqlite3.connect(str(db_file))
        try:
            assert conn.execute("PRAGMA foreign_key_check;").fetchall() == []

            for (cid, rev_num), expected_inputs in fixture["inputs"].items():
                actual_inputs = conn.execute(
                    "SELECT inputs_json FROM calculation_inputs WHERE calculation_id = ? AND revision_number = ?;",
                    (cid, rev_num),
                ).fetchone()[0]
                assert actual_inputs == expected_inputs
                assert _sha256_bytes(actual_inputs.encode("utf-8")) == _sha256_bytes(expected_inputs.encode("utf-8"))

            for (cid, rev_num), expected_results in fixture["results"].items():
                actual_results = conn.execute(
                    "SELECT results_json FROM calculation_results WHERE calculation_id = ? AND revision_number = ?;",
                    (cid, rev_num),
                ).fetchone()[0]
                assert actual_results == expected_results
                assert _sha256_bytes(actual_results.encode("utf-8")) == _sha256_bytes(expected_results.encode("utf-8"))

            actual_revs = conn.execute(
                """
                SELECT revision_id, calculation_id, revision_number, change_notes, created_by, software_version, created_at
                FROM calculation_revisions
                ORDER BY revision_id ASC;
                """
            ).fetchall()
            assert actual_revs == fixture["revisions"]
        finally:
            conn.close()

        # Backward-compatible HistoryService read on migrated v1 revision
        hist = HistoryService(repository=repo)
        diff = hist.compare_revisions("c1", 1, 2)
        assert diff["input_diffs"]["V_mph"]["previous"] == 115.0
        assert diff["input_diffs"]["V_mph"]["current"] == 130.0

        # 6. Idempotence: second migration / reopen is a strict no-op (no duplicate backup)
        repo2 = ProjectRepository(db_path=db_file, backup_dir=backup_dir)
        assert repo2.get_schema_version() == 2
        assert repo2.last_migration_result["migrated"] is False
        assert repo2.last_backup_path is None
        second_run = migrate_to_v2(db_file, backup_dir=backup_dir)
        assert second_run["migrated"] is False
        assert len(list(backup_dir.glob("legacy_v1_*.sqlite3"))) == 1

    def test_v1_user_version_1_and_default_storage_backups_dir(self, tmp_path):
        db_file = tmp_path / f"legacy_v1_uv1_{uuid.uuid4().hex}.sqlite3"
        _create_v1_fixture_db(db_file, user_version=1)

        repo = ProjectRepository(db_path=db_file)
        expected_backups_dir = Path(__file__).resolve().parent.parent / "storage" / "backups"
        backup_path = repo.last_backup_path
        try:
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.parent == expected_backups_dir.resolve()
            assert f"{db_file.stem}_v1_backup_" in backup_path.name
            assert repo.get_schema_version() == 2
        finally:
            if backup_path is not None and backup_path.exists():
                backup_path.unlink()

    def test_migration_rollback_on_failure_and_recovery(self, tmp_path, monkeypatch):
        db_file = tmp_path / "rollback_test.sqlite3"
        backup_dir = tmp_path / "backups"
        fixture = _create_v1_fixture_db(db_file, user_version=0)

        def fail_mid_migration(conn):
            raise RuntimeError("Simulated mid-migration failure")

        monkeypatch.setattr(schema_v2, "_backfill_v1_calculations", fail_mid_migration)

        with pytest.raises(RuntimeError, match="Simulated mid-migration failure"):
            ProjectRepository(db_path=db_file, backup_dir=backup_dir)

        # Backup must exist while DB changes were cleanly rolled back
        backups = list(backup_dir.glob("rollback_test_v0_backup_*.sqlite3"))
        assert len(backups) == 1
        assert _sha256_bytes(backups[0].read_bytes()) == fixture["db_sha256"]

        conn = sqlite3.connect(str(db_file))
        try:
            assert conn.execute("PRAGMA user_version;").fetchone()[0] == 0
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
            assert "calculation_groups" not in tables
            assert "project_settings" not in tables
            calc_cols = {r[1] for r in conn.execute("PRAGMA table_info(calculations);").fetchall()}
            assert "item_number" not in calc_cols
            assert conn.execute("SELECT COUNT(*) FROM calculation_revisions;").fetchone()[0] == 4
        finally:
            conn.close()

        # Restore original backfill and confirm clean recovery migration
        monkeypatch.undo()
        recovered = ProjectRepository(db_path=db_file, backup_dir=backup_dir)
        assert recovered.get_schema_version() == 2
        assert len(recovered.list_calculations_for_project("p1")) == 3

    def test_in_memory_database_schema_v2(self):
        repo = ProjectRepository(db_path=":memory:")
        try:
            assert repo.get_schema_version() == 2
            prj = repo.create_project(name="Memory Project")
            calc = repo.create_calculation(
                project_id=prj["project_id"],
                module_id="asce7_parapet_wind",
                title="Mem Calc",
                code_edition="ASCE 7-22",
                design_method="ASD",
            )
            assert calc["item_number"] == 1
            assert calc["display_code"] == "C-01"
        finally:
            repo.close()


class TestSchemaV2ItemAndGroupLifecycle:
    """WP-1b repository layer: settings, groups, monotonic item_number, draft, run state, duplicate, move, soft delete."""

    def test_project_settings_init_and_upsert(self, temp_repo):
        prj = temp_repo.create_project(name="Settings Test")
        settings = temp_repo.get_project_settings(prj["project_id"])
        assert settings is not None
        assert settings["default_design_method"] == "ASD"
        assert settings["code_registry_json"] is None

        updated = temp_repo.upsert_project_settings(
            project_id=prj["project_id"],
            default_design_method=DesignMethod.LRFD,
            code_registry_json={"IBC": "v2024", "AISC_360": "v16th_ed"},
        )
        assert updated["default_design_method"] == "LRFD"
        assert updated["code_registry"] == {"IBC": "v2024", "AISC_360": "v16th_ed"}

        inherited = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="asce7_parapet_wind",
            title="Inherited Method Calc",
            code_edition="ASCE 7-22",
        )
        assert inherited["design_method"] == "LRFD"

        with pytest.raises(ValueError):
            temp_repo.upsert_project_settings(prj["project_id"], default_design_method="INVALID")

    def test_group_crud_reorder_collapse_and_delete(self, temp_repo):
        prj = temp_repo.create_project(name="Grouped Project")
        pid = prj["project_id"]

        g1 = temp_repo.create_group(pid, "Roof framing")
        g2 = temp_repo.create_group(pid, "Level 2")
        g3 = temp_repo.create_group(pid, "Foundation")

        assert [g["name"] for g in temp_repo.list_groups(pid)] == ["Roof framing", "Level 2", "Foundation"]
        assert g1["is_collapsed"] is False

        renamed = temp_repo.rename_group(g2["group_id"], "Second Floor")
        assert renamed["name"] == "Second Floor"

        collapsed = temp_repo.set_group_collapsed(g1["group_id"], True)
        assert collapsed["is_collapsed"] is True

        # Move Foundation (index 2) to index 0
        reordered = temp_repo.move_group(g3["group_id"], 0)
        assert [g["name"] for g in reordered] == ["Foundation", "Roof framing", "Second Floor"]
        assert [g["sort_order"] for g in reordered] == [1, 2, 3]

        # Add calculation inside Second Floor, then delete Second Floor -> item becomes ungrouped
        calc = temp_repo.create_calculation(
            project_id=pid,
            module_id="wood_bolt_lateral",
            title="Beam Bolt",
            code_edition="NDS 2024",
            design_method="ASD",
            group_id=g2["group_id"],
        )
        assert temp_repo.delete_group(g2["group_id"]) is True
        assert temp_repo.get_group(g2["group_id"]) is None
        fetched_calc = temp_repo.get_calculation(calc["calculation_id"])
        assert fetched_calc["group_id"] is None
        assert [g["name"] for g in temp_repo.list_groups(pid)] == ["Foundation", "Roof framing"]

    def test_monotonic_item_number_and_soft_delete_preserves_revisions(self, temp_repo, sample_result):
        p1 = temp_repo.create_project(name="Project 1")
        p2 = temp_repo.create_project(name="Project 2")

        c1 = temp_repo.create_calculation(p1["project_id"], "asce7_parapet_wind", "P1-1", "ASCE 7-22", "ASD")
        c2 = temp_repo.create_calculation(p1["project_id"], "asce7_parapet_wind", "P1-2", "ASCE 7-22", "ASD")
        c3 = temp_repo.create_calculation(p1["project_id"], "asce7_parapet_wind", "P1-3", "ASCE 7-22", "ASD")
        other = temp_repo.create_calculation(p2["project_id"], "asce7_parapet_wind", "P2-1", "ASCE 7-22", "ASD")

        assert (c1["item_number"], c1["display_code"]) == (1, "C-01")
        assert (c2["item_number"], c2["display_code"]) == (2, "C-02")
        assert (c3["item_number"], c3["display_code"]) == (3, "C-03")
        assert (other["item_number"], other["display_code"]) == (1, "C-01")

        # Save a revision on c3 before soft deleting it
        rev_num = temp_repo.save_calculation_run(
            c3["calculation_id"],
            sample_result,
            change_notes="Saved before delete",
            engineer="Nhat Do, PE",
            reference_manifest_sha256="sha256-manifest-abc",
            reference_snapshot={"total": 92},
            input_hash="hash-rev1",
        )
        assert rev_num == 1

        assert temp_repo.soft_delete_calculation(c3["calculation_id"]) is True
        assert [c["calculation_id"] for c in temp_repo.list_calculations_for_project(p1["project_id"])] == [
            c1["calculation_id"],
            c2["calculation_id"],
        ]
        all_with_deleted = temp_repo.list_calculations_for_project(p1["project_id"], include_deleted=True)
        assert len(all_with_deleted) == 3
        assert all_with_deleted[2]["is_deleted"] is True

        # Revisions, inputs, and results for soft-deleted c3 remain intact
        revs = temp_repo.get_calculation_revisions(c3["calculation_id"])
        assert len(revs) == 1
        detail = temp_repo.get_revision_detail(c3["calculation_id"], 1)
        assert detail["code_edition"] == "AISC 360-22"
        assert detail["reference_manifest_sha256"] == "sha256-manifest-abc"
        assert detail["reference_snapshot"] == {"total": 92}

        # New item after soft delete gets monotonic item_number = 4 (never reuses 3)
        c4 = temp_repo.create_calculation(p1["project_id"], "asce7_parapet_wind", "P1-4", "ASCE 7-22", "ASD")
        assert (c4["item_number"], c4["display_code"]) == (4, "C-04")

    def test_draft_autosave_and_run_state_without_revision(self, temp_repo):
        prj = temp_repo.create_project(name="Draft Lifecycle")
        calc = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="asce7_parapet_wind",
            title="Parapet Check",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.ASD,
        )
        assert calc["current_revision"] == 0
        assert calc["status"] == "INCOMPLETE"
        assert calc["draft_inputs_json"] is None
        assert calc["last_dcr"] is None
        assert calc["last_input_hash"] is None

        drafted = temp_repo.update_draft(
            calc["calculation_id"],
            draft_inputs={"V_mph": 120.0, "h_roof_ft": 30.0},
            design_method=DesignMethod.LRFD,
        )
        assert drafted["design_method"] == "LRFD"
        assert drafted["draft_inputs"] == {"V_mph": 120.0, "h_roof_ft": 30.0}
        assert drafted["draft_updated_at"] is not None
        assert drafted["current_revision"] == 0
        assert temp_repo.get_calculation_revisions(calc["calculation_id"]) == []

        run_updated = temp_repo.update_run_state(
            calc["calculation_id"],
            last_dcr=0.72,
            status=CalculationStatus.PASS,
            last_input_hash="canonical-hash-001",
        )
        assert run_updated["last_dcr"] == pytest.approx(0.72)
        assert run_updated["status"] == "PASS"
        assert run_updated["last_input_hash"] == "canonical-hash-001"
        assert run_updated["current_revision"] == 0
        assert temp_repo.get_calculation_revisions(calc["calculation_id"]) == []

    def test_duplicate_calculation_copies_draft_or_latest_revision_and_zero_revisions(self, temp_repo, sample_result):
        prj = temp_repo.create_project(name="Duplicate Test")
        grp1 = temp_repo.create_group(prj["project_id"], "Group A")
        grp2 = temp_repo.create_group(prj["project_id"], "Group B")

        # Case 1: Source has saved revision and no draft -> copies latest revision inputs
        src1 = temp_repo.create_calculation(
            project_id=prj["project_id"],
            module_id="steel_beam",
            title="Primary Beam",
            code_edition="AISC 360-22",
            design_method="ASD",
            group_id=grp1["group_id"],
        )
        sample_result.input_parameters = {"span_ft": 18.0, "fy_ksi": 50.0}
        temp_repo.save_calculation_run(src1["calculation_id"], sample_result, "Rev 1")
        sample_result.input_parameters = {"span_ft": 24.0, "fy_ksi": 50.0}
        temp_repo.save_calculation_run(src1["calculation_id"], sample_result, "Rev 2")

        dup1 = temp_repo.duplicate_calculation(src1["calculation_id"])
        assert dup1["calculation_id"] != src1["calculation_id"]
        assert dup1["item_number"] == 2
        assert dup1["title"] == "Primary Beam (Copy)"
        assert dup1["group_id"] == grp1["group_id"]
        assert dup1["current_revision"] == 0
        assert dup1["status"] == "INCOMPLETE"
        assert dup1["last_dcr"] is None
        assert dup1["draft_inputs"] == {"span_ft": 24.0, "fy_ksi": 50.0}
        assert temp_repo.get_calculation_revisions(dup1["calculation_id"]) == []

        # Case 2: Source has edited draft -> copies edited draft rather than older revision, and supports target group_id
        temp_repo.update_draft(src1["calculation_id"], {"span_ft": 30.0, "fy_ksi": 50.0})
        dup2 = temp_repo.duplicate_calculation(
            src1["calculation_id"],
            new_title="Beam Alt",
            group_id=grp2["group_id"],
        )
        assert dup2["item_number"] == 3
        assert dup2["title"] == "Beam Alt"
        assert dup2["group_id"] == grp2["group_id"]
        assert dup2["draft_inputs"] == {"span_ft": 30.0, "fy_ksi": 50.0}
        assert temp_repo.get_calculation_revisions(dup2["calculation_id"]) == []

        # Case 3: Blank source
        blank = temp_repo.create_calculation(prj["project_id"], "cc_parapet", "Blank", "ASCE 7-22", "ASD")
        dup3 = temp_repo.duplicate_calculation(blank["calculation_id"])
        assert dup3["draft_inputs_json"] is None
        assert dup3["current_revision"] == 0
        assert dup3["status"] == "INCOMPLETE"

    def test_rename_and_atomic_move_calculation_ordering(self, temp_repo):
        prj = temp_repo.create_project(name="Ordering Test")
        pid = prj["project_id"]
        g1 = temp_repo.create_group(pid, "Roof")
        g2 = temp_repo.create_group(pid, "Wall")

        c1 = temp_repo.create_calculation(pid, "asce7_parapet_wind", "Item 1", "ASCE 7-22", "ASD", group_id=g1["group_id"])
        c2 = temp_repo.create_calculation(pid, "asce7_parapet_wind", "Item 2", "ASCE 7-22", "ASD", group_id=g1["group_id"])
        c3 = temp_repo.create_calculation(pid, "asce7_parapet_wind", "Item 3", "ASCE 7-22", "ASD", group_id=g1["group_id"])
        u1 = temp_repo.create_calculation(pid, "wood_bolt_lateral", "Ungrouped 1", "NDS 2024", "ASD")

        renamed = temp_repo.rename_calculation(c2["calculation_id"], "Parapet Corner")
        assert renamed["title"] == "Parapet Corner"

        # Reorder within same group: move Item 3 to index 0
        ordered = temp_repo.move_calculation(c3["calculation_id"], g1["group_id"], 0)
        assert [c["calculation_id"] for c in ordered] == [
            c3["calculation_id"],
            c1["calculation_id"],
            c2["calculation_id"],
            u1["calculation_id"],
        ]

        # Move Item 1 across groups into g2 at index 0
        ordered = temp_repo.move_calculation(c1["calculation_id"], g2["group_id"], 0)
        assert [c["calculation_id"] for c in ordered] == [
            c3["calculation_id"],
            c2["calculation_id"],
            c1["calculation_id"],
            u1["calculation_id"],
        ]
        assert temp_repo.get_calculation(c1["calculation_id"])["group_id"] == g2["group_id"]

        # Move Ungrouped 1 into g2 at index 0 -> before Item 1 in Wall group
        ordered = temp_repo.move_calculation(u1["calculation_id"], g2["group_id"], 0)
        assert [c["calculation_id"] for c in ordered] == [
            c3["calculation_id"],
            c2["calculation_id"],
            u1["calculation_id"],
            c1["calculation_id"],
        ]

        # Move Item 3 to ungrouped (group_id=None)
        ordered = temp_repo.move_calculation(c3["calculation_id"], None, 0)
        assert [c["calculation_id"] for c in ordered] == [
            c2["calculation_id"],
            u1["calculation_id"],
            c1["calculation_id"],
            c3["calculation_id"],
        ]

        # Invalid target_group_id fails atomically without altering existing ordering
        with pytest.raises(ValueError):
            temp_repo.move_calculation(c2["calculation_id"], "non-existent-group", 0)
        after_err = temp_repo.list_calculations_for_project(pid)
        assert [c["calculation_id"] for c in after_err] == [c["calculation_id"] for c in ordered]
