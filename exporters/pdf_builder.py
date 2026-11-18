"""PDF Report Builder using ReportLab (12-section Plan Check layout + multi-item packages).

Consumes CalculationResult (including WP-2 CalcStep trace grouped by Stage 1..4)
and WP-8 DiagramSpec schematics to produce deterministic, offline Plan-Check PDFs
for both single calculation items and ordered multi-item project packages.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union
from xml.sax.saxutils import escape as xml_escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import DiagramSpec
from app.rendering.diagram_builders import build_diagram_spec
from app.rendering.math_renderer import STAGE_TITLES, safe_markup_to_html
from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.calculation_result import (
    AcceptanceCriterion,
    CalcStep,
    CalculationResult,
    CalculationStatus,
)
from exporters.audit_logger import build_project_source_audit_records, build_source_audit_records


_ENTITY_REPLACEMENTS = {
    "&le;": "≤",
    "&ge;": "≥",
    "&ne;": "≠",
    "&bull;": "•",
    "&rarr;": "→",
    "&larr;": "←",
    "&harr;": "↔",
    "&ell;": "ℓ",
    "&times;": "×",
    "&middot;": "·",
    "&plusmn;": "±",
    "&deg;": "°",
    "&ndash;": "–",
    "&mdash;": "—",
    "&nbsp;": " ",
    "&phi;": "φ",
    "&Phi;": "Φ",
    "&Omega;": "Ω",
    "&Delta;": "Δ",
    "&delta;": "δ",
    "&theta;": "θ",
    "&lambda;": "λ",
    "&alpha;": "α",
    "&beta;": "β",
    "&gamma;": "γ",
    "&psi;": "ψ",
}

_STRAY_AMP_RE = re.compile(r"&(?!lt;|gt;|amp;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)")


def _xml_text(value: Any) -> str:
    """Escape plain text safely for ReportLab Paragraph XML."""
    return xml_escape("" if value is None else str(value))


def _format_math_for_pdf(expr: str) -> str:
    """Convert restricted LaTeX / markup string into ReportLab-safe rich XML."""
    if not expr or not str(expr).strip():
        return ""
    rendered = safe_markup_to_html(str(expr))
    rendered = rendered.replace("<br>", "<br/>").replace("<BR>", "<br/>")
    for entity, ch in _ENTITY_REPLACEMENTS.items():
        rendered = rendered.replace(entity, ch)
    rendered = re.sub(r"</?(?:span|div)[^>]*>", "", rendered)
    rendered = _STRAY_AMP_RE.sub("&amp;", rendered)
    return rendered


def _hex_to_rl(hex_color: str, fallback: Any = colors.HexColor("#343a40")) -> Any:
    try:
        text = str(hex_color or "").strip()
        if text.startswith("#") and len(text) in (4, 7):
            return colors.HexColor(text)
    except Exception:
        pass
    return fallback


def _status_display(calc_result: CalculationResult) -> str:
    base = calc_result.status.value
    if getattr(calc_result, "is_stale", False) and base not in (
        CalculationStatus.INCOMPLETE.value,
        CalculationStatus.INVALID_INPUT.value,
    ):
        return f"{base} (STALE)"
    return base


def _status_color(status: CalculationStatus, is_stale: bool = False) -> Any:
    if is_stale and status not in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT):
        return colors.HexColor("#b45309")
    if status == CalculationStatus.PASS:
        return colors.HexColor("#198754")
    if status == CalculationStatus.FAIL:
        return colors.HexColor("#dc3545")
    if status == CalculationStatus.REQUIRES_REVIEW:
        return colors.HexColor("#b45309")
    return colors.HexColor("#6c757d")


def _format_acceptance(acc: Any) -> str:
    if acc is None:
        return ""
    if isinstance(acc, AcceptanceCriterion):
        parts = [acc.comparison]
        if acc.limit_value is not None:
            parts.append(f"{acc.limit_value} {acc.limit_unit}".strip())
        if acc.description:
            parts.append(acc.description)
        return " ".join(p for p in parts if p)
    if isinstance(acc, dict):
        return str(acc.get("description") or acc.get("comparison") or "")
    return str(acc)


def _format_scalar(val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.4g}"
    return str(val)


def _build_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PdfTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14.5,
            leading=18.5,
            textColor=colors.HexColor("#1b365d"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "PdfSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.8,
            textColor=colors.HexColor("#495057"),
            spaceAfter=7,
        ),
        "sec_head": ParagraphStyle(
            "PdfSectionHead",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=13.5,
            textColor=colors.HexColor("#1b365d"),
            spaceBefore=7,
            spaceAfter=3.5,
        ),
        "stage_head": ParagraphStyle(
            "PdfStageHead",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.0,
            leading=12.0,
            textColor=colors.HexColor("#0f4c81"),
            spaceBefore=5,
            spaceAfter=2.5,
        ),
        "normal": ParagraphStyle(
            "PdfNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.4,
            leading=11.2,
            textColor=colors.HexColor("#212529"),
        ),
        "bold": ParagraphStyle(
            "PdfBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=11.2,
            textColor=colors.HexColor("#212529"),
        ),
        "small": ParagraphStyle(
            "PdfSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=9.8,
            textColor=colors.HexColor("#495057"),
        ),
        "ref_right": ParagraphStyle(
            "PdfRefRight",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.6,
            alignment=2,  # TA_RIGHT
            textColor=colors.HexColor("#495057"),
        ),
        "banner_warn": ParagraphStyle(
            "PdfBannerWarn",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=11.6,
            textColor=colors.HexColor("#7c2d12"),
        ),
    }


def _build_diagram_drawing(
    diagram_spec: Optional[DiagramSpec],
    width: float = 490.0,
    height: float = 155.0,
) -> Optional[Drawing]:
    """Render Qt-independent DiagramSpec primitives as a ReportLab Drawing."""
    if diagram_spec is None:
        return None

    drawing = Drawing(width, height)
    drawing.add(
        Rect(
            0,
            0,
            width,
            height,
            fillColor=colors.HexColor("#fcfdff"),
            strokeColor=colors.HexColor("#ced4da"),
            strokeWidth=0.8,
        )
    )
    drawing.add(
        String(
            10,
            height - 14,
            diagram_spec.title[:80],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            fillColor=colors.HexColor("#1b365d"),
        )
    )

    if diagram_spec.is_empty_state:
        msg = diagram_spec.empty_message or "Enter required inputs to preview structural schematic."
        drawing.add(
            String(
                width / 2.0,
                height / 2.0,
                msg[:95],
                fontName="Helvetica-Oblique",
                fontSize=8.4,
                textAnchor="middle",
                fillColor=colors.HexColor("#6c757d"),
            )
        )
        return drawing

    xs: List[float] = []
    ys: List[float] = []
    for shp in diagram_spec.shapes:
        if shp.kind == "rect" and len(shp.coords) >= 4:
            x, y, w, h = shp.coords[:4]
            xs.extend([x, x + w])
            ys.extend([y, y + h])
        elif shp.kind == "line" and len(shp.coords) >= 4:
            xs.extend([shp.coords[0], shp.coords[2]])
            ys.extend([shp.coords[1], shp.coords[3]])
        elif shp.kind == "circle" and len(shp.coords) >= 3:
            cx, cy, r = shp.coords[:3]
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])
        elif shp.kind == "polygon" and len(shp.coords) >= 6:
            xs.extend(shp.coords[0::2])
            ys.extend(shp.coords[1::2])

    for dim in diagram_spec.dimensions:
        xs.extend([dim.p1[0], dim.p2[0]])
        ys.extend([dim.p1[1], dim.p2[1]])
    for frc in diagram_spec.forces:
        ox, oy = frc.origin
        dx, dy = frc.direction
        xs.extend([ox, ox + dx * 45.0])
        ys.extend([oy, oy + dy * 45.0])

    min_x = min(xs) if xs else 0.0
    max_x = max(xs) if xs else 380.0
    min_y = min(ys) if ys else 0.0
    max_y = max(ys) if ys else 200.0
    span_x = max(max_x - min_x, 40.0)
    span_y = max(max_y - min_y, 30.0)

    pad_x = 32.0
    pad_top = 24.0
    pad_bottom = 22.0
    avail_w = max(width - 2 * pad_x, 80.0)
    avail_h = max(height - pad_top - pad_bottom, 55.0)
    scale = min(avail_w / span_x, avail_h / span_y)

    offset_x = (width - span_x * scale) / 2.0 - min_x * scale
    offset_top_y = pad_top + (avail_h - span_y * scale) / 2.0 - min_y * scale

    def _tx(x: float) -> float:
        return x * scale + offset_x

    def _ty(y: float) -> float:
        return height - (y * scale + offset_top_y)

    for shp in diagram_spec.shapes:
        fill_c = _hex_to_rl(shp.fill_color, colors.HexColor("#fde6cf"))
        stroke_c = _hex_to_rl(shp.stroke_color, colors.HexColor("#343a40"))
        sw = max(0.5, float(shp.stroke_width or 1.2) * 0.7)
        if shp.kind == "rect" and len(shp.coords) >= 4:
            x, y, w, h = shp.coords[:4]
            rx = _tx(x)
            ry = _ty(y + h)
            rw = max(w * scale, 1.0)
            rh = max(h * scale, 1.0)
            drawing.add(Rect(rx, ry, rw, rh, fillColor=fill_c, strokeColor=stroke_c, strokeWidth=sw))
            if shp.label:
                drawing.add(
                    String(
                        rx + rw / 2.0,
                        ry + rh / 2.0 - 2.5,
                        shp.label[:28],
                        fontName="Helvetica",
                        fontSize=6.8,
                        textAnchor="middle",
                        fillColor=colors.HexColor("#212529"),
                    )
                )
        elif shp.kind == "line" and len(shp.coords) >= 4:
            x1, y1, x2, y2 = shp.coords[:4]
            drawing.add(Line(_tx(x1), _ty(y1), _tx(x2), _ty(y2), strokeColor=stroke_c, strokeWidth=sw))
        elif shp.kind == "circle" and len(shp.coords) >= 3:
            cx, cy, r = shp.coords[:3]
            drawing.add(
                Circle(
                    _tx(cx),
                    _ty(cy),
                    max(r * scale, 1.5),
                    fillColor=fill_c,
                    strokeColor=stroke_c,
                    strokeWidth=sw,
                )
            )
        elif shp.kind == "polygon" and len(shp.coords) >= 6:
            pts: List[float] = []
            for idx in range(0, len(shp.coords) - 1, 2):
                pts.extend([_tx(shp.coords[idx]), _ty(shp.coords[idx + 1])])
            drawing.add(Polygon(pts, fillColor=fill_c, strokeColor=stroke_c, strokeWidth=sw))

    for dim in diagram_spec.dimensions:
        c = _hex_to_rl(dim.color, colors.HexColor("#007bff"))
        x1, y1 = _tx(dim.p1[0]), _ty(dim.p1[1])
        x2, y2 = _tx(dim.p2[0]), _ty(dim.p2[1])
        drawing.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=0.8, strokeDashArray=[2, 2]))
        drawing.add(
            String(
                (x1 + x2) / 2.0,
                (y1 + y2) / 2.0 + 3.0,
                dim.label[:34],
                fontName="Helvetica",
                fontSize=6.8,
                textAnchor="middle",
                fillColor=c,
            )
        )

    for frc in diagram_spec.forces:
        c = colors.HexColor("#b45309") if frc.is_stale else _hex_to_rl(frc.color, colors.HexColor("#d96818"))
        ox, oy = _tx(frc.origin[0]), _ty(frc.origin[1])
        dx, dy = frc.direction
        ex = ox + dx * 36.0 * scale
        ey = oy - dy * 36.0 * scale
        drawing.add(Line(ox, oy, ex, ey, strokeColor=c, strokeWidth=1.4))
        drawing.add(Circle(ex, ey, 2.2, fillColor=c, strokeColor=c))
        lbl = frc.label
        if frc.is_stale and "STALE" not in lbl.upper():
            lbl = f"{lbl} [STALE]"
        drawing.add(
            String(
                ex + 3.0,
                ey + 2.0,
                lbl[:36],
                fontName="Helvetica-Bold",
                fontSize=6.8,
                fillColor=c,
            )
        )

    footer_parts: List[str] = []
    if diagram_spec.summary_badge:
        footer_parts.append(diagram_spec.summary_badge)
    for pill in diagram_spec.callouts[:2]:
        footer_parts.append(pill.text)
    if footer_parts:
        footer_text = "  |  ".join(footer_parts)[:105]
        badge_color = colors.HexColor("#b45309") if diagram_spec.is_stale else colors.HexColor("#1b365d")
        drawing.add(
            String(
                10,
                6,
                footer_text,
                fontName="Helvetica-Bold",
                fontSize=7.2,
                fillColor=badge_color,
            )
        )

    return drawing


def _build_calc_item_story(
    calc_result: CalculationResult,
    project_info: Dict[str, Any],
    kb: KnowledgeBaseService,
    styles: Dict[str, ParagraphStyle],
    diagram_spec: Optional[DiagramSpec] = None,
    item_label: Optional[str] = None,
    item_title: Optional[str] = None,
    group_name: Optional[str] = None,
    revision_number: Optional[int] = None,
) -> List[Any]:
    """Build 12-section ReportLab flowables aligned to the 7-section Plan Check layout."""
    story: List[Any] = []
    is_stale = bool(getattr(calc_result, "is_stale", False))
    status_text = _status_display(calc_result)
    status_hex = _status_color(calc_result.status, is_stale=is_stale)
    heading_title = item_title or calc_result.module_id

    # Section 1: Header & Code Basis Block
    title_prefix = f"{item_label} — " if item_label else ""
    story.append(
        Paragraph(
            _xml_text(f"{title_prefix}STRUCTURAL CALCULATION: {heading_title}"),
            styles["title"],
        )
    )
    meta_bits = [
        f"Module: {calc_result.module_id}",
        f"Project: {project_info.get('project_name', 'N/A')} ({project_info.get('project_code', 'N/A')})",
        f"Engineer: {project_info.get('engineer', 'N/A')}",
        f"Date: {project_info.get('date', 'N/A')}",
    ]
    if group_name:
        meta_bits.append(f"Group: {group_name}")
    if revision_number is not None:
        meta_bits.append(f"Rev: {revision_number}")
    story.append(Paragraph(_xml_text("  |  ".join(meta_bits)), styles["subtitle"]))

    dcr_display = (
        "—"
        if calc_result.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT)
        else f"{calc_result.dcr:.3f}"
    )
    hdr_table = Table(
        [
            [
                Paragraph(f"<b>Code Basis:</b> {_xml_text(calc_result.code_edition)}", styles["normal"]),
                Paragraph(f"<b>Method:</b> {_xml_text(calc_result.design_method.value)}", styles["normal"]),
                Paragraph(f"<b>Governing DCR:</b> {dcr_display}", styles["normal"]),
                Paragraph(f"<b>Status:</b> {_xml_text(status_text)}", styles["bold"]),
            ]
        ],
        colWidths=[2.2 * inch, 1.15 * inch, 1.45 * inch, 2.0 * inch],
    )
    hdr_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4fb")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#b8c9dc")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d3e0ee")),
                ("TEXTCOLOR", (3, 0), (3, 0), status_hex),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(hdr_table)
    story.append(Spacer(1, 5))

    # Explicit non-passing / stale disclosure banner
    if calc_result.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT) or is_stale:
        banner_msgs: List[str] = []
        if calc_result.status == CalculationStatus.INCOMPLETE:
            reasons = "; ".join(calc_result.incomplete_reasons)
            msg = "INCOMPLETE CALCULATION: Required inputs are missing; no verified check was completed."
            if reasons:
                msg += f" ({reasons})"
            banner_msgs.append(msg)
        elif calc_result.status == CalculationStatus.INVALID_INPUT:
            reasons = "; ".join(calc_result.incomplete_reasons or calc_result.warnings)
            msg = "INVALID INPUT: Input parameters violate domain or applicability limits."
            if reasons:
                msg += f" ({reasons})"
            banner_msgs.append(msg)
        if is_stale:
            banner_msgs.append(
                "STALE RESULT: Draft inputs were edited after the last run — re-run required."
            )
        banner_tbl = Table(
            [[Paragraph(_xml_text(" ".join(banner_msgs)), styles["banner_warn"])]],
            colWidths=[6.8 * inch],
        )
        banner_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#f59e0b")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(banner_tbl)
        story.append(Spacer(1, 5))

    # Section 2: Design Inputs
    story.append(Paragraph("2. Design Inputs & Boundary Conditions", styles["sec_head"]))
    input_rows: List[List[Any]] = [
        [
            Paragraph("<b>Parameter</b>", styles["normal"]),
            Paragraph("<b>Value</b>", styles["normal"]),
            Paragraph("<b>Parameter</b>", styles["normal"]),
            Paragraph("<b>Value</b>", styles["normal"]),
        ]
    ]
    input_items = list((calc_result.input_parameters or {}).items())
    if not input_items:
        input_items = [("inputs", "(none entered)")]
    for idx in range(0, len(input_items), 2):
        k1, v1 = input_items[idx]
        if idx + 1 < len(input_items):
            k2, v2 = input_items[idx + 1]
        else:
            k2, v2 = "", ""
        input_rows.append(
            [
                Paragraph(_xml_text(k1), styles["normal"]),
                Paragraph(_xml_text("—" if v1 is None else v1), styles["normal"]),
                Paragraph(_xml_text(k2), styles["normal"]),
                Paragraph(_xml_text(("—" if v2 is None else v2) if k2 else ""), styles["normal"]),
            ]
        )
    inp_tbl = Table(input_rows, colWidths=[1.8 * inch, 1.6 * inch, 1.8 * inch, 1.6 * inch])
    inp_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(inp_tbl)
    story.append(Spacer(1, 4))

    # Section 3: Applicable Code References & Referenced KB Files
    story.append(Paragraph("3. Applicable Code Provisions & Verified Knowledge Base Sources", styles["sec_head"]))
    ls_clauses = [ls.code_clause for ls in calc_result.limit_states if ls.code_clause]
    trace_refs: List[str] = []
    for st in getattr(calc_result, "trace", ()) or ():
        for r in st.refs:
            lbl = r.display_label
            if lbl not in trace_refs:
                trace_refs.append(lbl)
    all_clauses = list(dict.fromkeys([*ls_clauses, *trace_refs]))
    ref_list = ", ".join(all_clauses) if all_clauses else calc_result.code_edition
    tbl_list = ", ".join(calc_result.reference_files) if calc_result.reference_files else "None"
    story.append(Paragraph(f"<b>Code Provisions:</b> {_xml_text(ref_list)}", styles["normal"]))
    story.append(Paragraph(f"<b>Referenced KB Tables:</b> {_xml_text(tbl_list)}", styles["normal"]))
    story.append(Spacer(1, 4))

    # Section 4: Structural Schematic Diagram (DiagramSpec)
    story.append(Paragraph("4. Structural Schematic & Geometry / Force Diagram", styles["sec_head"]))
    resolved_diagram = diagram_spec
    if resolved_diagram is None:
        resolved_diagram = build_diagram_spec(
            calc_result.module_id,
            calc_result.input_parameters or {},
            result=(
                calc_result
                if calc_result.status not in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT)
                else None
            ),
            is_stale=is_stale,
        )
    drawing = _build_diagram_drawing(resolved_diagram, width=490.0, height=150.0)
    if drawing is not None:
        story.append(drawing)
    story.append(Spacer(1, 4))

    # Sections 5-7: 4-Stage Calculation Sheet & Trace
    story.append(Paragraph("5. Step-by-Step Calculation Trace (Equation → Substitution → Result)", styles["sec_head"]))
    trace_steps: Sequence[CalcStep] = getattr(calc_result, "trace", ()) or ()
    if trace_steps:
        by_stage: Dict[int, List[CalcStep]] = {}
        for step in trace_steps:
            by_stage.setdefault(int(step.stage or 1), []).append(step)

        for stage_num in sorted(by_stage.keys()):
            stage_title = STAGE_TITLES.get(stage_num, f"Stage {stage_num}")
            story.append(Paragraph(_xml_text(stage_title), styles["stage_head"]))
            step_rows: List[List[Any]] = [
                [
                    Paragraph("<b>Step</b>", styles["small"]),
                    Paragraph("<b>Equation &amp; Substitution → Result</b>", styles["small"]),
                    Paragraph("<b>Code Reference</b>", styles["small"]),
                ]
            ]
            for step in by_stage[stage_num]:
                lines: List[str] = [f"<b>{_xml_text(step.title)}</b>"]
                if step.symbolic:
                    lines.append(f"Eq: {_format_math_for_pdf(step.symbolic)}")
                if step.substituted:
                    lines.append(f"Sub: {_format_math_for_pdf(step.substituted)}")
                if step.result_value is not None:
                    unit_suffix = f" {step.result_unit}" if step.result_unit else ""
                    res_line = f"<b>Result = {_xml_text(_format_scalar(step.result_value))}{_xml_text(unit_suffix)}</b>"
                    acc_str = _format_acceptance(step.acceptance)
                    if acc_str:
                        res_line += f"  [{_xml_text(acc_str)}]"
                    if step.dcr is not None:
                        res_line += f"  (DCR = {step.dcr:.3f})"
                    lines.append(res_line)
                elif step.acceptance is not None:
                    lines.append(f"<b>{_xml_text(_format_acceptance(step.acceptance))}</b>")
                if step.note:
                    lines.append(f"<i>{_xml_text(step.note)}</i>")

                ref_parts = []
                for ref in step.refs:
                    part = ref.display_label
                    if ref.kb_reference_id:
                        part += f" [{ref.kb_reference_id}]"
                    ref_parts.append(_xml_text(part))
                ref_html = "<br/>".join(ref_parts) if ref_parts else "—"
                step_rows.append(
                    [
                        Paragraph(_xml_text(step.step_id or str(step.stage)), styles["small"]),
                        Paragraph("<br/>".join(lines), styles["normal"]),
                        Paragraph(ref_html, styles["ref_right"]),
                    ]
                )
            st_tbl = Table(step_rows, colWidths=[0.65 * inch, 4.45 * inch, 1.7 * inch])
            st_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(st_tbl)
            story.append(Spacer(1, 3))
    else:
        if calc_result.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT):
            story.append(
                Paragraph(
                    "<i>No calculation steps executed because required inputs are incomplete or invalid.</i>",
                    styles["normal"],
                )
            )
        else:
            for ls in calc_result.limit_states:
                story.append(
                    Paragraph(
                        f"• <b>{_xml_text(ls.name)}:</b> {_format_math_for_pdf(ls.equation_latex)} → "
                        f"{_format_math_for_pdf(ls.substitution_str)} ({_xml_text(ls.code_clause)})",
                        styles["normal"],
                    )
                )
            for key, val in (calc_result.intermediate_results or {}).items():
                story.append(Paragraph(f"• {_xml_text(key)} = {_xml_text(_format_scalar(val))}", styles["normal"]))

    story.append(Spacer(1, 4))

    # Section 8: Limit State Verification Summary Table
    story.append(Paragraph("6. Limit State Verification Summary", styles["sec_head"]))
    ls_rows: List[List[Any]] = [
        [
            Paragraph("<b>Limit State</b>", styles["small"]),
            Paragraph("<b>Demand</b>", styles["small"]),
            Paragraph("<b>Capacity</b>", styles["small"]),
            Paragraph("<b>DCR</b>", styles["small"]),
            Paragraph("<b>Status</b>", styles["small"]),
            Paragraph("<b>Code Clause</b>", styles["small"]),
        ]
    ]
    if calc_result.limit_states:
        for ls in calc_result.limit_states:
            ls_rows.append(
                [
                    Paragraph(_xml_text(ls.name), styles["normal"]),
                    Paragraph(_xml_text(f"{ls.demand:.2f} {ls.units}".strip()), styles["normal"]),
                    Paragraph(_xml_text(f"{ls.capacity:.2f} {ls.units}".strip()), styles["normal"]),
                    Paragraph(f"{ls.dcr:.3f}", styles["normal"]),
                    Paragraph(_xml_text("STALE" if is_stale else ls.status.value), styles["bold"]),
                    Paragraph(_xml_text(ls.code_clause), styles["small"]),
                ]
            )
    else:
        ls_rows.append(
            [
                Paragraph("No evaluated limit states", styles["normal"]),
                Paragraph("—", styles["normal"]),
                Paragraph("—", styles["normal"]),
                Paragraph("—", styles["normal"]),
                Paragraph(_xml_text(status_text), styles["bold"]),
                Paragraph(_xml_text(calc_result.code_edition), styles["small"]),
            ]
        )
    ls_tbl = Table(ls_rows, colWidths=[2.05 * inch, 1.0 * inch, 1.0 * inch, 0.65 * inch, 0.9 * inch, 1.2 * inch])
    ls_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b365d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    story.append(ls_tbl)
    story.append(Spacer(1, 5))

    # Sections 9-10: Engineering Conclusion, Warnings & Assumptions
    story.append(Paragraph("7. Acceptance Criteria, Warnings & Engineering Conclusion", styles["sec_head"]))
    gov_name = (
        calc_result.governing_limit_state.name
        if calc_result.governing_limit_state is not None
        else "None"
    )
    story.append(
        Paragraph(
            f"<b>Governing Limit State:</b> {_xml_text(gov_name)}  |  "
            f"<b>Governing DCR:</b> {dcr_display}  |  "
            f"<b>Final Status:</b> {_xml_text(status_text)}",
            styles["normal"],
        )
    )
    for w in calc_result.warnings:
        story.append(Paragraph(f"• <b>Warning:</b> {_xml_text(w)}", styles["normal"]))
    for a in calc_result.assumptions:
        story.append(Paragraph(f"• <b>Assumption:</b> {_xml_text(a)}", styles["small"]))

    # Sections 11-12: Verification & Source Audit Metadata
    story.append(Spacer(1, 3))
    story.append(Paragraph("8. Source Verification & Audit Fingerprint", styles["sec_head"]))
    audit_rows = build_source_audit_records(calc_result, kb=kb)
    verified_count = sum(1 for r in audit_rows if r.get("verified"))
    manifest_sha = str(
        kb.manifest_data.get("manifest_sha256")
        or kb.manifest_data.get("generated_utc")
        or "N/A"
    )[:24]
    story.append(
        Paragraph(
            f"<b>Software Version:</b> {_xml_text(calc_result.software_version)}  |  "
            f"<b>KB Manifest SHA-256:</b> {_xml_text(manifest_sha)}  |  "
            f"<b>Verified Sources:</b> {verified_count}/{len(audit_rows)}",
            styles["small"],
        )
    )
    return story


def export_calculation_to_pdf(
    calc_result: CalculationResult,
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
    diagram_spec: Optional[DiagramSpec] = None,
) -> Path:
    """Export a single CalculationResult to a structured Plan-Check PDF file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    kb_svc = kb or KnowledgeBaseService()
    info = project_info or {}
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{calc_result.module_id} Calculation",
    )
    story = _build_calc_item_story(
        calc_result=calc_result,
        project_info=info,
        kb=kb_svc,
        styles=styles,
        diagram_spec=diagram_spec,
    )
    doc.build(story)
    return out


def export_project_to_pdf(
    items: Sequence[Dict[str, Any]],
    output_path: Union[str, Path],
    project_info: Optional[Dict[str, Any]] = None,
    kb: Optional[KnowledgeBaseService] = None,
) -> Path:
    """Export an ordered sequence of project calculation items into one multi-item PDF package.

    Each item dict accepts:
      - display_code: str (e.g. 'C-01')
      - title: str
      - group_name: str
      - revision_number: int
      - calc_result: CalculationResult
      - diagram_spec: Optional[DiagramSpec]
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    kb_svc = kb or KnowledgeBaseService()
    info = project_info or {}
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{info.get('project_name', 'Project')} Calculation Package",
    )

    story: List[Any] = []
    story.append(
        Paragraph(
            _xml_text(f"STRUCTURAL CALCULATION PACKAGE — {info.get('project_name', 'Untitled Project')}"),
            styles["title"],
        )
    )
    story.append(
        Paragraph(
            _xml_text(
                f"Project Code: {info.get('project_code', 'N/A')}  |  "
                f"Engineer: {info.get('engineer', 'N/A')}  |  "
                f"Date: {info.get('date', 'N/A')}  |  "
                f"Items: {len(items)}"
            ),
            styles["subtitle"],
        )
    )
    story.append(Paragraph("Ordered Calculation Index (Sidebar Sequence)", styles["sec_head"]))

    idx_rows: List[List[Any]] = [
        [
            Paragraph("<b>#</b>", styles["small"]),
            Paragraph("<b>ID</b>", styles["small"]),
            Paragraph("<b>Group</b>", styles["small"]),
            Paragraph("<b>Title</b>", styles["small"]),
            Paragraph("<b>Code / Method</b>", styles["small"]),
            Paragraph("<b>Rev</b>", styles["small"]),
            Paragraph("<b>DCR</b>", styles["small"]),
            Paragraph("<b>Status</b>", styles["small"]),
        ]
    ]
    calc_results: List[CalculationResult] = []
    for pos, entry in enumerate(items, start=1):
        res: CalculationResult = entry["calc_result"]
        calc_results.append(res)
        dcr_str = (
            "—"
            if res.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT)
            else f"{res.dcr:.3f}"
        )
        idx_rows.append(
            [
                Paragraph(str(pos), styles["small"]),
                Paragraph(_xml_text(entry.get("display_code", f"C-{pos:02d}")), styles["small"]),
                Paragraph(_xml_text(entry.get("group_name", "Ungrouped")), styles["small"]),
                Paragraph(_xml_text(entry.get("title", res.module_id)), styles["small"]),
                Paragraph(_xml_text(f"{res.code_edition} ({res.design_method.value})"), styles["small"]),
                Paragraph(str(entry.get("revision_number", 0)), styles["small"]),
                Paragraph(dcr_str, styles["small"]),
                Paragraph(_xml_text(_status_display(res)), styles["bold"]),
            ]
        )

    idx_tbl = Table(
        idx_rows,
        colWidths=[0.3 * inch, 0.55 * inch, 0.95 * inch, 1.85 * inch, 1.25 * inch, 0.35 * inch, 0.55 * inch, 1.0 * inch],
    )
    idx_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b365d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    story.append(idx_tbl)
    story.append(Spacer(1, 8))

    audit_records = build_project_source_audit_records(calc_results, kb=kb_svc)
    if audit_records:
        story.append(Paragraph("Project Reference Source Audit", styles["sec_head"]))
        aud_rows: List[List[Any]] = [
            [
                Paragraph("<b>Table / Code Reference</b>", styles["small"]),
                Paragraph("<b>Edition</b>", styles["small"]),
                Paragraph("<b>SHA-256</b>", styles["small"]),
                Paragraph("<b>Verified</b>", styles["small"]),
            ]
        ]
        for rec in audit_records:
            aud_rows.append(
                [
                    Paragraph(_xml_text(rec.get("source_table", "")), styles["small"]),
                    Paragraph(_xml_text(rec.get("code_edition", "")), styles["small"]),
                    Paragraph(_xml_text(str(rec.get("sha256", ""))[:20]), styles["small"]),
                    Paragraph(_xml_text("YES" if rec.get("verified") else "NO"), styles["small"]),
                ]
            )
        aud_tbl = Table(aud_rows, colWidths=[2.7 * inch, 1.5 * inch, 1.8 * inch, 0.8 * inch])
        aud_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(aud_tbl)

    for pos, entry in enumerate(items, start=1):
        story.append(PageBreak())
        story.extend(
            _build_calc_item_story(
                calc_result=entry["calc_result"],
                project_info=info,
                kb=kb_svc,
                styles=styles,
                diagram_spec=entry.get("diagram_spec"),
                item_label=entry.get("display_code", f"C-{pos:02d}"),
                item_title=entry.get("title"),
                group_name=entry.get("group_name"),
                revision_number=entry.get("revision_number"),
            )
        )

    doc.build(story)
    return out
