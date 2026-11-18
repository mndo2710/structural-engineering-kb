"""Pure-Python unit tests for WP-1b (ProjectService/HistoryService) & WP-4 (WorkspaceController).

Zero PySide6/Qt imports.
"""

import ast
from pathlib import Path
import pytest

from app.controllers import WorkspaceController
from app.models import CalculationStatus, DesignMethod, WorkspaceViewModel
from app.registry import ModuleMaturity, ModuleRegistry, ModuleSpec, get_module_registry
from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from storage.repositories.project_repository import ProjectRepository


@pytest.fixture
def env(tmp_path):
    db_path = tmp_path / "wp4_test.sqlite3"
    repo = ProjectRepository(db_path=db_path)
    kb = KnowledgeBaseService()
    prj = ProjectService(repository=repo)
    prj.ensure_active_project()
    hist = HistoryService(repository=repo)
    calc = CalculationService(kb_service=kb, project_service=prj)
    ctrl = WorkspaceController(
        project_service=prj,
        calculation_service=calc,
        history_service=hist,
        knowledge_base_service=kb,
    )
    return {
        "db_path": db_path,
        "repo": repo,
        "kb": kb,
        "prj": prj,
        "hist": hist,
        "calc": calc,
        "ctrl": ctrl,
    }


def _populate_bolt_benchmark(ctrl: WorkspaceController, item_id: str, p_demand: float = 340.0) -> WorkspaceViewModel:
    bm = dict(get_module_registry().get_benchmark_inputs("wood_bolt_lateral"))
    bm["P_demand_lbs"] = p_demand
    vm = ctrl.load(item_id)
    for k, v in bm.items():
        vm = ctrl.edit_field(item_id, k, str(v))
    return vm


class TestIndependentMultiItemState:
    def test_two_items_same_module_are_fully_independent(self, env):
        prj: ProjectService = env["prj"]
        ctrl: WorkspaceController = env["ctrl"]

        item1 = prj.add_item("wood_bolt_lateral", "C-01 · Bolt Joint A", group_name="Roof framing", start_from="blank")
        item2 = prj.add_item("wood_bolt_lateral", "C-02 · Bolt Joint B", group_name="Level 2", start_from="blank")
        id1 = item1["calculation_id"]
        id2 = item2["calculation_id"]

        # Populate distinct inputs and design methods
        _populate_bolt_benchmark(ctrl, id1, p_demand=340.0)
        _populate_bolt_benchmark(ctrl, id2, p_demand=520.0)
        ctrl.set_design_method(id2, DesignMethod.LRFD)

        vm1 = ctrl.run(id1)
        vm2 = ctrl.run(id2)

        assert vm1.design_method == DesignMethod.ASD
        assert vm2.design_method == DesignMethod.LRFD
        assert vm1.last_result is not None and vm2.last_result is not None
        assert vm1.summary.dcr != vm2.summary.dcr
        assert vm1.last_result.input_parameters["P_demand_lbs"] == pytest.approx(340.0)
        assert vm2.last_result.input_parameters["P_demand_lbs"] == pytest.approx(520.0)

        # Save revision only on item1; item2 keeps 0 revisions
        vm1_saved = ctrl.save_revision(id1, "Saved joint A only")
        vm2_reload = ctrl.load(id2)
        assert vm1_saved.current_revision == 1
        assert vm2_reload.current_revision == 0


class TestBlankAndInvalidValidationLifecycle:
    def test_blank_start_and_invalid_numeric_prevent_engine_execution(self, env, monkeypatch):
        prj: ProjectService = env["prj"]
        ctrl: WorkspaceController = env["ctrl"]
        calc: CalculationService = env["calc"]

        calls = []
        orig_run = calc.run_calculation

        def spy_run(*args, **kwargs):
            calls.append((args, kwargs))
            return orig_run(*args, **kwargs)

        monkeypatch.setattr(calc, "run_calculation", spy_run)

        item = prj.add_item("wood_bolt_lateral", "C-01 · Blank Bolt", group_name="Roof framing", start_from="blank")
        cid = item["calculation_id"]

        vm_init = ctrl.load(cid)
        assert vm_init.status == CalculationStatus.INCOMPLETE
        assert vm_init.last_result is None
        assert vm_init.summary.dcr is None
        assert vm_init.summary.rows == ()
        assert len(vm_init.incomplete_reasons) > 0

        # Run on blank inputs -> INCOMPLETE, engine NOT invoked
        vm_blank_run = ctrl.run(cid)
        assert vm_blank_run.status == CalculationStatus.INCOMPLETE
        assert len(calls) == 0
        assert prj.get_calculation(cid)["last_dcr"] is None

        # Invalid numeric field -> INVALID INPUT, engine NOT invoked
        _populate_bolt_benchmark(ctrl, cid)
        vm_bad = ctrl.edit_field(cid, "D_in", "not_a_number")
        assert vm_bad.status == CalculationStatus.INVALID_INPUT
        bad_field = next(f for f in vm_bad.fields if f.spec.key == "D_in")
        assert bad_field.is_valid is False
        assert "Invalid numeric" in bad_field.error_message

        vm_bad_run = ctrl.run(cid)
        assert vm_bad_run.status == CalculationStatus.INVALID_INPUT
        assert len(calls) == 0

        with pytest.raises(ValueError, match="Cannot save revision"):
            ctrl.save_revision(cid, "Should fail")


class TestRunVsSaveRevisionAndStaleTracking:
    def test_run_does_not_create_revision_while_save_revision_creates_immutable_snapshot(self, env):
        prj: ProjectService = env["prj"]
        ctrl: WorkspaceController = env["ctrl"]
        hist: HistoryService = env["hist"]

        item = prj.add_item("wood_bolt_lateral", "C-01 · Heel Bolt", group_name="Roof framing", start_from="blank")
        cid = item["calculation_id"]
        _populate_bolt_benchmark(ctrl, cid, p_demand=340.0)

        # 1. Run Calculation: updates last_dcr & status, ZERO revisions written
        vm_run = ctrl.run(cid)
        assert vm_run.status == CalculationStatus.PASS
        assert vm_run.is_stale is False
        assert vm_run.current_revision == 0
        assert len(hist.get_history(cid)) == 0
        rec = prj.get_calculation(cid)
        assert rec["last_dcr"] == pytest.approx(vm_run.summary.dcr, rel=1e-4)
        assert rec["current_revision"] == 0

        # 2. Save Revision 1: writes immutable revision with SHA-256 snapshot
        vm_rev1 = ctrl.save_revision(cid, "Baseline ASD heel bolt")
        assert vm_rev1.current_revision == 1
        assert vm_rev1.is_stale is False
        revs = hist.get_history(cid)
        assert len(revs) == 1
        rev1_detail = hist.get_revision(cid, 1)
        assert rev1_detail is not None
        assert rev1_detail["reference_manifest_sha256"]
        assert "reference_files" in (rev1_detail.get("reference_snapshot") or {})

        # Reconstruct CalculationResult from revision 1
        reconstructed = hist.reconstruct_calculation_result(cid, 1)
        assert reconstructed is not None
        assert reconstructed.dcr == pytest.approx(vm_run.summary.dcr, rel=1e-4)
        assert len(reconstructed.limit_states) == len(vm_run.last_result.limit_states)

        # 3. Edit field after saving revision -> flips is_stale = True
        vm_edited = ctrl.edit_field(cid, "P_demand_lbs", "400.0")
        assert vm_edited.is_stale is True
        assert vm_edited.current_revision == 1

        # Save Revision 2 with new demand
        vm_rev2 = ctrl.save_revision(cid, "Increased tension demand to 400 lbs")
        assert vm_rev2.current_revision == 2
        assert vm_rev2.is_stale is False
        assert vm_rev2.summary.dcr > vm_rev1.summary.dcr

        # 4. Load Revision 1 restores revision 1 inputs and result cleanly
        vm_restored = ctrl.load_revision(cid, 1)
        assert vm_restored.is_stale is False
        assert vm_restored.last_result is not None
        assert vm_restored.summary.dcr == pytest.approx(vm_rev1.summary.dcr, rel=1e-4)
        assert vm_restored.draft_inputs["P_demand_lbs"] == pytest.approx(340.0)


class TestDuplicateGroupMoveAndPersistence:
    def test_duplicate_item_copies_draft_only_with_zero_revisions(self, env):
        prj: ProjectService = env["prj"]
        ctrl: WorkspaceController = env["ctrl"]
        hist: HistoryService = env["hist"]

        src = prj.add_item("wood_bolt_lateral", "C-01 · Original Bolt", group_name="Roof framing", start_from="blank")
        src_id = src["calculation_id"]
        _populate_bolt_benchmark(ctrl, src_id, p_demand=340.0)
        ctrl.set_design_method(src_id, DesignMethod.LRFD)
        ctrl.save_revision(src_id, "Rev 1 on original")

        dup = prj.duplicate_item(src_id, new_title="Copied Bolt")
        dup_id = dup["calculation_id"]

        assert dup["item_number"] > src["item_number"]
        assert dup["current_revision"] == 0
        assert dup["status"] == CalculationStatus.INCOMPLETE.value
        assert dup["design_method"] == "LRFD"
        assert len(hist.get_history(dup_id)) == 0

        vm_dup = ctrl.load(dup_id)
        assert vm_dup.design_method == DesignMethod.LRFD
        assert float(vm_dup.draft_inputs["P_demand_lbs"]) == pytest.approx(340.0)
        p_field = next(f for f in vm_dup.fields if f.spec.key == "P_demand_lbs")
        assert p_field.parsed_value == pytest.approx(340.0)
        assert vm_dup.status == CalculationStatus.INCOMPLETE
        assert vm_dup.last_result is None

    def test_groups_reorder_rename_soft_delete_and_persistence_across_sessions(self, env):
        db_path = env["db_path"]
        prj1: ProjectService = env["prj"]
        ctrl1: WorkspaceController = env["ctrl"]

        # Create groups and items
        grp_a = prj1.create_group("Custom Truss Group")
        grp_b = prj1.create_group("Shear Walls")
        prj1.rename_group(grp_b["group_id"], "Lateral Walls")
        prj1.set_group_collapsed(grp_a["group_id"], True)

        i1 = prj1.add_item("asce7_parapet_wind", "Parapet A", group_id=grp_a["group_id"], start_from="blank")
        i2 = prj1.add_item("asce7_parapet_wind", "Parapet B", group_id=grp_a["group_id"], start_from="blank")
        i3 = prj1.add_item("wood_shear_wall_sdpws", "SW-1", group_id=grp_b["group_id"], start_from="blank")

        # Populate and save revision on i1, then soft-delete i2
        bm_par = get_module_registry().get_benchmark_inputs("asce7_parapet_wind")
        ctrl1.load(i1["calculation_id"])
        for k, v in bm_par.items():
            ctrl1.edit_field(i1["calculation_id"], k, str(v))
        ctrl1.save_revision(i1["calculation_id"], "Initial parapet")

        # Edit i1 after revision so it is stale on reopen
        ctrl1.edit_field(i1["calculation_id"], "V_mph", "125.0")

        # Move i3 into grp_a at index 0, rename it, and soft-delete i2
        assert prj1.move_item(i3["calculation_id"], grp_a["group_id"], 0) is True
        assert prj1.rename_item(i3["calculation_id"], "SW-1 Moved") is True
        assert prj1.delete_item(i2["calculation_id"]) is True

        # Project defaults & coming_soon add_item gate
        prj1.set_project_defaults(DesignMethod.LRFD, {"custom": "test"})
        gated_reg = ModuleRegistry()
        gated_reg.register(
            ModuleSpec(
                module_id="future_pt_slab",
                aliases=(),
                category="Concrete / CMU (ACI / TMS)",
                title="Post-tensioned slab",
                subtitle="ACI 318",
                description="Future module",
                code_family="ACI_318",
                default_name="C-99 · PT slab",
                default_group="Level 2",
                preview_type="concrete",
                calculation_callable=None,
                diagram_id=None,
                procedure_md=None,
                maturity=ModuleMaturity.COMING_SOON,
                fields=(),
            )
        )
        gated_prj = ProjectService(repository=prj1.repository, registry=gated_reg)
        gated_prj.set_active_project(prj1.active_project_id)
        with pytest.raises(ValueError, match="coming_soon"):
            gated_prj.add_item("future_pt_slab", "Future Gate Test")

        # Reopen fresh ProjectService + WorkspaceController on same SQLite file
        repo2 = ProjectRepository(db_path=db_path)
        prj2 = ProjectService(repository=repo2)
        prj2.ensure_active_project()
        hist2 = HistoryService(repository=repo2)
        calc2 = CalculationService(kb_service=env["kb"], project_service=prj2)
        ctrl2 = WorkspaceController(
            project_service=prj2,
            calculation_service=calc2,
            history_service=hist2,
            knowledge_base_service=env["kb"],
        )

        defaults2 = prj2.get_project_defaults()
        assert defaults2["default_design_method"] == "LRFD"
        assert defaults2["code_registry"] == {"custom": "test"}

        groups2 = prj2.list_groups()
        grp_a2 = next(g for g in groups2 if g["group_id"] == grp_a["group_id"])
        grp_b2 = next(g for g in groups2 if g["group_id"] == grp_b["group_id"])
        assert grp_a2["is_collapsed"] is True
        assert grp_b2["name"] == "Lateral Walls"

        items2 = prj2.list_items()
        item_ids2 = [it["calculation_id"] for it in items2]
        assert i2["calculation_id"] not in item_ids2
        assert i3["calculation_id"] in item_ids2
        assert i1["calculation_id"] in item_ids2
        # i3 was moved to index 0 of grp_a before i1
        assert item_ids2.index(i3["calculation_id"]) < item_ids2.index(i1["calculation_id"])
        i3_rec = next(it for it in items2 if it["calculation_id"] == i3["calculation_id"])
        assert i3_rec["title"] == "SW-1 Moved"

        # Soft-deleted item revisions remain intact if queried directly in history
        vm_i1 = ctrl2.load(i1["calculation_id"])
        assert vm_i1.current_revision == 1
        assert vm_i1.is_stale is True
        assert vm_i1.draft_inputs["V_mph"] == "125.0"


class TestPurePythonBoundaries:
    def test_zero_qt_imports_in_controllers_models_registry_and_test_suite(self):
        repo_root = Path(__file__).resolve().parent.parent
        paths = [
            *(repo_root / "app" / "controllers").rglob("*.py"),
            *(repo_root / "app" / "models").rglob("*.py"),
            *(repo_root / "app" / "registry").rglob("*.py"),
            Path(__file__).resolve(),
        ]
        for py_file in paths:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name.split(".")[0] != "PySide6", f"Qt import in {py_file}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert node.module.split(".")[0] != "PySide6", f"Qt import in {py_file}"
