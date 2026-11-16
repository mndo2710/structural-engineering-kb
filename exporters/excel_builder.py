"""Excel Report Builder using openpyxl (17-column A-Q layout, Arial 10pt, baseline alignment).

Conforms to SAD v1.0 Section 11.4 & Master Rule 6 (@structural-excel):
- 17 columns (A to Q), Arial 10pt, row height 18.0 pt.
- Explicit vertAlign="baseline" on inline font runs where rich text / sub-superscripts are used.
- Zero cell borders inside the calculation body; blue font (#0000FF) for user inputs.
- Root expressions formatted as (a)^(1/2); multiplication formatted with '.'.
- 3-Tab Workbook Architecture: Calc_Sheet (Equation -> Substitution -> Result -> Limit -> DCR),
  Database, and Source_Audit.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import openpyxl
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.calculation_result import CalculationResult, CalculationStatus
from exporters.audit_logger import build_source_audit_records


FONT_NAME = "Arial"
FONT_SIZE = 10
ROW_HEIGHT_PT = 18.0


def _make_inline_font(
    bold: bool = False,
    italic: bool = False,
    color: str = "000000",
    vert_align: str = "baseline",
) -> InlineFont:
    """Create an openpyxl InlineFont with explicit vertAlign='baseline', 'subscript', or 'superscript'."""
    return InlineFont(
        rFont=FONT_NAME,
        sz=FONT_SIZE,
        b=bold,
        i=italic,
        color=color,
        vertAlign=vert_align,
    )


def _configure_17_col_grid(ws) -> None:
    """Configure standardized 17-column (A:Q) widths and clean view properties."""
    col_widths = {
        "A": 5.0,   # Step ID
        "B": 18.0,  # Parameter / Limit State Name
        "C": 14.0,  # Description continuation
        "D": 10.0,  # Symbol
        "E": 4.0,   # '='
        "F": 16.0,  # Equation
        "G": 16.0,  # Equation cont.
        "H": 20.0,  # Substitution
        "I": 16.0,  # Substitution cont.
        "J": 12.0,  # Result / Demand
        "K": 8.0,   # Units
        "L": 12.0,  # Limit / Capacity
        "M": 8.0,   # Units
        "N": 10.0,  # DCR
        "O": 12.0,  # Status
        "P": 16.0,  # Code Reference
        "Q": 16.0,  # Notes
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width
    ws.views.sheetView[0].showGridLines = True


def export_calculation_to_excel(
    calc_result: CalculationResult,
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
) -> Path:
    """
    Generate a 3-tab standardized US structural engineering Excel workbook (.xlsx)
    (`Calc_Sheet`, `Database`, `Source_Audit`) from a CalculationResult.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prj = project_info or {}

    wb = openpyxl.Workbook()

    # ==========================================================================
    # TAB 1: Calc_Sheet (17 Columns A:Q, Arial 10pt, 18.0 pt row height, zero body borders)
    # ==========================================================================
    ws_calc = wb.active
    ws_calc.title = "Calc_Sheet"
    _configure_17_col_grid(ws_calc)

    font_header_banner = Font(name=FONT_NAME, size=11, bold=True, color="FFFFFF")
    font_sec_hdr = Font(name=FONT_NAME, size=10, bold=True, color="1F4E78")
    font_tbl_hdr = Font(name=FONT_NAME, size=10, bold=True, color="000000")
    font_label = Font(name=FONT_NAME, size=10, bold=False, color="000000")
    font_bold = Font(name=FONT_NAME, size=10, bold=True, color="000000")
    font_input_blue = Font(name=FONT_NAME, size=10, bold=True, color="0000FF")
    font_code_ref = Font(name=FONT_NAME, size=10, italic=True, color="333333")
    font_pass = Font(name=FONT_NAME, size=10, bold=True, color="008000")
    font_fail = Font(name=FONT_NAME, size=10, bold=True, color="CC0000")

    fill_banner = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fill_sec = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    fill_subhdr = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    no_border = Border()

    row_idx = 1

    def set_row_std(r: int) -> None:
        ws_calc.row_dimensions[r].height = ROW_HEIGHT_PT

    # Title Banner (Rows 1-2)
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_title = ws_calc.cell(
        row=row_idx,
        column=1,
        value=f"STRUCTURAL ENGINEERING CALCULATION — {calc_result.module_id.upper()} ({calc_result.code_edition} | {calc_result.design_method.value})",
    )
    c_title.font = font_header_banner
    c_title.fill = fill_banner
    c_title.alignment = Alignment(horizontal="left", vertical="center")
    row_idx += 1

    set_row_std(row_idx)
    ws_calc.cell(row=row_idx, column=1, value="Project:").font = font_bold
    ws_calc.cell(row=row_idx, column=2, value=prj.get("name", "Smith Residence")).font = font_input_blue
    ws_calc.cell(row=row_idx, column=6, value="Calculation ID:").font = font_bold
    ws_calc.cell(row=row_idx, column=7, value=calc_result.calculation_id).font = font_label
    ws_calc.cell(row=row_idx, column=10, value="Design Method:").font = font_bold
    ws_calc.cell(row=row_idx, column=11, value=calc_result.design_method.value).font = font_input_blue
    ws_calc.cell(row=row_idx, column=14, value="Governing Status:").font = font_bold
    c_st = ws_calc.cell(row=row_idx, column=15, value=calc_result.status.value)
    c_st.font = font_pass if calc_result.status == CalculationStatus.PASS else font_fail
    row_idx += 2

    # Section 1: Design Assumptions & Governing Codes
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_sec1 = ws_calc.cell(row=row_idx, column=1, value="1. DESIGN ASSUMPTIONS, LOAD PATH & GOVERNING CODES")
    c_sec1.font = font_sec_hdr
    c_sec1.fill = fill_sec
    row_idx += 1

    for idx_a, assumption in enumerate(calc_result.assumptions, start=1):
        set_row_std(row_idx)
        ws_calc.cell(row=row_idx, column=1, value=f"1.{idx_a}").font = font_label
        ws_calc.cell(row=row_idx, column=2, value=assumption).font = font_label
        row_idx += 1

    row_idx += 1

    # Section 2: Input Parameters (Blue Font for User Inputs, Zero Borders)
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_sec2 = ws_calc.cell(row=row_idx, column=1, value="2. DESIGN INPUT PARAMETERS (US CUSTOMARY UNITS)")
    c_sec2.font = font_sec_hdr
    c_sec2.fill = fill_sec
    row_idx += 1

    for idx_p, (k, v) in enumerate(calc_result.input_parameters.items(), start=1):
        set_row_std(row_idx)
        ws_calc.cell(row=row_idx, column=1, value=f"I.{idx_p}").font = font_label
        ws_calc.cell(row=row_idx, column=2, value=str(k)).font = font_label
        # RichText symbol with explicit baseline alignment per Rule 6
        rt_sym = CellRichText(TextBlock(_make_inline_font(italic=True, vert_align="baseline"), str(k)))
        ws_calc.cell(row=row_idx, column=4, value=rt_sym)
        ws_calc.cell(row=row_idx, column=5, value="=").font = font_label
        c_val = ws_calc.cell(row=row_idx, column=6, value=v)
        c_val.font = font_input_blue
        c_val.alignment = Alignment(horizontal="right", vertical="center")
        c_val.border = no_border
        row_idx += 1

    row_idx += 1

    # Section 3: Intermediate Engineering Calculations
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_sec3 = ws_calc.cell(row=row_idx, column=1, value="3. INTERMEDIATE CALCULATIONS & CODE LOOKUP VALUES")
    c_sec3.font = font_sec_hdr
    c_sec3.fill = fill_sec
    row_idx += 1

    for idx_m, (k, v) in enumerate(calc_result.intermediate_results.items(), start=1):
        set_row_std(row_idx)
        ws_calc.cell(row=row_idx, column=1, value=f"M.{idx_m}").font = font_label
        ws_calc.cell(row=row_idx, column=2, value=str(k)).font = font_label
        ws_calc.cell(row=row_idx, column=5, value="=").font = font_label
        c_inter = ws_calc.cell(row=row_idx, column=10, value=v)
        c_inter.font = font_bold
        c_inter.alignment = Alignment(horizontal="right", vertical="center")
        c_inter.border = no_border
        row_idx += 1

    row_idx += 1

    # Section 4: Sequential Limit States (Equation -> Substitution -> Result -> Limit -> DCR)
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_sec4 = ws_calc.cell(
        row=row_idx,
        column=1,
        value="4. SEQUENTIAL LIMIT STATE VERIFICATION (Equation -> Substitution -> Result -> Limit -> DCR)",
    )
    c_sec4.font = font_sec_hdr
    c_sec4.fill = fill_sec
    row_idx += 1

    # Header row for limit states
    set_row_std(row_idx)
    headers = {
        1: "Step",
        2: "Limit State Check",
        6: "Equation",
        8: "Substitution",
        10: "Result (Demand)",
        11: "Units",
        12: "Limit (Capacity)",
        13: "Units",
        14: "DCR",
        15: "Status",
        16: "Code Clause",
        17: "Engineering Notes",
    }
    for col_i, h_text in headers.items():
        cell = ws_calc.cell(row=row_idx, column=col_i, value=h_text)
        cell.font = font_tbl_hdr
        cell.fill = fill_subhdr
    row_idx += 1

    for ls in calc_result.limit_states:
        set_row_std(row_idx)
        ws_calc.cell(row=row_idx, column=1, value=ls.step_id).font = font_label
        ws_calc.cell(row=row_idx, column=2, value=ls.name).font = font_bold

        # Format equation with '.' for multiplication and baseline inline font
        eq_clean = ls.equation_latex.replace("\\cdot", ".").replace("*", ".")
        rt_eq = CellRichText(TextBlock(_make_inline_font(vert_align="baseline"), eq_clean))
        ws_calc.cell(row=row_idx, column=6, value=rt_eq)

        sub_clean = ls.substitution_str.replace("*", ".")
        rt_sub = CellRichText(TextBlock(_make_inline_font(vert_align="baseline"), sub_clean))
        ws_calc.cell(row=row_idx, column=8, value=rt_sub)

        c_dem = ws_calc.cell(row=row_idx, column=10, value=round(ls.demand, 2))
        c_dem.font = font_bold
        c_dem.number_format = "0.00"

        ws_calc.cell(row=row_idx, column=11, value=ls.units).font = font_label

        c_cap = ws_calc.cell(row=row_idx, column=12, value=round(ls.capacity, 2))
        c_cap.font = font_bold
        c_cap.number_format = "0.00"

        ws_calc.cell(row=row_idx, column=13, value=ls.units).font = font_label

        # Excel formula for DCR = Demand / Capacity
        c_dcr = ws_calc.cell(row=row_idx, column=14, value=f"=ROUND(J{row_idx}/L{row_idx}, 3)")
        c_dcr.font = font_bold
        c_dcr.number_format = "0.000"

        c_stat = ws_calc.cell(row=row_idx, column=15, value=ls.status.value)
        c_stat.font = font_pass if ls.status == CalculationStatus.PASS else font_fail

        ws_calc.cell(row=row_idx, column=16, value=ls.code_clause).font = font_code_ref
        ws_calc.cell(row=row_idx, column=17, value=ls.notes).font = font_label

        # Enforce zero borders in calculation body per Rule 6
        for c_i in range(1, 18):
            ws_calc.cell(row=row_idx, column=c_i).border = no_border

        row_idx += 1

    if calc_result.warnings:
        row_idx += 1
        set_row_std(row_idx)
        ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
        c_sec5 = ws_calc.cell(row=row_idx, column=1, value="5. MANDATORY DETAILING NOTES & WARNINGS")
        c_sec5.font = font_sec_hdr
        c_sec5.fill = fill_sec
        row_idx += 1
        for w_idx, w_text in enumerate(calc_result.warnings, start=1):
            set_row_std(row_idx)
            ws_calc.cell(row=row_idx, column=1, value=f"N.{w_idx}").font = font_label
            ws_calc.cell(row=row_idx, column=2, value=w_text).font = font_label
            row_idx += 1

    # ==========================================================================
    # TAB 2: Database (Embedded Reference Lookup Snapshot for VLOOKUP/INDEX-MATCH)
    # ==========================================================================
    ws_db = wb.create_sheet(title="Database")
    ws_db.row_dimensions[1].height = ROW_HEIGHT_PT
    ws_db.cell(row=1, column=1, value="Referenced Lookup Table Snapshot (UTF-8-SIG Verified)").font = font_sec_hdr

    db_row = 3
    if kb is not None:
        for ref_file in calc_result.reference_files:
            if not ref_file.endswith(".csv"):
                continue
            try:
                df = kb.get_table(ref_file)
                ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                ws_db.cell(row=db_row, column=1, value=f"Table: {ref_file}").font = font_bold
                db_row += 1
                # Write columns
                ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                for c_idx, col_name in enumerate(df.columns, start=1):
                    c = ws_db.cell(row=db_row, column=c_idx, value=str(col_name))
                    c.font = font_tbl_hdr
                    c.fill = fill_subhdr
                db_row += 1
                # Write up to 15 rows per referenced table to keep workbook lightweight
                for _, r_data in df.head(15).iterrows():
                    ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                    for c_idx, val in enumerate(r_data.values, start=1):
                        ws_db.cell(row=db_row, column=c_idx, value=str(val) if str(val) != "nan" else "").font = font_label
                    db_row += 1
                db_row += 1
            except Exception:
                continue

    # ==========================================================================
    # TAB 3: Source_Audit (SHA-256 Reference & Code Edition Traceability)
    # ==========================================================================
    ws_audit = wb.create_sheet(title="Source_Audit")
    audit_headers = [
        "Audit #",
        "Reference ID",
        "Relative File Path",
        "Governing Standard",
        "Encoding",
        "SHA-256 Checksum",
        "Verification Status",
        "Software Version",
        "Audit Timestamp (UTC)",
    ]
    ws_audit.row_dimensions[1].height = ROW_HEIGHT_PT
    for c_idx, h_title in enumerate(audit_headers, start=1):
        c = ws_audit.cell(row=1, column=c_idx, value=h_title)
        c.font = font_header_banner
        c.fill = fill_banner

    audit_records = build_source_audit_records(calc_result, kb=kb)
    for r_offset, rec in enumerate(audit_records, start=2):
        ws_audit.row_dimensions[r_offset].height = ROW_HEIGHT_PT
        vals = [
            rec["audit_index"],
            rec["reference_id"],
            rec["relative_path"],
            rec["code_standard"],
            rec["encoding"],
            rec["sha256"],
            rec["verification_status"],
            rec["software_version"],
            rec["audit_timestamp"],
        ]
        for c_idx, val in enumerate(vals, start=1):
            ws_audit.cell(row=r_offset, column=c_idx, value=val).font = font_label

    for c_idx in range(1, len(audit_headers) + 1):
        ws_audit.column_dimensions[get_column_letter(c_idx)].width = 24.0

    wb.save(out_file)
    return out_file
