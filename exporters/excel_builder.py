"""Excel Report Builder using openpyxl (17-column A-Q layout, Arial 10pt, baseline alignment).

Conforms to SAD v1.1 Section 11 & Master Rule 6 (@structural-excel):
- 17 columns (A to Q), Arial 10pt, row height 18.0 pt.
- Explicit vertAlign="baseline" on inline font runs where rich text / sub-superscripts are used.
- Zero cell borders inside the calculation body; blue font (#0000FF) for user inputs.
- Root expressions formatted as (a)^(1/2); multiplication formatted with '.'.
- 3-Tab Workbook Architecture: Calc_Sheet (Equation -> Substitution -> Result -> Limit -> DCR),
  Database (resilient multi-header CSV snapshots), and Source_Audit.
- Supports both single CalculationResult export and ordered multi-item project packages.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union

import openpyxl
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.calculation_result import CalculationResult, CalculationStatus
from core.common.math_markup import math_markup_to_plain_text
from exporters.audit_logger import build_project_source_audit_records


FONT_NAME = "Arial"
FONT_SIZE = 10
ROW_HEIGHT_PT = 18.0

_LEGACY_EXCEL_REPLACEMENTS = (
    (r"\cdot", "."),
    (r"\times", "."),
    (r"\leq", "<="),
    (r"\le", "<="),
    (r"\geq", ">="),
    (r"\ge", ">="),
    (r"\neq", "!="),
    (r"\pm", "+/-"),
    (r"\phi", "phi"),
    (r"\Phi", "Phi"),
    (r"\Omega", "Omega"),
    (r"\Delta", "Delta"),
    (r"\delta", "delta"),
    (r"\theta", "theta"),
    (r"\lambda", "lambda"),
    (r"\alpha", "alpha"),
    (r"\beta", "beta"),
    (r"\gamma", "gamma"),
    (r"\psi", "psi"),
    (r"\epsilon", "epsilon"),
    (r"\parallel", "||"),
    (r"\perp", "perp"),
    (r"\circ", " deg"),
    (r"\ell", "l"),
    ("&ell;", "l"),
    ("·", "."),
    ("×", "."),
)


def _replace_sqrt_with_power(text: str) -> str:
    """Convert Unicode '√(expr)' into Rule 6 '(expr)^(1/2)' notation."""
    out = text
    while "√(" in out:
        idx = out.index("√(")
        depth = 0
        end = -1
        for pos in range(idx + 1, len(out)):
            if out[pos] == "(":
                depth += 1
            elif out[pos] == ")":
                depth -= 1
                if depth == 0:
                    end = pos
                    break
        if end < 0:
            break
        inner = out[idx + 2 : end]
        out = out[:idx] + f"({inner})^(1/2)" + out[end + 1 :]
    return out


def format_math_for_excel(expr: str) -> str:
    """Format restricted LaTeX or legacy math string per Rule 6 ('.' multiplication, (a)^(1/2) roots)."""
    if not expr or not str(expr).strip():
        return ""
    raw = str(expr).strip()
    try:
        plain = math_markup_to_plain_text(raw)
        plain = plain.replace("·", ".").replace("×", ".")
        return _replace_sqrt_with_power(plain)
    except ValueError:
        cleaned = raw
        for src, dst in _LEGACY_EXCEL_REPLACEMENTS:
            cleaned = cleaned.replace(src, dst)
        cleaned = re.sub(r"\\text\{([^}]*)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", cleaned)
        cleaned = re.sub(r"\\sqrt\{([^}]*)\}", r"(\1)^(1/2)", cleaned)
        cleaned = cleaned.replace("\\left", "").replace("\\right", "")
        cleaned = cleaned.replace("{", "").replace("}", "")
        return cleaned.replace("*", ".")


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
        "A": 8.0,   # Step / Item ID
        "B": 20.0,  # Parameter / Limit State Name
        "C": 14.0,  # Description continuation
        "D": 10.0,  # Symbol
        "E": 4.0,   # '='
        "F": 18.0,  # Equation
        "G": 16.0,  # Equation cont.
        "H": 22.0,  # Substitution
        "I": 16.0,  # Substitution cont.
        "J": 12.0,  # Result / Demand
        "K": 8.0,   # Units
        "L": 12.0,  # Limit / Capacity
        "M": 8.0,   # Units
        "N": 10.0,  # DCR
        "O": 14.0,  # Status
        "P": 20.0,  # Code Reference
        "Q": 18.0,  # Notes
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width
    ws.views.sheetView[0].showGridLines = True


def _write_calc_item_to_sheet(
    ws_calc,
    start_row: int,
    calc_result: CalculationResult,
    prj: Dict[str, Any],
    item_meta: Optional[Dict[str, Any]] = None,
) -> int:
    """Write a complete 17-column calculation item block onto ws_calc; return next available row."""
    font_header_banner = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="FFFFFF")
    font_sec_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="1F4E78")
    font_tbl_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    font_label = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color="000000")
    font_bold = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    font_input_blue = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="0000FF")
    font_code_ref = Font(name=FONT_NAME, size=FONT_SIZE, italic=True, color="333333")
    font_pass = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="008000")
    font_fail = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="CC0000")
    font_warn = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="856404")

    fill_banner = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fill_sec = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    fill_subhdr = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    fill_warn = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    no_border = Border()

    row_idx = start_row
    meta = item_meta or {}
    disp_code = meta.get("display_code", "")
    item_title = meta.get("title", calc_result.module_id.upper())
    group_name = meta.get("group_name", "")
    rev_num = meta.get("revision_number", 0)
    is_stale = bool(getattr(calc_result, "is_stale", False))

    def set_row_std(r: int) -> None:
        ws_calc.row_dimensions[r].height = ROW_HEIGHT_PT

    # Item Title Banner
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    prefix = f"{disp_code} · " if disp_code else ""
    c_title = ws_calc.cell(
        row=row_idx,
        column=1,
        value=f"STRUCTURAL ENGINEERING CALCULATION — {prefix}{item_title} ({calc_result.code_edition} | {calc_result.design_method.value})",
    )
    c_title.font = font_header_banner
    c_title.fill = fill_banner
    c_title.alignment = Alignment(horizontal="left", vertical="center")
    row_idx += 1

    # Metadata row
    set_row_std(row_idx)
    ws_calc.cell(row=row_idx, column=1, value="Project:").font = font_bold
    ws_calc.cell(row=row_idx, column=2, value=prj.get("name", "Smith Residence")).font = font_input_blue
    ws_calc.cell(row=row_idx, column=5, value="Group:").font = font_bold
    ws_calc.cell(row=row_idx, column=6, value=group_name or "General").font = font_label
    ws_calc.cell(row=row_idx, column=8, value="Rev:").font = font_bold
    ws_calc.cell(row=row_idx, column=9, value=f"Rev {rev_num}" if rev_num else "Draft").font = font_label
    ws_calc.cell(row=row_idx, column=10, value="Design Method:").font = font_bold
    ws_calc.cell(row=row_idx, column=11, value=calc_result.design_method.value).font = font_input_blue
    ws_calc.cell(row=row_idx, column=14, value="Status:").font = font_bold
    status_disp = f"{calc_result.status.value} (STALE)" if is_stale else calc_result.status.value
    c_st = ws_calc.cell(row=row_idx, column=15, value=status_disp)
    c_st.font = (
        font_warn if is_stale else (font_pass if calc_result.status == CalculationStatus.PASS else font_fail)
    )
    row_idx += 1

    # Explicit disclosure banner if INCOMPLETE, INVALID INPUT, or STALE
    if calc_result.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT) or is_stale:
        set_row_std(row_idx)
        ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
        reasons = "; ".join(getattr(calc_result, "incomplete_reasons", []) or [])
        if is_stale:
            msg = "STATUS DISCLOSURE: STALE — Inputs modified after last run; re-run calculation before relying on results."
        elif calc_result.status == CalculationStatus.INVALID_INPUT:
            msg = f"STATUS DISCLOSURE: INVALID INPUT — {reasons or 'One or more parameters failed validation.'}"
        else:
            msg = f"STATUS DISCLOSURE: INCOMPLETE — {reasons or 'Calculation has not been executed with complete inputs; NOT a verified PASS.'}"
        c_disc = ws_calc.cell(row=row_idx, column=1, value=msg)
        c_disc.font = font_warn
        c_disc.fill = fill_warn
        row_idx += 1

    row_idx += 1

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
        ws_calc.cell(row=row_idx, column=2, value=str(assumption)).font = font_label
        row_idx += 1
    if not calc_result.assumptions:
        set_row_std(row_idx)
        ws_calc.cell(row=row_idx, column=2, value="No assumptions recorded (item not yet computed).").font = font_label
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
        rt_sym = CellRichText(TextBlock(_make_inline_font(italic=True, vert_align="baseline"), str(k)))
        ws_calc.cell(row=row_idx, column=4, value=rt_sym)
        ws_calc.cell(row=row_idx, column=5, value="=").font = font_label
        c_val = ws_calc.cell(row=row_idx, column=6, value=v)
        c_val.font = font_input_blue
        c_val.alignment = Alignment(horizontal="right", vertical="center")
        c_val.border = no_border
        row_idx += 1

    row_idx += 1

    # Section 3: Intermediate Calculations & Ordered 4-Stage CalcStep Trace
    set_row_std(row_idx)
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_sec3 = ws_calc.cell(row=row_idx, column=1, value="3. CALCULATION TRACE & CODE LOOKUP VALUES (4-STAGE LOAD PATH)")
    c_sec3.font = font_sec_hdr
    c_sec3.fill = fill_sec
    row_idx += 1

    trace = getattr(calc_result, "trace", ()) or ()
    if trace:
        set_row_std(row_idx)
        trace_headers = {
            1: "Step",
            2: "Stage & Calculation Step",
            6: "Equation",
            8: "Substitution",
            10: "Result",
            11: "Unit",
            12: "Acceptance",
            14: "DCR",
            15: "Status",
            16: "Code Reference(s)",
            17: "Notes",
        }
        for col_i, h_text in trace_headers.items():
            cell = ws_calc.cell(row=row_idx, column=col_i, value=h_text)
            cell.font = font_tbl_hdr
            cell.fill = fill_subhdr
        row_idx += 1

        for step in trace:
            set_row_std(row_idx)
            ws_calc.cell(row=row_idx, column=1, value=step.step_id).font = font_label
            ws_calc.cell(row=row_idx, column=2, value=f"[Stage {step.stage}] {step.title}").font = font_bold

            eq_txt = format_math_for_excel(step.symbolic)
            if eq_txt:
                ws_calc.cell(row=row_idx, column=6, value=CellRichText(TextBlock(_make_inline_font(vert_align="baseline"), eq_txt)))

            sub_txt = format_math_for_excel(step.substituted)
            if sub_txt:
                ws_calc.cell(row=row_idx, column=8, value=CellRichText(TextBlock(_make_inline_font(vert_align="baseline"), sub_txt)))

            if step.result_value is not None:
                c_res = ws_calc.cell(row=row_idx, column=10, value=step.result_value)
                c_res.font = font_bold
            ws_calc.cell(row=row_idx, column=11, value=step.result_unit or "").font = font_label

            acc_str = ""
            if step.acceptance is not None:
                acc_lim = getattr(step.acceptance, "limit_value", None)
                acc_unit = getattr(step.acceptance, "limit_unit", "")
                acc_desc = getattr(step.acceptance, "description", "")
                if acc_lim is not None:
                    acc_str = f"{acc_lim} {acc_unit}".strip()
                elif acc_desc:
                    acc_str = str(acc_desc)
                else:
                    acc_str = str(step.acceptance)
            ws_calc.cell(row=row_idx, column=12, value=acc_str).font = font_label

            ws_calc.cell(row=row_idx, column=14, value=round(step.dcr, 3) if step.dcr is not None else "—").font = font_bold
            st_val = step.status.value if isinstance(step.status, CalculationStatus) else str(step.status)
            c_step_st = ws_calc.cell(row=row_idx, column=15, value=st_val)
            c_step_st.font = font_pass if st_val == "PASS" else (font_fail if st_val == "FAIL" else font_label)

            refs_str = "; ".join(r.display_label for r in step.refs) if step.refs else ""
            ws_calc.cell(row=row_idx, column=16, value=refs_str).font = font_code_ref
            ws_calc.cell(row=row_idx, column=17, value=step.note).font = font_label

            for c_i in range(1, 18):
                ws_calc.cell(row=row_idx, column=c_i).border = no_border
            row_idx += 1
    else:
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

        eq_clean = format_math_for_excel(ls.equation_latex)
        rt_eq = CellRichText(TextBlock(_make_inline_font(vert_align="baseline"), eq_clean))
        ws_calc.cell(row=row_idx, column=6, value=rt_eq)

        sub_clean = format_math_for_excel(ls.substitution_str)
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

        c_dcr = ws_calc.cell(row=row_idx, column=14, value=f"=ROUND(J{row_idx}/L{row_idx}, 3)" if ls.capacity > 0 else ls.dcr)
        c_dcr.font = font_bold
        c_dcr.number_format = "0.000"

        c_stat = ws_calc.cell(row=row_idx, column=15, value=ls.status.value)
        c_stat.font = font_pass if ls.status == CalculationStatus.PASS else font_fail

        ws_calc.cell(row=row_idx, column=16, value=ls.code_clause).font = font_code_ref
        ws_calc.cell(row=row_idx, column=17, value=ls.notes).font = font_label

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
            ws_calc.cell(row=row_idx, column=2, value=str(w_text)).font = font_label
            row_idx += 1

    return row_idx + 2


def _populate_database_tab(
    ws_db,
    calc_results: Sequence[CalculationResult],
    kb: Optional[KnowledgeBaseService],
) -> None:
    """Populate Database tab with resilient multi-header CSV snapshots (zero silent skips)."""
    font_sec_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="1F4E78")
    font_tbl_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    font_label = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color="000000")
    font_bold = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    fill_subhdr = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    ws_db.row_dimensions[1].height = ROW_HEIGHT_PT
    ws_db.cell(row=1, column=1, value="Referenced Lookup Table Snapshot (UTF-8-SIG Verified)").font = font_sec_hdr

    if kb is None:
        return

    db_row = 3
    seen_csvs: set[str] = set()
    for calc_result in calc_results:
        for ref_file in calc_result.reference_files:
            norm = str(ref_file).strip()
            if not norm.endswith(".csv") or norm in seen_csvs:
                continue
            seen_csvs.add(norm)

            df = kb.get_table(norm)
            ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
            ws_db.cell(row=db_row, column=1, value=f"Table: {norm}").font = font_bold
            db_row += 1

            if not df.empty:
                ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                for c_idx, col_name in enumerate(df.columns, start=1):
                    c = ws_db.cell(row=db_row, column=c_idx, value=str(col_name))
                    c.font = font_tbl_hdr
                    c.fill = fill_subhdr
                db_row += 1

                for _, r_data in df.head(20).iterrows():
                    ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                    for c_idx, val in enumerate(r_data.values, start=1):
                        val_str = str(val)
                        ws_db.cell(row=db_row, column=c_idx, value="" if val_str == "nan" else val_str).font = font_label
                    db_row += 1
            else:
                raw_rows = kb.get_table_raw_rows(norm)
                for raw_r in raw_rows[:20]:
                    ws_db.row_dimensions[db_row].height = ROW_HEIGHT_PT
                    for c_idx, val in enumerate(raw_r, start=1):
                        ws_db.cell(row=db_row, column=c_idx, value=str(val)).font = font_label
                    db_row += 1
            db_row += 1


def _populate_source_audit_tab(
    ws_audit,
    calc_results: Sequence[CalculationResult],
    kb: Optional[KnowledgeBaseService],
) -> None:
    font_header_banner = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="FFFFFF")
    font_label = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color="000000")
    fill_banner = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

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

    audit_records = build_project_source_audit_records(calc_results, kb=kb)
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


def export_calculation_to_excel(
    calc_result: CalculationResult,
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
) -> Path:
    """
    Generate a 3-tab standardized US structural engineering Excel workbook (.xlsx)
    (`Calc_Sheet`, `Database`, `Source_Audit`) from a single CalculationResult.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prj = project_info or {}

    wb = openpyxl.Workbook()
    ws_calc = wb.active
    ws_calc.title = "Calc_Sheet"
    _configure_17_col_grid(ws_calc)

    _write_calc_item_to_sheet(ws_calc, start_row=1, calc_result=calc_result, prj=prj)

    ws_db = wb.create_sheet(title="Database")
    _populate_database_tab(ws_db, [calc_result], kb=kb)

    ws_audit = wb.create_sheet(title="Source_Audit")
    _populate_source_audit_tab(ws_audit, [calc_result], kb=kb)

    wb.save(out_file)
    return out_file


def export_project_to_excel(
    items: Sequence[Dict[str, Any]],
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
) -> Path:
    """
    Generate an ordered multi-item project Excel workbook (.xlsx) preserving
    sidebar group/item order, 17-column A:Q layout, resilient Database tab, and Source_Audit.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prj = project_info or {}

    wb = openpyxl.Workbook()
    ws_calc = wb.active
    ws_calc.title = "Calc_Sheet"
    _configure_17_col_grid(ws_calc)

    font_header_banner = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="FFFFFF")
    font_sec_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="1F4E78")
    font_tbl_hdr = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    font_label = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color="000000")
    font_bold = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="000000")
    font_pass = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="008000")
    font_fail = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="CC0000")
    font_warn = Font(name=FONT_NAME, size=FONT_SIZE, bold=True, color="856404")

    fill_banner = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fill_sec = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    fill_subhdr = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    row_idx = 1
    ws_calc.row_dimensions[row_idx].height = ROW_HEIGHT_PT
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_pkg = ws_calc.cell(
        row=row_idx,
        column=1,
        value=f"PROJECT CALCULATION PACKAGE — {prj.get('name', 'Smith Residence')} ({prj.get('code', 'PRJ-2026-001')})",
    )
    c_pkg.font = font_header_banner
    c_pkg.fill = fill_banner
    row_idx += 2

    # Project Table of Contents in exact sidebar order
    ws_calc.row_dimensions[row_idx].height = ROW_HEIGHT_PT
    ws_calc.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=17)
    c_toc = ws_calc.cell(row=row_idx, column=1, value="PROJECT CALCULATION INDEX (ORDERED BY SIDEBAR TREE)")
    c_toc.font = font_sec_hdr
    c_toc.fill = fill_sec
    row_idx += 1

    ws_calc.row_dimensions[row_idx].height = ROW_HEIGHT_PT
    toc_headers = {
        1: "Item #",
        2: "Calculation Title",
        5: "Group",
        7: "Module ID",
        9: "Code Edition",
        11: "Method",
        12: "Rev",
        13: "DCR",
        15: "Status",
        16: "Stale",
    }
    for col_i, h_txt in toc_headers.items():
        cell = ws_calc.cell(row=row_idx, column=col_i, value=h_txt)
        cell.font = font_tbl_hdr
        cell.fill = fill_subhdr
    row_idx += 1

    calc_results: List[CalculationResult] = []
    for entry in items:
        res: CalculationResult = entry["calc_result"]
        calc_results.append(res)
        is_stale = bool(getattr(res, "is_stale", False))
        rev_num = entry.get("revision_number", 0)

        ws_calc.row_dimensions[row_idx].height = ROW_HEIGHT_PT
        ws_calc.cell(row=row_idx, column=1, value=entry.get("display_code", "")).font = font_bold
        ws_calc.cell(row=row_idx, column=2, value=entry.get("title", res.module_id)).font = font_label
        ws_calc.cell(row=row_idx, column=5, value=entry.get("group_name", "General")).font = font_label
        ws_calc.cell(row=row_idx, column=7, value=res.module_id).font = font_label
        ws_calc.cell(row=row_idx, column=9, value=res.code_edition).font = font_label
        ws_calc.cell(row=row_idx, column=11, value=res.design_method.value).font = font_label
        ws_calc.cell(row=row_idx, column=12, value=rev_num).font = font_label
        dcr_val = (
            round(res.dcr, 2)
            if res.status not in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT)
            else "—"
        )
        ws_calc.cell(row=row_idx, column=13, value=dcr_val).font = font_bold
        c_st = ws_calc.cell(row=row_idx, column=15, value=res.status.value)
        c_st.font = (
            font_pass
            if res.status == CalculationStatus.PASS and not is_stale
            else (font_warn if is_stale or res.status == CalculationStatus.INCOMPLETE else font_fail)
        )
        ws_calc.cell(row=row_idx, column=16, value="STALE" if is_stale else "Current").font = (
            font_warn if is_stale else font_label
        )
        row_idx += 1

    row_idx += 2

    # Write each calculation item in exact order
    for entry in items:
        row_idx = _write_calc_item_to_sheet(
            ws_calc,
            start_row=row_idx,
            calc_result=entry["calc_result"],
            prj=prj,
            item_meta=entry,
        )

    ws_db = wb.create_sheet(title="Database")
    _populate_database_tab(ws_db, calc_results, kb=kb)

    ws_audit = wb.create_sheet(title="Source_Audit")
    _populate_source_audit_tab(ws_audit, calc_results, kb=kb)

    wb.save(out_file)
    return out_file
