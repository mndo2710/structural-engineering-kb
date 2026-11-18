"""Phase 7 (WP-10 + Day 18) exporter, multi-header CSV, and multi-item package tests."""

from pathlib import Path

import openpyxl
from pypdf import PdfReader
import pytest

from app.controllers.workspace_controller import WorkspaceController
from app.registry import get_module_registry
from app.services.calculation_service import CalculationService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from core.common.calculation_result import CalculationStatus, DesignMethod
from exporters.excel_builder import format_math_for_excel
from storage.repositories.project_repository import ProjectRepository


def _benchmark_inputs(module_id: str) -> dict:
    spec = get_module_registry().resolve(module_id)
    return {f.key: f.benchmark_value for f in spec.fields if f.benchmark_value is not None}


def test_resilient_multi_header_csv_parsing_all_database_files():
    """All 73 CSV files in database/ must parse with 0 exceptions and >= 2 columns."""
    kb = KnowledgeBaseService()
    db_root = Path("database")
    csv_files = sorted(db_root.rglob("*.csv"))
    assert len(csv_files) >= 73

    for csv_path in csv_files:
        rel = csv_path.relative_to(db_root).as_posix()
        df = kb.get_table(rel)
        assert len(df.columns) >= 2, f"{rel} parsed with < 2 columns: {list(df.columns)}"
        assert len(df) >= 1, f"{rel} parsed as empty DataFrame"
        raw_rows = kb.get_table_raw_rows(rel)
        assert len(raw_rows) >= 2

    # Specific NDS / ESR multi-header / multi-section tables from Day 14 backlog
    for nds_table in (
        "nds_wood/v2024/NDS-2024_Table_12.2B.csv",
        "nds_wood/v2024/NDS-2024_Table_12.2C.csv",
        "nds_wood/v2024/NDS-2024_Table_12.3.3.csv",
        "nds_wood/v2024/NDS-2024_Table_12.3.3A.csv",
        "nds_wood/v2024/NDS-2024_Table_L1_L7_L8.csv",
        "nds_wood/v2024/NDS-2024_Table_L2_L3_L4_I1.csv",
        "manufacturer_catalogs/simpson_strong_tie/ICC-ESR-2236_Table_1_2_3_4_5.csv",
    ):
        df = kb.get_table(nds_table)
        assert len(df.columns) >= 3
        assert len(df) >= 3

    # Verify ASCE7-22 C30.3-2_C30.3-3 ragged header (9-col banner + 10-col data) keeps all 10 columns & values
    df_c30 = kb.get_table("asce_7/v7_22/ASCE7-22_Table_C30.3-2_C30.3-3.csv")
    assert len(df_c30.columns) == 10
    flat_vals = set(df_c30.astype(str).to_numpy().flatten().tolist())
    assert any("-4.4360" in v for v in flat_vals)
    assert any("1.2360" in v for v in flat_vals)


def test_rule6_math_formatting_and_nds_database_tab_export(tmp_path):
    """Wood fastener/bolt exports populate NDS multi-header tables into Database tab under Rule 6."""
    assert format_math_for_excel(r"Z \cdot C_D \cdot \sqrt{F_c}") == "Z . C_D . (F_c)^(1/2)"
    assert format_math_for_excel(r"\Omega \times V_{max}") == "Ω . V_max"

    kb = KnowledgeBaseService()
    cs = CalculationService(kb_service=kb)
    rs = ReportService(kb_service=kb)

    bolt_res = cs.run_calculation(
        "wood_bolt_lateral",
        _benchmark_inputs("wood_bolt_lateral"),
        DesignMethod.ASD,
    )
    fastener_res = cs.run_calculation(
        "wood_fastener_nds",
        _benchmark_inputs("wood_fastener_nds"),
        DesignMethod.ASD,
    )

    xlsx_path = tmp_path / "wood_bolt_fastener.xlsx"
    rs.export_excel(bolt_res, xlsx_path)
    assert xlsx_path.is_file()

    wb = openpyxl.load_workbook(xlsx_path)
    assert wb.sheetnames == ["Calc_Sheet", "Database", "Source_Audit"]

    ws_calc = wb["Calc_Sheet"]
    assert ws_calc.cell(row=1, column=1).font.name == "Arial"
    assert ws_calc.cell(row=1, column=1).font.size == 10
    assert ws_calc.row_dimensions[1].height == pytest.approx(18.0)
    # 17 columns A..Q must have positive configured widths
    for col_idx in range(1, 18):
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        assert ws_calc.column_dimensions[col_letter].width > 0

    # Zero borders on calculation body rows (skip title row 1)
    for r in range(5, ws_calc.max_row + 1):
        val = ws_calc.cell(row=r, column=1).value
        if val and str(val).startswith("S"):
            border = ws_calc.cell(row=r, column=1).border
            assert border.top is None or border.top.style is None
            assert border.bottom is None or border.bottom.style is None

    ws_db = wb["Database"]
    db_text = "\n".join(
        str(ws_db.cell(row=r, column=c).value or "")
        for r in range(1, ws_db.max_row + 1)
        for c in range(1, min(ws_db.max_column, 8) + 1)
    )
    # Every CSV referenced by wood_bolt_lateral (including multi-header NDS tables) must NOT be skipped
    for ref_file in bolt_res.reference_files:
        if ref_file.lower().endswith(".csv"):
            assert Path(ref_file).name in db_text
    assert "NDS-2024_Table_12.3.3.csv" in db_text
    assert "NDS-2024_Table_12.3.3A.csv" in db_text

    # Also verify wood_fastener_nds multi-header tables export into Database tab without skipping
    xlsx_fast = tmp_path / "wood_fastener.xlsx"
    rs.export_excel(fastener_res, xlsx_fast)
    wb_fast = openpyxl.load_workbook(xlsx_fast)
    ws_fast_db = wb_fast["Database"]
    fast_db_text = "\n".join(
        str(ws_fast_db.cell(row=r, column=c).value or "")
        for r in range(1, ws_fast_db.max_row + 1)
        for c in range(1, min(ws_fast_db.max_column, 8) + 1)
    )
    for ref_file in fastener_res.reference_files:
        if ref_file.lower().endswith(".csv"):
            assert Path(ref_file).name in fast_db_text

    pdf_path = tmp_path / "wood_bolt.pdf"
    rs.export_pdf(bolt_res, pdf_path)
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1
    pdf_txt = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "wood_bolt_lateral" in pdf_txt
    assert "Limit State Verification Summary" in pdf_txt


def test_ordered_multi_item_project_reports_reorder_and_disclosures(tmp_path):
    """Multi-item PDF/XLSX follow exact sidebar order, update after reorder, and disclose STALE/INCOMPLETE."""
    db_file = tmp_path / "project_day18.sqlite"
    repo = ProjectRepository(db_file)
    kb = KnowledgeBaseService()
    ps = ProjectService(repository=repo)
    proj = ps.create_project("Day 18 Residence", "PRJ-D18", "Senior PE")
    p_id = proj["project_id"]

    g_roof = ps.ensure_group("Roof framing", project_id=p_id)["group_id"]
    g_l1 = ps.ensure_group("Level 1", project_id=p_id)["group_id"]

    cs = CalculationService(kb_service=kb)
    ctrl = WorkspaceController(project_service=ps, calculation_service=cs, knowledge_base_service=kb)
    rs = ReportService(kb_service=kb, project_service=ps)

    # Item 1 (C-01): Parapet Wind PASS & saved revision
    item1 = ps.add_item(
        "asce7_parapet_wind",
        "Roof Parapet North",
        group_id=g_roof,
        draft_inputs=_benchmark_inputs("asce7_parapet_wind"),
        project_id=p_id,
    )
    vm1 = ctrl.run(item1["calculation_id"])
    assert vm1.status == CalculationStatus.PASS
    ctrl.save_revision(item1["calculation_id"], "Initial parapet check")

    # Item 2 (C-02): Wood Bolt PASS then edited to become STALE
    item2 = ps.add_item(
        "wood_bolt_lateral",
        "Ridge Beam Bolt",
        group_id=g_roof,
        draft_inputs=_benchmark_inputs("wood_bolt_lateral"),
        project_id=p_id,
    )
    vm2 = ctrl.run(item2["calculation_id"])
    assert vm2.status == CalculationStatus.PASS
    ctrl.save_revision(item2["calculation_id"], "Initial bolt check")
    vm2_stale = ctrl.edit_field(item2["calculation_id"], "n_bolts_per_row", 2)
    assert vm2_stale.is_stale is True

    # Item 3 (C-03): Blank Shear Wall -> INCOMPLETE
    item3 = ps.add_item(
        "wood_shear_wall_sdpws",
        "Grid A Shear Wall",
        group_id=g_l1,
        start_from="blank",
        project_id=p_id,
    )

    xlsx_initial = tmp_path / "package_initial.xlsx"
    pdf_initial = tmp_path / "package_initial.pdf"
    rs.export_project_excel(xlsx_initial, project_id=p_id, controller=ctrl)
    rs.export_project_pdf(pdf_initial, project_id=p_id, controller=ctrl)

    # Check Excel order C-01 -> C-02 -> C-03 and STALE / INCOMPLETE disclosures
    wb1 = openpyxl.load_workbook(xlsx_initial)
    ws_c1 = wb1["Calc_Sheet"]
    calc_lines_1 = [
        " | ".join(str(ws_c1.cell(row=r, column=c).value or "") for c in range(1, 18))
        for r in range(1, ws_c1.max_row + 1)
    ]
    joined_1 = "\n".join(calc_lines_1)
    assert joined_1.index("C-01") < joined_1.index("C-02") < joined_1.index("C-03")
    assert "STALE" in joined_1
    assert "INCOMPLETE" in joined_1

    # Check PDF cover + page order + disclosures
    reader1 = PdfReader(str(pdf_initial))
    assert len(reader1.pages) >= 4
    cover_txt_1 = reader1.pages[0].extract_text() or ""
    assert cover_txt_1.index("C-01") < cover_txt_1.index("C-02") < cover_txt_1.index("C-03")
    full_pdf_1 = "\n".join(p.extract_text() or "" for p in reader1.pages)
    assert "STALE" in full_pdf_1
    assert "INCOMPLETE" in full_pdf_1

    # Reorder C-03 into Roof framing at index 0 (before C-01) and re-export
    moved = ps.move_item(item3["calculation_id"], g_roof, 0)
    assert moved is True

    xlsx_reordered = tmp_path / "package_reordered.xlsx"
    pdf_reordered = tmp_path / "package_reordered.pdf"
    rs.export_project_excel(xlsx_reordered, project_id=p_id, controller=ctrl)
    rs.export_project_pdf(pdf_reordered, project_id=p_id, controller=ctrl)

    wb2 = openpyxl.load_workbook(xlsx_reordered)
    ws_c2 = wb2["Calc_Sheet"]
    joined_2 = "\n".join(
        " | ".join(str(ws_c2.cell(row=r, column=c).value or "") for c in range(1, 18))
        for r in range(1, ws_c2.max_row + 1)
    )
    assert joined_2.index("C-03") < joined_2.index("C-01") < joined_2.index("C-02")

    reader2 = PdfReader(str(pdf_reordered))
    cover_txt_2 = reader2.pages[0].extract_text() or ""
    assert cover_txt_2.index("C-03") < cover_txt_2.index("C-01") < cover_txt_2.index("C-02")

    # Subset item_ids + reconstruction without controller (from HistoryService SQLite)
    pdf_subset = tmp_path / "package_subset_no_ctrl.pdf"
    rs.export_project_pdf(
        pdf_subset,
        project_id=p_id,
        item_ids=[item1["calculation_id"], item2["calculation_id"]],
        controller=None,
    )
    reader_sub = PdfReader(str(pdf_subset))
    sub_cover = reader_sub.pages[0].extract_text() or ""
    assert "C-01" in sub_cover
    assert "C-02" in sub_cover
    assert "C-03" not in sub_cover


def test_four_discipline_e2e_workspace_and_project_reports(tmp_path):
    """E2E integration across C&C, Wood, Steel, and Concrete/CMU in WorkspaceHost/MainWindow and PDF/XLSX."""
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    from gui.widgets.cc_workspace import CCDiagramWidget
    from gui.widgets.wood_workspace import WoodDiagramWidget
    from gui.widgets.workspace_host import DiagramSpecCanvasWidget

    app = QApplication.instance() or QApplication([])

    db_file = tmp_path / "four_discipline_e2e.sqlite"
    repo = ProjectRepository(db_file)
    kb = KnowledgeBaseService()
    ps = ProjectService(repository=repo)
    proj = ps.create_project("V1 Four-Discipline Building", "PRJ-4D", "Senior SE, PE")
    p_id = proj["project_id"]

    g_roof = ps.ensure_group("Roof framing", project_id=p_id)["group_id"]
    g_fnd = ps.ensure_group("Foundations", project_id=p_id)["group_id"]

    cs = CalculationService(kb_service=kb, project_service=ps)
    ctrl = WorkspaceController(project_service=ps, calculation_service=cs, knowledge_base_service=kb)
    rs = ReportService(kb_service=kb, project_service=ps)

    item_cc = ps.add_item(
        "asce7_parapet_wind",
        "Parapet Wind Check",
        group_id=g_roof,
        draft_inputs=_benchmark_inputs("asce7_parapet_wind"),
        project_id=p_id,
    )
    item_wood = ps.add_item(
        "wood_bolt_lateral",
        "Wood Ledger Bolt",
        group_id=g_roof,
        draft_inputs=_benchmark_inputs("wood_bolt_lateral"),
        project_id=p_id,
    )
    item_steel = ps.add_item(
        "aisc_base_plate",
        "Column Base Plate",
        group_id=g_fnd,
        draft_inputs=_benchmark_inputs("aisc_base_plate"),
        project_id=p_id,
    )
    item_conc = ps.add_item(
        "aci318_anchor_tension_shear",
        "Concrete Anchor Bolts",
        group_id=g_fnd,
        draft_inputs=_benchmark_inputs("aci318_anchor_tension_shear"),
        project_id=p_id,
    )

    for entry in (item_cc, item_wood, item_steel, item_conc):
        cid = entry["calculation_id"]
        vm = ctrl.run(cid)
        assert vm.status == CalculationStatus.PASS
        saved = ctrl.save_revision(cid, "V1 four-discipline benchmark")
        assert saved.current_revision == 1

    # Verify MainWindow & WorkspaceHost render all 4 material families cleanly
    win = MainWindow(project_service=ps, kb_service=kb, workspace_controller=ctrl)
    win.select_calculation(item_cc["calculation_id"])
    assert isinstance(win.page_cc.diagram_widget, CCDiagramWidget)
    assert win.page_cc.status_badge.text() == "PASS"

    win.select_calculation(item_wood["calculation_id"])
    assert isinstance(win.page_wood.diagram_widget, WoodDiagramWidget)
    assert win.page_wood.status_badge.text() == "PASS"

    win.select_calculation(item_steel["calculation_id"])
    assert isinstance(win.page_steel.diagram_widget, DiagramSpecCanvasWidget)
    assert win.page_steel.status_badge.text() == "PASS"
    assert win.page_steel.table_limit_states.rowCount() >= 1

    win.select_calculation(item_conc["calculation_id"])
    assert isinstance(win.page_concrete.diagram_widget, DiagramSpecCanvasWidget)
    assert win.page_concrete.status_badge.text() == "PASS"
    assert win.page_concrete.table_limit_states.rowCount() >= 1
    win.close()
    app.processEvents()

    # Export ordered 4-item project Excel + PDF
    xlsx_4d = tmp_path / "four_discipline.xlsx"
    pdf_4d = tmp_path / "four_discipline.pdf"
    rs.export_project_excel(xlsx_4d, project_id=p_id, controller=ctrl)
    rs.export_project_pdf(pdf_4d, project_id=p_id, controller=ctrl)

    wb = openpyxl.load_workbook(xlsx_4d)
    ws_calc = wb["Calc_Sheet"]
    calc_txt = "\n".join(
        " | ".join(str(ws_calc.cell(row=r, column=c).value or "") for c in range(1, 18))
        for r in range(1, ws_calc.max_row + 1)
    )
    assert calc_txt.index("C-01") < calc_txt.index("C-02") < calc_txt.index("C-03") < calc_txt.index("C-04")
    assert "aisc_base_plate" in calc_txt
    assert "aci318_anchor_tension_shear" in calc_txt

    reader = PdfReader(str(pdf_4d))
    assert len(reader.pages) >= 5
    cover = reader.pages[0].extract_text() or ""
    assert cover.index("C-01") < cover.index("C-02") < cover.index("C-03") < cover.index("C-04")
    full_pdf = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "Column Base Plate" in full_pdf
    assert "Concrete Anchor Bolts" in full_pdf
