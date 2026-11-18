"""Unit and regression tests for PySide6 GUI workspaces, ModuleRegistry (WP-3), and WP-0b Live-Data Safety."""

import ast
import json
import os
from pathlib import Path
import pytest

# Configure Qt for headless/offscreen execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.models import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
from app.registry import ModuleMaturity, ModuleRegistry, ModuleSpec, get_module_registry
from app.registry.module_registry import build_default_registry
from app.services.calculation_service import CalculationService
from app.services.project_service import ProjectService
from core.common.exceptions import StructuralEngineeringError
from storage.repositories.project_repository import ProjectRepository
from gui.dialogs.add_calculation_dialog import AddCalculationDialog
from gui.main_window import MainWindow
from gui.widgets.base_workspace import BaseCalculationWorkspace, StatusBadgeWidget
from gui.widgets.cc_workspace import CCCalculationWorkspace
from gui.widgets.wood_workspace import WoodCalculationWorkspace


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_calc_result():
    ls = LimitStateResult(
        step_id="S1",
        name="Parapet Wind Suction",
        code_clause="ASCE 7-22 Sec. 30.9",
        equation_latex="p = q_p \\cdot ((GC_{pn}) - (GC_{pi}))",
        substitution_str="25.5 psf * (1.8 - (-0.18))",
        demand=50.5,
        capacity=60.0,
        units="psf",
        dcr=0.84,
        status=CalculationStatus.PASS,
    )
    return CalculationResult(
        calculation_id="test-cc-01",
        module_id="cc_parapet",
        code_edition="ASCE 7-22",
        design_method=DesignMethod.ASD,
        input_parameters={"V_mph": 115, "h_ft": 30, "parapet_ht_ft": 3.5},
        assumptions=["Risk Category II", "Exposure C"],
        intermediate_results={"qp_psf": 25.5, "GCpn": 1.8},
        limit_states=[ls],
        governing_limit_state=ls,
        demand=50.5,
        capacity=60.0,
        dcr=0.84,
        status=CalculationStatus.PASS,
        reference_files=["database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv"],
        software_version="1.0.0",
    )


class TestStatusBadgeWidget:
    def test_status_badge_updates(self, qapp):
        badge = StatusBadgeWidget()
        assert badge.text() == "INCOMPLETE"

        badge.update_status(CalculationStatus.PASS)
        assert badge.text() == "PASS"

        badge.update_status(CalculationStatus.FAIL)
        assert badge.text() == "FAIL"

        badge.update_status(CalculationStatus.REQUIRES_REVIEW)
        assert badge.text() == "REQUIRES REVIEW"

        badge.update_status(CalculationStatus.INVALID_INPUT)
        assert badge.text() == "INVALID INPUT"


class TestBaseCalculationWorkspace:
    def test_workspace_initialization_and_blank_safety(self, qapp):
        ws = BaseCalculationWorkspace(module_title="Parapet Wind", default_code="ASCE 7-22")
        assert ws.get_selected_design_method() == DesignMethod.ASD
        assert ws.status_badge.text() == "INCOMPLETE"
        assert ws.table_limit_states.rowCount() == 0
        assert ws.lbl_dcr_val.text() == "—"
        assert ws.diagram_widget.has_result is False
        assert ws.diagram_widget.c_delta is None
        assert "Douglas Fir-Larch" not in ws.lbl_code_basis.text()
        assert "604 lb" not in ws.calc_text.toPlainText()
        assert "&ell;" not in ws.calc_text.toHtml()

        ws.radio_lrfd.setChecked(True)
        assert ws.get_selected_design_method() == DesignMethod.LRFD

    def test_workspace_display_results(self, qapp, sample_calc_result):
        ws = BaseCalculationWorkspace(module_title="Parapet Wind", default_code="ASCE 7-22")
        ws.display_results(sample_calc_result)

        assert ws.status_badge.text() == "PASS"
        assert ws.dcr_bar.value() == 84
        assert "Parapet Wind Suction" in ws.lbl_governing.text()
        assert ws.table_limit_states.rowCount() == 1
        assert ws.table_limit_states.item(0, 0).text() == "S1"
        assert ws.table_limit_states.item(0, 5).text() == "0.84"
        assert ws.diagram_widget.has_result is True
        assert ws.diagram_widget.c_delta is None


class TestWP0bLiveDataSafetyAndValidation:
    def test_blank_cc_and_wood_workspaces_start_incomplete(self, qapp):
        cc_ws = CCCalculationWorkspace(start_blank=True)
        assert cc_ws.status_badge.text() == "INCOMPLETE"
        assert cc_ws.table_limit_states.rowCount() == 0
        assert cc_ws.lbl_dcr_val.text() == "—"
        assert cc_ws._current_result is None
        assert cc_ws.diagram_widget.has_result is False
        assert all(edit.text() == "" for edit in cc_ws._input_edits.values())

        wood_ws = WoodCalculationWorkspace(start_blank=True)
        assert wood_ws.status_badge.text() == "INCOMPLETE"
        assert wood_ws.table_limit_states.rowCount() == 0
        assert wood_ws.lbl_dcr_val.text() == "—"
        assert wood_ws._current_result is None
        assert wood_ws.diagram_widget.has_result is False
        assert wood_ws.diagram_widget.c_delta is None
        assert all(edit.text() == "" for edit in wood_ws._input_edits.values())

        # Clear an active populated workspace to blank
        wood_ws.select_submodule("wood_bolt_lateral", start_blank=False)
        assert wood_ws._current_result is not None
        assert wood_ws.diagram_widget.c_delta == pytest.approx(0.69, abs=0.01)

        wood_ws.clear_inputs_to_blank()
        assert wood_ws.status_badge.text() == "INCOMPLETE"
        assert wood_ws.table_limit_states.rowCount() == 0
        assert wood_ws.lbl_dcr_val.text() == "—"
        assert wood_ws.diagram_widget.c_delta is None
        assert wood_ws.diagram_widget.has_result is False

    def test_blank_and_invalid_numeric_input_validation(self, qapp):
        cc_ws = CCCalculationWorkspace(start_blank=True)
        # Submitting blank required inputs yields INCOMPLETE and never invokes engine
        cc_ws.btn_calculate.click()
        assert cc_ws.status_badge.text() == "INCOMPLETE"
        assert cc_ws._current_result is None
        assert cc_ws.table_limit_states.rowCount() == 0

        # Populate benchmark defaults, then corrupt V_mph with non-numeric text
        cc_ws.load_benchmark_defaults()
        cc_ws._input_edits["V_mph"].setText("abc")
        cc_ws.btn_calculate.click()
        assert cc_ws.status_badge.text() == "INVALID INPUT"
        assert "V_mph" in cc_ws.lbl_governing.text()
        assert "V_mph" in cc_ws.calc_text.toPlainText()
        assert cc_ws._current_result is None

        # Same check on Wood workspace
        wood_ws = WoodCalculationWorkspace(start_blank=True)
        wood_ws.btn_calculate.click()
        assert wood_ws.status_badge.text() == "INCOMPLETE"

        wood_ws.load_benchmark_defaults()
        wood_ws._input_edits["D_in"].setText("not-a-number")
        wood_ws.btn_calculate.click()
        assert wood_ws.status_badge.text() == "INVALID INPUT"
        assert "D_in" in wood_ws.lbl_governing.text()
        assert "D_in" in wood_ws.calc_text.toPlainText()


class TestWP3ModuleRegistryAndGating:
    def test_registry_uniqueness_aliases_and_procedures(self):
        registry = get_module_registry()

        # 19 canonical verified modules (5 C&C + 5 Wood + 6 Steel + 3 Concrete/CMU) + 3 preset Wood templates = 22
        canonical_ids = registry.list_canonical_verified_ids()
        assert len(canonical_ids) == 19
        assert len(set(canonical_ids)) == 19
        assert len(registry.list_modules(maturity=ModuleMaturity.VERIFIED)) == 22

        # Duplicate module_id or alias detection
        dup_reg = ModuleRegistry()
        spec_a = registry.resolve("asce7_parapet_wind")
        dup_reg.register(spec_a)
        with pytest.raises(ValueError, match="Duplicate"):
            dup_reg.register(spec_a)

        dup_alias = ModuleSpec(
            module_id="other_id",
            aliases=("cc_parapet",),
            category="Loads (ASCE 7)",
            title="Other",
            subtitle="Sub",
            description="Desc",
            code_family="ASCE_7",
            default_name="Other",
            default_group="General",
            preview_type="loads",
            calculation_callable=None,
            fields=(),
            diagram_id=None,
            procedure_md=None,
            maturity=ModuleMaturity.COMING_SOON,
        )
        with pytest.raises(ValueError, match="Duplicate"):
            dup_reg.register(dup_alias)

        # Alias resolution
        assert registry.resolve("cc_parapet").module_id == "asce7_parapet_wind"
        assert registry.resolve("wood_bolt_nds").module_id == "wood_bolt_lateral"
        assert registry.resolve("wood_nail_lateral").preset_inputs["fastener_category"] == "Common Nail"
        assert registry.resolve("wood_screw_withdrawal").preset_inputs["fastener_category"] == "Lag Screw"
        assert registry.resolve("wood_combined_lateral_withdrawal").preset_inputs["fastener_category"] == "Lag Screw"

        # Dynamic code edition resolution (never NDS 2018)
        assert registry.resolve_code_display("wood_bolt_lateral") == "NDS 2024"
        assert registry.resolve_code_display("asce7_parapet_wind") == "ASCE 7-22"
        assert registry.resolve_code_display("aisc_shear_tab") == "AISC 360-22"
        assert registry.resolve_code_display("ACI_TMS") == "ACI 318-19 / TMS 402-22"
        assert "NDS 2018" not in registry.resolve_code_display("wood_bolt_lateral")

        # Manifest procedure existence for every registered module with procedure_md
        repo_root = Path(__file__).resolve().parent.parent
        manifest = json.loads((repo_root / "config" / "reference_manifest.json").read_text(encoding="utf-8"))
        manifest_paths = {ref["relative_path"] for ref in manifest["references"]}
        for spec in registry.list_modules():
            if spec.procedure_md:
                assert (repo_root / spec.procedure_md).exists(), f"Missing procedure file: {spec.procedure_md}"
                assert spec.procedure_md in manifest_paths, f"Procedure not in manifest: {spec.procedure_md}"

    def test_calculation_service_gating_and_presets(self):
        cs = CalculationService()
        assert len(cs.list_supported_modules()) == 19

        # All 9 Day 15 Steel & Day 16 Concrete/CMU modules are now VERIFIED & executable
        for mod_id in (
            "aisc_shear_tab",
            "aisc_bolt_bearing",
            "aisc_welded_connection",
            "aisc_angle_connection",
            "aisc_base_plate",
            "aisc_hss_connection",
            "aci318_anchor_tension_shear",
            "tms402_cmu_anchorage",
            "tms402_embedded_post",
        ):
            res_mod = cs.run_calculation(mod_id, {}, DesignMethod.ASD)
            assert res_mod.status in (CalculationStatus.PASS, CalculationStatus.FAIL)

        # Verify COMING_SOON gating on a custom test ModuleRegistry
        gated_reg = ModuleRegistry()
        gated_reg.register(
            ModuleSpec(
                module_id="future_pt_slab",
                aliases=(),
                category="Concrete / CMU (ACI / TMS)",
                title="Post-tensioned slab (future)",
                subtitle="ACI 318 Ch. 8",
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
        gated_cs = CalculationService(registry=gated_reg)
        with pytest.raises(StructuralEngineeringError, match="coming_soon"):
            gated_cs.run_calculation("future_pt_slab", {}, DesignMethod.ASD)

        # Specialized Wood template presets propagate to unified fastener engine
        res = cs.run_calculation("wood_nail_lateral", {"n_fasteners": 6, "V_demand_lbs": 650.0, "T_demand_lbs": 0.0, "D_in": 0.148, "L_in": 3.0}, DesignMethod.ASD)
        assert res.status == CalculationStatus.PASS
        assert "Common" in res.assumptions[0] or res.input_parameters.get("fastener_type") is not None


class TestMainWindow:
    @staticmethod
    def _isolated_main_window(tmp_path: Path) -> MainWindow:
        ps = ProjectService(ProjectRepository(db_path=tmp_path / "test_mw.sqlite3"))
        return MainWindow(project_service=ps)

    def test_main_window_init_and_navigation(self, qapp, tmp_path):
        win = self._isolated_main_window(tmp_path)
        assert win.nav_list.count() == 4
        assert win.stacked_pages.count() == 8

        # NDS 2024 resolved dynamically (never NDS 2018)
        assert "NDS 2024" in win.lbl_calc_title.text()
        for calc in win.calculations:
            assert "NDS 2018" not in calc["title"]

        # C-01 routed to Wood workspace (page index 3)
        win.select_calculation("C-01")
        assert win.stacked_pages.currentIndex() == 3

        # C-03 (Steel) and C-04 (Concrete) start in clean INCOMPLETE state
        win.select_calculation("C-03")
        assert win.stacked_pages.currentIndex() == 4
        assert "Beam seat" in win.lbl_calc_title.text()
        assert win.page_steel.status_badge.text() == "INCOMPLETE"
        assert win.page_steel.table_limit_states.rowCount() == 0

        win.select_calculation("C-04")
        assert win.stacked_pages.currentIndex() == 5
        assert win.page_concrete.status_badge.text() == "INCOMPLETE"
        assert win.page_concrete.table_limit_states.rowCount() == 0

        # Top nav checks
        win.nav_list.setCurrentRow(1)
        assert win.stacked_pages.currentIndex() == 1
        win.nav_list.setCurrentRow(2)
        assert win.stacked_pages.currentIndex() == 6

        # C-02 Wood workspace
        win.select_calculation("C-02")
        assert win.stacked_pages.currentIndex() == 3
        assert "Truss heel bolt" in win.lbl_calc_title.text()
        win.close()

    def test_add_blank_calculation_opens_incomplete_with_empty_inputs(self, qapp, tmp_path):
        win = self._isolated_main_window(tmp_path)
        win._add_calculation_from_data(
            {
                "name": "C-06 · New Parapet Check",
                "group": "Roof framing",
                "template_id": "asce7_parapet_wind",
                "category": "Loads (ASCE 7)",
                "design_method": "ASD",
                "start_from": "blank",
            }
        )
        assert win.stacked_pages.currentIndex() == 2
        assert win.page_cc.status_badge.text() == "INCOMPLETE"
        assert win.page_cc.table_limit_states.rowCount() == 0
        assert win.page_cc.lbl_dcr_val.text() == "—"
        assert all(e.text() == "" for e in win.page_cc._input_edits.values())
        win.close()

    def test_sidebar_collapse_toggle(self, qapp, tmp_path):
        win = self._isolated_main_window(tmp_path)
        win.show()
        assert not win.is_sidebar_collapsed
        assert not win.sidebar_expanded_widget.isHidden()
        assert win.sidebar_collapsed_widget.isHidden()

        win.toggle_sidebar()
        assert win.is_sidebar_collapsed
        assert win.sidebar_expanded_widget.isHidden()
        assert not win.sidebar_collapsed_widget.isHidden()

        win.toggle_sidebar()
        assert not win.is_sidebar_collapsed
        assert not win.sidebar_expanded_widget.isHidden()
        assert win.sidebar_collapsed_widget.isHidden()
        win.close()

    def test_segmented_design_method_toggle(self, qapp, tmp_path):
        win = self._isolated_main_window(tmp_path)
        assert win._current_design_method == DesignMethod.ASD

        win.set_active_design_method(DesignMethod.LRFD)
        assert win._current_design_method == DesignMethod.LRFD

        win.set_active_design_method(DesignMethod.ASD)
        assert win._current_design_method == DesignMethod.ASD
        win.close()


class TestAddCalculationDialog:
    def test_add_calc_dialog_init(self, qapp):
        dialog = AddCalculationDialog()
        assert dialog.list_categories.count() == 5
        assert dialog.list_categories.currentRow() == 2
        assert "WOOD CONNECTIONS" in dialog.lbl_category_header.text()
        assert dialog.btn_add_and_open.isEnabled()

        # Verify Recent parapet subtitle fix (ASCE 7-22 Sec. 30.9, not Sec. 29.4)
        recent_parapet = [t for t in dialog.TEMPLATES_DATA["Recent"] if t["id"] == "asce7_parapet_wind"][0]
        assert "30.9" in recent_parapet["subtitle"]
        assert "29.4" not in recent_parapet["subtitle"]

    def test_add_calc_dialog_category_switching_and_coming_soon_gating(self, qapp):
        dialog = AddCalculationDialog()
        # Switch to Steel (AISC), row 3 -> all 6 Steel modules VERIFIED & enabled
        dialog.list_categories.setCurrentRow(3)
        assert "STEEL CONNECTIONS (AISC)" in dialog.lbl_category_header.text()
        assert len(dialog._card_widgets) == 6
        assert "[COMING SOON]" not in dialog._card_widgets[0].title
        assert dialog.btn_add_and_open.isEnabled()

        # Switch to Concrete / CMU (ACI / TMS), row 4 -> all 3 Concrete/CMU modules VERIFIED & enabled
        dialog.list_categories.setCurrentRow(4)
        assert len(dialog._card_widgets) == 3
        assert "[COMING SOON]" not in dialog._card_widgets[0].title
        assert dialog.btn_add_and_open.isEnabled()

        # Switch back to Loads (ASCE 7), row 1 -> VERIFIED enabled
        dialog.list_categories.setCurrentRow(1)
        assert dialog.btn_add_and_open.isEnabled()

        # Verify COMING_SOON gating in AddCalculationDialog using a custom test registry
        gated_reg = build_default_registry()
        gated_reg.register(
            ModuleSpec(
                module_id="future_pt_slab",
                aliases=(),
                category="Concrete / CMU (ACI / TMS)",
                title="Post-tensioned slab (future)",
                subtitle="ACI 318 Ch. 8",
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
        gated_dialog = AddCalculationDialog(registry=gated_reg)
        gated_dialog.list_categories.setCurrentRow(4)
        assert len(gated_dialog._card_widgets) == 4
        assert "[COMING SOON]" in gated_dialog._card_widgets[-1].title
        gated_dialog._on_template_selected("future_pt_slab")
        assert not gated_dialog.btn_add_and_open.isEnabled()

    def test_add_calc_dialog_get_data(self, qapp):
        dialog = AddCalculationDialog()
        data = dialog.get_calculation_data()
        assert "name" in data
        assert "group" in data
        assert "template_id" in data
        assert "category" in data
        assert data["design_method"] == "ASD"
        assert data["start_from"] == "blank"


class TestCleanArchitectureBoundaries:
    def test_zero_prohibited_imports_in_gui_and_pure_app_layers(self):
        repo_root = Path(__file__).resolve().parent.parent
        prohibited_gui_roots = {"core", "storage", "cloud", "exporters"}

        for py_file in (repo_root / "gui").rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        assert top not in prohibited_gui_roots, f"Prohibited import '{alias.name}' in {py_file}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    assert top not in prohibited_gui_roots, f"Prohibited import '{node.module}' in {py_file}"

        for app_subdir in ("models", "registry"):
            for py_file in (repo_root / "app" / app_subdir).rglob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert alias.name.split(".")[0] != "PySide6", f"Qt import in {py_file}"
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module.split(".")[0] != "PySide6", f"Qt import in {py_file}"
