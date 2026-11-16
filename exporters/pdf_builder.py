"""PDF Calculation Report Builder using ReportLab (12-Section Layout built around 7-Section Plan Check).

Conforms to SAD v1.0 Section 11.3 & Master Rule 5 (@structural-procedures):
Generates formal US structural engineering PDF calculation reports containing all
12 SAD sections and the mandatory 7-section Plan Check layout (including the 4-column
Summary Checklist Table and SHA-256 reference traceability).
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.calculation_result import CalculationResult
from exporters.audit_logger import build_source_audit_records


def export_calculation_to_pdf(
    calc_result: CalculationResult,
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
) -> Path:
    """
    Generate a 12-section formal PDF calculation report built around the 7-section
    Plan Check layout per SAD v1.0 Section 11.3 and Master Rule 5.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prj = project_info or {}

    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Structural Calculation Report - {calc_result.module_id}",
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=6,
    )
    style_sec = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1F4E78"),
        spaceBefore=10,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "BodyStd",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#212529"),
    )
    style_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )
    style_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=style_cell,
        fontName="Helvetica-Bold",
    )

    story: List[Any] = []
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Project Information & 2. Calculation Title
    story.append(Paragraph(f"STRUCTURAL ENGINEERING CALCULATION REPORT — {calc_result.module_id.upper()}", style_title))
    meta_data = [
        [
            Paragraph("<b>1. Project:</b>", style_cell),
            Paragraph(str(prj.get("name", "Smith Residence")), style_cell),
            Paragraph("<b>2. Calculation ID:</b>", style_cell),
            Paragraph(str(calc_result.calculation_id), style_cell),
        ],
        [
            Paragraph("<b>3. Governing Code:</b>", style_cell),
            Paragraph(f"{calc_result.code_edition} ({calc_result.design_method.value})", style_cell),
            Paragraph("<b>Status / DCR:</b>", style_cell),
            Paragraph(f"<b>{calc_result.status.value} (DCR = {calc_result.dcr:.2f})</b>", style_cell),
        ],
        [
            Paragraph("<b>Engineer:</b>", style_cell),
            Paragraph(str(prj.get("engineer", "Senior Structural Engineer, PE")), style_cell),
            Paragraph("<b>Date:</b>", style_cell),
            Paragraph(date_str, style_cell),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[1.3 * inch, 2.3 * inch, 1.3 * inch, 2.3 * inch])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#DEE2E6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E9ECEF")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # 3 & 4. Section 1 (Plan Check): Design Assumptions, Load Path & Governing Codes
    story.append(Paragraph("SECTION 1: DESIGN ASSUMPTIONS, LOAD PATH & GOVERNING CODES", style_sec))
    for a_text in calc_result.assumptions:
        story.append(Paragraph(f"&bull; {a_text}", style_body))

    # 5. Input Parameters
    story.append(Paragraph("SECTION 2: DESIGN INPUT PARAMETERS & LOAD COMBINATIONS", style_sec))
    in_rows = [[
        Paragraph("<b>Parameter</b>", style_cell_bold),
        Paragraph("<b>Value</b>", style_cell_bold),
        Paragraph("<b>Intermediate Output</b>", style_cell_bold),
        Paragraph("<b>Computed Value</b>", style_cell_bold),
    ]]
    in_items = list(calc_result.input_parameters.items())
    inter_items = list(calc_result.intermediate_results.items())
    max_len = max(len(in_items), len(inter_items))
    for i in range(max_len):
        k_in, v_in = in_items[i] if i < len(in_items) else ("", "")
        k_int, v_int = inter_items[i] if i < len(inter_items) else ("", "")
        in_rows.append([
            Paragraph(str(k_in), style_cell),
            Paragraph(str(v_in), style_cell),
            Paragraph(str(k_int), style_cell),
            Paragraph(str(v_int), style_cell),
        ])
    t_inputs = Table(in_rows, colWidths=[1.9 * inch, 1.7 * inch, 1.9 * inch, 1.7 * inch])
    t_inputs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CED4DA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E9ECEF")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_inputs)

    # 6, 7, 8, 9. Primary Member, Sequential Connection Limit States & Substrate Verification
    story.append(Paragraph("SECTIONS 3–5: PRIMARY MEMBER, CONNECTION LIMIT STATES & SUBSTRATE CHECKS", style_sec))
    ls_rows = [[
        Paragraph("<b>Step</b>", style_cell_bold),
        Paragraph("<b>Limit State &amp; Equation / Substitution</b>", style_cell_bold),
        Paragraph("<b>Code Reference</b>", style_cell_bold),
        Paragraph("<b>Demand</b>", style_cell_bold),
        Paragraph("<b>Capacity</b>", style_cell_bold),
        Paragraph("<b>DCR / Status</b>", style_cell_bold),
    ]]
    for ls in calc_result.limit_states:
        eq_clean = ls.equation_latex.replace("\\cdot", ".").replace("\\max", "max")
        desc_html = f"<b>{ls.name}</b><br/>Eq: {eq_clean}<br/>Sub: {ls.substitution_str}"
        ls_rows.append([
            Paragraph(ls.step_id, style_cell),
            Paragraph(desc_html, style_cell),
            Paragraph(ls.code_clause, style_cell),
            Paragraph(f"{ls.demand:.2f} {ls.units}", style_cell),
            Paragraph(f"{ls.capacity:.2f} {ls.units}", style_cell),
            Paragraph(f"<b>{ls.dcr:.2f} ({ls.status.value})</b>", style_cell),
        ])
    t_ls = Table(ls_rows, colWidths=[0.45 * inch, 3.05 * inch, 1.25 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch])
    t_ls.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CED4DA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DEE2E6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_ls)

    # 10. Section 6 (Plan Check): Mandatory Detailing & Construction Notes
    story.append(Paragraph("SECTION 6: MANDATORY DETAILING & CONSTRUCTION NOTES", style_sec))
    if calc_result.warnings:
        for w_text in calc_result.warnings:
            story.append(Paragraph(f"&bull; {w_text}", style_body))
    else:
        story.append(Paragraph("&bull; Verify all material grades, edge distances, and fastener installations per approved structural drawings.", style_body))

    # 11. Section 7 (Plan Check): 4-Column Summary Calculation & Detailing Checklist Table
    story.append(Paragraph("SECTION 7: SUMMARY CALCULATION & DETAILING CHECKLIST TABLE", style_sec))
    chk_rows = [[
        Paragraph("<b>Step</b>", style_cell_bold),
        Paragraph("<b>Design Verification Item</b>", style_cell_bold),
        Paragraph("<b>Governing Code Reference</b>", style_cell_bold),
        Paragraph("<b>Limit State / Acceptance Equation</b>", style_cell_bold),
    ]]
    for ls in calc_result.limit_states:
        chk_rows.append([
            Paragraph(ls.step_id, style_cell),
            Paragraph(ls.name, style_cell),
            Paragraph(ls.code_clause, style_cell),
            Paragraph(f"{ls.demand:.2f} {ls.units} &le; {ls.capacity:.2f} {ls.units} (DCR = {ls.dcr:.2f} — {ls.status.value})", style_cell),
        ])
    t_chk = Table(chk_rows, colWidths=[0.6 * inch, 2.2 * inch, 1.8 * inch, 2.6 * inch])
    t_chk.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CED4DA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DEE2E6")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_chk)

    # 12. Calculation References and SHA-256 Revision Traceability
    story.append(Paragraph("SECTION 8: REFERENCE MANIFEST & SHA-256 AUDIT TRACEABILITY", style_sec))
    audit_recs = build_source_audit_records(calc_result, kb=kb)
    aud_rows = [[
        Paragraph("<b>Ref ID</b>", style_cell_bold),
        Paragraph("<b>Reference File Path</b>", style_cell_bold),
        Paragraph("<b>SHA-256 Checksum (First 24 Hex)</b>", style_cell_bold),
        Paragraph("<b>Status</b>", style_cell_bold),
    ]]
    for rec in audit_recs:
        sha_short = str(rec["sha256"])[:24] + "..." if len(str(rec["sha256"])) > 24 else str(rec["sha256"])
        aud_rows.append([
            Paragraph(str(rec["reference_id"]), style_cell),
            Paragraph(str(rec["relative_path"]), style_cell),
            Paragraph(sha_short, style_cell),
            Paragraph(str(rec["verification_status"]), style_cell),
        ])
    t_aud = Table(aud_rows, colWidths=[1.1 * inch, 3.3 * inch, 2.0 * inch, 0.8 * inch])
    t_aud.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CED4DA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E9ECEF")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_aud)

    doc.build(story)
    return out_file
