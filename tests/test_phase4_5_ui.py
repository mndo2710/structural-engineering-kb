"""Offscreen PySide6 & Rendering tests for Phase 4 (WP-5/WP-6) & Phase 5 (WP-7/WP-8)."""

import os
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.models import (
    CalcStep,
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
    Quantity,
    RefSpec,
)
from app.registry import get_module_registry
from app.rendering import (
    KATEX_SPIKE_REPORT,
    build_diagram_spec,
    has_webengine_support,
    render_calculation_sheet_html,
)
from app.services.project_service import ProjectService
from gui.dialogs.add_calculation_dialog import AddCalculationDialog
from gui.main_window import MainWindow
from gui.widgets.workspace_host import WorkspaceHost
from storage.repositories.project_repository import ProjectRepository


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_isolated_window(tmp_path, name: str = "ui_test.sqlite3") -> MainWindow:
    repo = ProjectRepository(db_path=tmp_path / name)
    prj = ProjectService(repository=repo)
    return MainWindow(project_service=prj)


class TestPhase4IndependentWorkspaceHostAndMainWindow:
    def test_two_items_same_module_independent_state_in_mainwindow_and_workspace_host(self, tmp_path, qapp):
        win = _make_isolated_window(tmp_path)
        registry = get_module_registry()
        bm = registry.get_benchmark_inputs("wood_bolt_lateral")

        # Add item #1 and item #2 of the exact same module type (wood_bolt_lateral)
        code1 = win._add_calculation_from_data({
            "name": "Bolt Joint #1",
            "group": "Roof framing",
            "template_id": "wood_bolt_lateral",
            "category": "Wood (NDS)",
            "design_method": "ASD",
            "start_from": "blank",
        })
        assert isinstance(win.page_wood, WorkspaceHost)
        assert win.page_wood.status_badge.text() == "INCOMPLETE"
        assert all(edit.text() == "" for edit in win.page_wood._input_edits.values())

        # Populate and run item #1 via UI inputs
        for key, val in bm.items():
            widget = win.page_wood._field_widgets[key]
            if hasattr(widget, "setText"):
                widget.setText(str(val))
                win.page_wood._on_line_edited(key, str(val), widget)
            else:
                idx = widget.findData(str(val))
                widget.setCurrentIndex(idx)
                win.page_wood._on_combo_edited(key, widget)

        win.page_wood.btn_calculate.click()
        assert win.page_wood.status_badge.text() == "PASS"
        dcr_1 = win.page_wood.active_viewmodel.summary.dcr
        assert dcr_1 == pytest.approx(0.82, abs=0.02)

        # Add item #2 of the exact same module type -> must start blank & INCOMPLETE
        code2 = win._add_calculation_from_data({
            "name": "Bolt Joint #2",
            "group": "Level 2",
            "template_id": "wood_bolt_lateral",
            "category": "Wood (NDS)",
            "design_method": "ASD",
            "start_from": "blank",
        })
        assert code2 != code1
        assert win.page_wood.status_badge.text() == "INCOMPLETE"
        assert win.page_wood.table_limit_states.rowCount() == 0
        assert all(edit.text() == "" for edit in win.page_wood._input_edits.values())

        # Switch back to item #1 -> restores item #1's exact inputs and PASS result
        win.select_calculation(code1)
        assert win.page_wood.status_badge.text() == "PASS"
        assert win.page_wood._input_edits["P_demand_lbs"].text() == str(bm["P_demand_lbs"])
        assert win.page_wood.active_viewmodel.summary.dcr == pytest.approx(dcr_1, abs=1e-4)

    def test_edit_updates_diagram_and_stale_flag_and_save_revision_persists(self, tmp_path, qapp):
        win = _make_isolated_window(tmp_path)
        bm = get_module_registry().get_benchmark_inputs("wood_bolt_lateral")

        code = win._add_calculation_from_data({
            "name": "Stale Check Bolt",
            "group": "Roof framing",
            "template_id": "wood_bolt_lateral",
            "category": "Wood (NDS)",
            "design_method": "ASD",
            "start_from": "blank",
        })

        for key, val in bm.items():
            widget = win.page_wood._field_widgets[key]
            if hasattr(widget, "setText"):
                widget.setText(str(val))
                win.page_wood._on_line_edited(key, str(val), widget)
            else:
                widget.setCurrentIndex(widget.findData(str(val)))
                win.page_wood._on_combo_edited(key, widget)

        # Run Calculation -> computes result without creating SQLite revision
        win.page_wood.btn_calculate.click()
        vm_run = win.page_wood.active_viewmodel
        assert vm_run.status == CalculationStatus.PASS
        assert vm_run.is_stale is False
        assert vm_run.current_revision == 0
        assert len(win.history_service.get_history(vm_run.item_id)) == 0

        # Edit geometry input after Run -> immediate DiagramSpec update + STALE flag, still 0 revisions
        tm_edit = win.page_wood._input_edits["t_m_in"]
        tm_edit.setText("2.5")
        win.page_wood._on_line_edited("t_m_in", "2.5", tm_edit)

        vm_stale = win.page_wood.active_viewmodel
        assert vm_stale.is_stale is True
        assert vm_stale.diagram_spec is not None
        assert vm_stale.diagram_spec.geometry_params["t_m_in"] == pytest.approx(2.5)
        assert vm_stale.diagram_spec.is_stale is True
        assert "STALE" in win.page_wood.calc_text.toPlainText()
        assert "STALE" in win.page_wood.lbl_governing.text()
        assert len(win.history_service.get_history(vm_stale.item_id)) == 0

        # Save Revision -> runs & persists immutable Revision 1
        win.page_wood.btn_save_revision.click()
        vm_saved = win.page_wood.active_viewmodel
        assert vm_saved.current_revision == 1
        assert vm_saved.is_stale is False
        assert len(win.history_service.get_history(vm_saved.item_id)) == 1


class TestPhase4SidebarOperationsAndDialog:
    def test_sidebar_reorder_duplicate_rename_delete_and_reload(self, tmp_path, qapp):
        db_file = tmp_path / "sidebar_ops.sqlite3"
        win1 = MainWindow(project_service=ProjectService(repository=ProjectRepository(db_path=db_file)))

        # Verify dynamic status bar counts (F-18)
        assert "Smith Residence" in win1.lbl_status_project.text()
        assert "66 Tables / 26 Procedures" in win1.lbl_status_kb.text()

        # Verify AddCalculationDialog dynamic duplicate source label
        win1.select_calculation("C-02")
        dlg = AddCalculationDialog(win1, registry=win1.registry, active_item_label="C-02 · Truss heel bolt")
        assert "Duplicate C-02" in dlg.radio_duplicate.text()

        # Duplicate C-02, rename it, move it to index 0 of Level 2, and soft-delete C-03
        dup_uuid = win1.duplicate_calculation_item("C-02", new_title="Copied Heel Bolt")
        assert dup_uuid is not None
        assert win1.rename_calculation_item(dup_uuid, "Renamed Heel Bolt") is True
        assert win1.move_calculation_item(dup_uuid, "Level 2", 0) is True
        assert win1.delete_calculation_item("C-03") is True

        # Reopen fresh MainWindow on same SQLite DB and verify persistence
        win2 = MainWindow(project_service=ProjectService(repository=ProjectRepository(db_path=db_file)))
        codes_and_names = [(c["calculation_id"], c["raw_title"], c["group"]) for c in win2.calculations]
        ids_only = [x[0] for x in codes_and_names]
        assert dup_uuid in ids_only
        dup_entry = next(x for x in codes_and_names if x[0] == dup_uuid)
        assert dup_entry[1] == "Renamed Heel Bolt"
        assert dup_entry[2] == "Level 2"
        assert all("Beam seat" not in x[1] for x in codes_and_names)


class TestPhase5OfflineMathRendererAndDiagramBuilders:
    def test_render_calculation_sheet_html_4stage_trace_and_stale_banner(self):
        step1 = CalcStep(
            step_id="S1",
            stage=1,
            title="Bolt End Distance Geometry",
            symbolic=r"e_{\min} = 7 \cdot D",
            substituted=r"7 \cdot 0.625 = 4.375 \text{ in.}",
            variables={"D": Quantity("D", 0.625, "in.")},
            result_value=4.375,
            result_unit="in.",
            refs=(RefSpec("NDS", "2024", "table", "Table 12.5.1A"),),
        )
        step2 = CalcStep(
            step_id="S2",
            stage=2,
            title="Adjusted Lateral Yield Capacity",
            symbolic=r"Z^\prime = Z \cdot C_D \cdot C_{\Delta}",
            substituted=r"604 \cdot 1.00 \cdot 0.69 = 417 \text{ lbs}",
            result_value=417.0,
            result_unit="lbs",
            dcr=0.82,
            status=CalculationStatus.PASS,
            refs=(RefSpec("NDS", "2024", "section", "Sec. 12.3.1"),),
        )
        ls = LimitStateResult(
            step_id="S2",
            name="Bolt Lateral Yield",
            code_clause="NDS Sec. 12.3.1",
            equation_latex=r"Z^\prime = Z \cdot C_D \cdot C_{\Delta}",
            substitution_str="604 * 1.0 * 0.69 = 417 lbs",
            demand=340.0,
            capacity=417.0,
            units="lbs",
            dcr=0.82,
            status=CalculationStatus.PASS,
        )
        res = CalculationResult(
            calculation_id="calc-trace-1",
            module_id="wood_bolt_lateral",
            code_edition="NDS 2024",
            design_method=DesignMethod.ASD,
            input_parameters={"D_in": 0.625},
            limit_states=[ls],
            governing_limit_state=ls,
            demand=340.0,
            capacity=417.0,
            dcr=0.82,
            status=CalculationStatus.PASS,
            trace=(step1, step2),
        )

        rendered = render_calculation_sheet_html(
            result=res,
            code_edition="NDS 2024",
            design_method="ASD",
            is_stale=True,
        )
        assert "Stage 1 — Geometry, Detailing &amp; Applicability Limits" in rendered
        assert "Stage 2 — Primary Force-Transfer Mechanism" in rendered
        assert "STALE" in rendered
        assert "NDS-2024 Table 12.5.1A" in rendered
        assert r"\cdot" not in rendered
        assert "&ell;" not in rendered
        assert "·" in rendered

        assert isinstance(has_webengine_support(), bool)
        assert KATEX_SPIKE_REPORT["cdn_allowed"] is False

    def test_build_diagram_spec_all_19_verified_and_empty_state(self):
        registry = get_module_registry()
        verified_ids = registry.list_canonical_verified_ids()
        assert len(verified_ids) == 19
        for mod_id in verified_ids:
            bm = registry.get_benchmark_inputs(mod_id)
            spec_no_res = build_diagram_spec(mod_id, bm, result=None, is_stale=False)
            assert spec_no_res.has_geometry is True
            assert spec_no_res.has_engine_result is False
            assert spec_no_res.forces == ()
            assert len(spec_no_res.shapes) >= 1

        # Unimplemented / future module returns explicit empty-state DiagramSpec
        future_spec = build_diagram_spec("future_pt_slab", {}, result=None)
        assert future_spec.is_empty_state is True
        assert future_spec.has_geometry is False

    def test_offline_katex_assets_and_webengine_support(self):
        from pathlib import Path
        from app.rendering.math_renderer import build_offline_katex_document, get_katex_assets_dir

        assets_dir = get_katex_assets_dir()
        assert (assets_dir / "katex.min.js").is_file()
        assert (assets_dir / "katex.min.css").is_file()
        assert "http://" not in (assets_dir / "katex.min.js").read_text(encoding="utf-8")
        assert "https://" not in (assets_dir / "katex.min.js").read_text(encoding="utf-8")
        assert has_webengine_support() is True

        doc_html = build_offline_katex_document(None, "NDS 2024", "ASD")
        assert "katex.min.css" in doc_html
        assert "katex.min.js" in doc_html
        assert "http://" not in doc_html and "https://" not in doc_html


class TestReleaseGateAuxiliaryPagesAndExportButtons:
    def test_pages_1_6_7_workspace_export_and_prefix_cleanliness(self, qapp, tmp_path):
        from types import SimpleNamespace
        from PySide6.QtCore import Qt
        import openpyxl
        from pypdf import PdfReader

        class _FakeSyncService:
            def __init__(self):
                self.called = False

            def sync_knowledge_base(self):
                self.called = True
                return SimpleNamespace(
                    connection_status=SimpleNamespace(value="OFFLINE"),
                    status="offline_cached",
                    files_synced=0,
                )

        fake_sync = _FakeSyncService()
        repo = ProjectRepository(db_path=tmp_path / "gate_ui.sqlite3")
        prj = ProjectService(repository=repo)
        win = MainWindow(project_service=prj, cloud_sync_service=fake_sync)
        win.report_output_dir = tmp_path / "pkg_exports"
        for host in (win.page_cc, win.page_wood, win.page_steel, win.page_concrete):
            host.export_dir = tmp_path / "item_exports"

        # 1. Verify no duplicate "C-XX · C-YY ·" title formatting on add/duplicate
        win.select_calculation("C-01")
        dup_id = win.duplicate_calculation_item("C-01")
        assert dup_id is not None
        dup_entry = win._find_calc_entry(dup_id)
        assert dup_entry is not None
        assert dup_entry["name"].count("C-") == 1

        # 2. WorkspaceHost single-item export buttons on Panel 1
        win.select_calculation("C-02")
        assert win.page_wood.btn_export_xlsx is not None
        assert win.page_wood.btn_export_pdf is not None
        win.page_wood.btn_export_xlsx.click()
        win.page_wood.btn_export_pdf.click()
        assert any((tmp_path / "item_exports").glob("*.xlsx"))
        assert any((tmp_path / "item_exports").glob("*.pdf"))

        # 3. Page 6: Deliverable Reports with subset unchecked item
        win._switch_to_page(6)
        assert win.list_report_items.count() >= 3
        # Uncheck the last item to test subset selection
        win.list_report_items.item(win.list_report_items.count() - 1).setCheckState(Qt.Unchecked)
        unchecked_label = win.list_report_items.item(win.list_report_items.count() - 1).text().split(" ")[0]
        win.btn_export_project_xlsx.click()
        win.btn_export_project_pdf.click()
        xlsx_files = list((tmp_path / "pkg_exports").glob("*.xlsx"))
        pdf_files = list((tmp_path / "pkg_exports").glob("*.pdf"))
        assert len(xlsx_files) == 1
        assert len(pdf_files) == 1
        wb = openpyxl.load_workbook(xlsx_files[0])
        assert wb.sheetnames == ["Calc_Sheet", "Database", "Source_Audit"]
        pdf_text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf_files[0])).pages)
        assert "C-01" in pdf_text
        assert unchecked_label not in (PdfReader(str(pdf_files[0])).pages[0].extract_text() or "")

        # 4. Page 7: Verify Local KB (92 SHA-256) & Cloud Sync buttons
        win._switch_to_page(7)
        win.btn_verify_kb.click()
        assert "92/92 verified" in win.lbl_settings_status.text()
        win.btn_sync_cloud.click()
        assert fake_sync.called is True
        assert "offline_cached" in win.lbl_settings_status.text()

        # 5. Page 1: Create & Activate Project via UI
        win._switch_to_page(1)
        initial_count = win.list_projects_widget.count()
        win.txt_new_project_name.setText("UI Created Tower")
        win.txt_new_project_code.setText("PRJ-UI-99")
        win.txt_new_project_engineer.setText("Lead SE, PE")
        win.btn_create_project.click()
        assert win.list_projects_widget.count() == initial_count + 1
        assert "UI Created Tower" in win.lbl_active_project_summary.text()
        assert win.calc_list.count() == 0

        win.close()
