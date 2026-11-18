"""Offline Panel 3 Calculation Sheet Math Renderer (WP-7).

Provides deterministic HTML rendering for Panel 3 using:
1. Local vendored KaTeX + QWebEngineView when BOTH `PySide6.QtWebEngineWidgets`
   and local `gui/assets/katex/katex.min.js` are present (zero CDN calls).
2. Deterministic `QTextEdit` rich-text HTML fallback powered by
   `core.common.math_markup.math_markup_to_rich_html` (zero external network calls).
"""

import html
from pathlib import Path
import re
from typing import Dict, List, Optional, Sequence

from app.models import CalcStep, CalculationResult, CalculationStatus
from core.common.math_markup import math_markup_to_rich_html


STAGE_TITLES: Dict[int, str] = {
    1: "Stage 1 — Geometry, Detailing & Applicability Limits",
    2: "Stage 2 — Primary Force-Transfer Mechanism",
    3: "Stage 3 — Connecting Element & Base Metal Limit States",
    4: "Stage 4 — Supporting Member / Global Substrate & Combined Interaction",
}

KATEX_SPIKE_REPORT = {
    "katex_relative_dir": "gui/assets/katex",
    "cdn_allowed": False,
    "fallback_mode": "QTextEdit + math_markup_to_rich_html",
    "notes": (
        "Locally vendored offline KaTeX CSS/JS (gui/assets/katex/katex.min.css and "
        "katex.min.js) and QtWebEngineWidgets are checked locally at runtime with zero "
        "CDN/network calls; QTextEdit rich-text fallback remains available."
    ),
}


def get_katex_assets_dir(assets_root: Optional[Path] = None) -> Path:
    """Return filesystem directory containing locally vendored offline KaTeX assets."""
    return assets_root or (Path(__file__).resolve().parent.parent.parent / "gui" / "assets" / "katex")


def has_webengine_support(assets_root: Optional[Path] = None) -> bool:
    """Return True only if QtWebEngineWidgets AND local vendored KaTeX JS/CSS are available offline."""
    root = get_katex_assets_dir(assets_root)
    if not (root / "katex.min.js").is_file() or not (root / "katex.min.css").is_file():
        return False
    try:
        import PySide6.QtWebEngineWidgets  # noqa: F401
        return True
    except Exception:
        return False


_LEGACY_REPLACEMENTS = (
    (r"\cdot", "·"),
    (r"\times", "×"),
    (r"\leq", "≤"),
    (r"\le", "≤"),
    (r"\geq", "≥"),
    (r"\ge", "≥"),
    (r"\neq", "≠"),
    (r"\pm", "±"),
    (r"\phi", "φ"),
    (r"\Phi", "Φ"),
    (r"\Omega", "Ω"),
    (r"\Delta", "Δ"),
    (r"\delta", "δ"),
    (r"\theta", "θ"),
    (r"\lambda", "λ"),
    (r"\alpha", "α"),
    (r"\beta", "β"),
    (r"\gamma", "γ"),
    (r"\psi", "ψ"),
    (r"\epsilon", "ε"),
    (r"\parallel", "∥"),
    (r"\perp", "⊥"),
    (r"\circ", "°"),
    (r"\ell", "ℓ"),
    ("&ell;", "ℓ"),
)


def safe_markup_to_html(expr: str) -> str:
    """Convert restricted LaTeX (or legacy equation string) into safe UTF-8 rich HTML."""
    if not expr or not expr.strip():
        return ""
    try:
        return math_markup_to_rich_html(expr)
    except ValueError:
        # Graceful deterministic normalization for legacy pre-WP-2 equation_latex strings
        cleaned = expr.strip()
        for src, dst in _LEGACY_REPLACEMENTS:
            cleaned = cleaned.replace(src, dst)
        cleaned = re.sub(r"\\text\{([^}]*)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1) / (\2)", cleaned)
        cleaned = re.sub(r"\\sqrt\{([^}]*)\}", r"√(\1)", cleaned)
        cleaned = cleaned.replace("\\left", "").replace("\\right", "")
        cleaned = cleaned.replace("{", "").replace("}", "")
        return html.escape(cleaned, quote=False)


def _format_step_result_cell(step: CalcStep) -> str:
    parts: List[str] = []
    if step.result_value is not None:
        if isinstance(step.result_value, float):
            val_str = f"{step.result_value:,.3f}".rstrip("0").rstrip(".") if abs(step.result_value) < 10 else f"{step.result_value:,.2f}"
        else:
            val_str = html.escape(str(step.result_value))
        unit_str = f" {html.escape(step.result_unit)}" if step.result_unit else ""
        parts.append(f"<b>{val_str}{unit_str}</b>")

    if step.dcr is not None:
        status_val = step.status.value if isinstance(step.status, CalculationStatus) else str(step.status)
        color = "#28a745" if status_val == "PASS" else ("#dc3545" if status_val == "FAIL" else "#6c757d")
        parts.append(
            f"<span style='color:{color}; font-weight:bold;'>DCR = {step.dcr:.2f} ({html.escape(status_val)})</span>"
        )
    elif step.acceptance is not None:
        acc_desc = getattr(step.acceptance, "description", None) or str(step.acceptance)
        if acc_desc:
            parts.append(f"<span style='color:#495057;'>{html.escape(str(acc_desc))}</span>")

    return " &nbsp; ".join(parts)


def render_calculation_sheet_html(
    result: Optional[CalculationResult],
    code_edition: str,
    design_method: str,
    is_stale: bool = False,
    incomplete_reasons: Sequence[str] = (),
) -> str:
    """
    Render Panel 3 Calculation Sheet HTML from CalculationResult.trace (or legacy fallback).
    Zero network/CDN dependencies; safe for QTextEdit and offline print/display.
    """
    if result is None:
        if incomplete_reasons:
            items_html = "".join(f"<li>{html.escape(str(r))}</li>" for r in incomplete_reasons)
            return (
                "<div style='font-family:\"Segoe UI\", Arial, sans-serif; font-size:12px; color:#6c757d;'>"
                "<p><b>No calculation results yet.</b> Complete the required inputs below:</p>"
                f"<ul style='margin-top:4px; margin-bottom:0;'>{items_html}</ul>"
                "</div>"
            )
        return (
            "<p style='font-family:\"Segoe UI\", Arial, sans-serif; font-size:12px; color:#6c757d;'>"
            "No calculation results yet. Enter required inputs and click Run Calculation."
            "</p>"
        )

    blocks: List[str] = []

    if is_stale:
        blocks.append(
            "<div style='background-color:#fff3cd; border:1px solid #ffeeba; color:#856404; "
            "padding:6px 10px; border-radius:4px; margin-bottom:8px; font-size:11px; font-weight:bold;'>"
            "Inputs modified since last run — results below are STALE. Click Run Calculation to update."
            "</div>"
        )

    trace = getattr(result, "trace", ()) or ()
    rows_html: List[str] = []

    if trace:
        by_stage: Dict[int, List[CalcStep]] = {1: [], 2: [], 3: [], 4: []}
        for step in trace:
            by_stage.setdefault(int(step.stage), []).append(step)

        for stage_num in sorted(by_stage.keys()):
            stage_steps = by_stage[stage_num]
            if not stage_steps:
                continue
            stage_title = STAGE_TITLES.get(stage_num, f"Stage {stage_num}")
            rows_html.append(
                "<tr>"
                f"<td colspan='2' style='background-color:#f8f9fa; color:#343a40; font-weight:bold; "
                f"font-size:11px; padding:5px 6px; border-bottom:1px solid #dee2e6;'>"
                f"{html.escape(stage_title)}</td>"
                "</tr>"
            )
            for step in stage_steps:
                eq_html = safe_markup_to_html(step.symbolic)
                sub_html = safe_markup_to_html(step.substituted)
                res_html = _format_step_result_cell(step)
                refs_html = "<br>".join(html.escape(r.display_label) for r in step.refs) if step.refs else ""

                line_parts = [f"<b>{html.escape(step.step_id)} · {html.escape(step.title)}</b>"]
                if eq_html:
                    line_parts.append(f"<span style='color:#212529;'>{eq_html}</span>")
                if sub_html:
                    line_parts.append(f"<span style='color:#495057;'>&rarr; {sub_html}</span>")
                if res_html:
                    line_parts.append(f"<span>= {res_html}</span>")
                if step.note:
                    line_parts.append(f"<br><small style='color:#6c757d;'>{html.escape(step.note)}</small>")

                rows_html.append(
                    "<tr>"
                    f"<td width='70%' style='padding:4px 6px; border-bottom:1px solid #f1f3f5;'>"
                    f"{line_parts[0]}"
                    + (f"<br>{' '.join(line_parts[1:])}" if len(line_parts) > 1 else "")
                    + "</td>"
                    f"<td width='30%' align='right' valign='top' style='color:#007bff; font-weight:500; font-size:11px; "
                    f"padding:4px 6px; border-bottom:1px solid #f1f3f5;'>"
                    f"{refs_html}</td>"
                    "</tr>"
                )
    else:
        for k, v in result.intermediate_results.items():
            rows_html.append(
                "<tr>"
                f"<td style='padding:3px 6px;'><b>{html.escape(str(k))}</b> = {html.escape(str(v))}</td>"
                "<td></td>"
                "</tr>"
            )
        for ls in result.limit_states:
            eq = safe_markup_to_html(ls.equation_latex) if ls.equation_latex else ""
            sub = safe_markup_to_html(ls.substitution_str) if ls.substitution_str else ""
            dcr_color = "#28a745" if ls.status == CalculationStatus.PASS else "#dc3545"
            rows_html.append(
                "<tr>"
                f"<td style='padding:4px 6px; border-bottom:1px solid #f1f3f5;'>"
                f"<b>{html.escape(ls.step_id)} · {html.escape(ls.name)}</b>"
                + (f": <span>{eq}</span>" if eq else "")
                + (f"<br><small style='color:#495057;'>{sub}</small>" if sub else "")
                + f" <small style='color:{dcr_color}; font-weight:bold;'>[DCR = {ls.dcr:.2f} {ls.status.value}]</small>"
                "</td>"
                f"<td align='right' valign='top' style='color:#007bff; font-weight:500; font-size:11px; "
                f"padding:4px 6px; border-bottom:1px solid #f1f3f5;'>{html.escape(ls.code_clause)}</td>"
                "</tr>"
            )

    table_html = (
        "<table width='100%' cellpadding='2' cellspacing='0' "
        "style='font-family:\"Segoe UI\", Arial, sans-serif; font-size:12px; border-collapse:collapse;'>"
        f"{''.join(rows_html)}"
        "</table>"
    )
    blocks.append(table_html)
    return "".join(blocks)


def build_offline_katex_document(
    result: Optional[CalculationResult],
    code_edition: str,
    design_method: str,
    is_stale: bool = False,
    incomplete_reasons: Sequence[str] = (),
    assets_root: Optional[Path] = None,
) -> str:
    """Wrap Panel 3 HTML in a self-contained offline document referencing local vendored KaTeX assets."""
    root = get_katex_assets_dir(assets_root)
    css_uri = (root / "katex.min.css").resolve().as_uri()
    js_uri = (root / "katex.min.js").resolve().as_uri()
    body = render_calculation_sheet_html(
        result=result,
        code_edition=code_edition,
        design_method=design_method,
        is_stale=is_stale,
        incomplete_reasons=incomplete_reasons,
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<link rel='stylesheet' href='{html.escape(css_uri)}'>"
        f"<script src='{html.escape(js_uri)}'></script>"
        "</head><body style='margin:6px; font-family:\"Segoe UI\", Arial, sans-serif;'>"
        f"{body}</body></html>"
    )
