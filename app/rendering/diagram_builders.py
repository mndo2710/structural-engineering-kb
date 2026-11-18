"""Qt-independent DiagramSpec builders for Panel 2 and report exporters (WP-8).

Strict architectural contract:
- Zero PySide6 / Qt imports.
- Zero structural engineering equations.
- Geometry shapes & dimensions reflect draft inputs immediately.
- Force vectors, derived parameters, and warning pills come strictly from
  CalculationResult (never fabricated when result is None).
"""

from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    CalculationResult,
    DiagramCalloutPill,
    DiagramDimension,
    DiagramForceVector,
    DiagramShape,
    DiagramSpec,
)
from app.registry import ModuleMaturity, get_module_registry


def _safe_float(data: Dict[str, Any], key: str) -> Optional[float]:
    val = data.get(key)
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_str(data: Dict[str, Any], key: str) -> str:
    val = data.get(key)
    return "" if val is None else str(val).strip()


def _fmt_dim(label_prefix: str, val: Optional[float], unit: str) -> str:
    if val is None:
        return f"{label_prefix} = —"
    unit_suffix = f" {unit}" if unit else ""
    return f"{label_prefix} = {val:.2f}{unit_suffix}".replace(".00 ", " ").replace(".00", "")


def _build_stale_and_result_extras(
    result: Optional[CalculationResult],
    is_stale: bool,
) -> Tuple[str, List[DiagramCalloutPill]]:
    if result is None:
        return "", []

    pills: List[DiagramCalloutPill] = []
    badge = f"{result.code_edition} ({result.design_method.value}) · DCR = {result.dcr:.2f} ({result.status.value})"
    if is_stale:
        badge += " [STALE — Re-run required]"
        pills.append(
            DiagramCalloutPill(
                text="Inputs modified — prior forces are STALE",
                severity="warning",
                position="top_right",
            )
        )

    for w in result.warnings:
        pills.append(DiagramCalloutPill(text=str(w), severity="warning", position="top_right"))

    return badge, pills


def _build_wood_bolt_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    t_m = _safe_float(draft_inputs, "t_m_in")
    t_s = _safe_float(draft_inputs, "t_s_in")
    e_end_m = _safe_float(draft_inputs, "e_end_m_in")
    d_in = _safe_float(draft_inputs, "D_in")
    shear_planes = _safe_str(draft_inputs, "shear_planes")
    side_mat = _safe_str(draft_inputs, "side_material")
    n_rows = _safe_float(draft_inputs, "n_rows")
    n_bolts = _safe_float(draft_inputs, "n_bolts_per_row")

    geom_params: Dict[str, Any] = {
        "t_m_in": t_m,
        "t_s_in": t_s,
        "e_end_m_in": e_end_m,
        "D_in": d_in,
        "shear_planes": shear_planes,
        "side_material": side_mat,
        "n_rows": n_rows,
        "n_bolts_per_row": n_bolts,
    }

    shapes: List[DiagramShape] = [
        DiagramShape("main_member", "rect", (60.0, 100.0, 180.0, 32.0), "#fde6cf", "#343a40", 1.5, "Main"),
        DiagramShape("side_member", "rect", (140.0, 68.0, 180.0, 32.0), "#fde6cf", "#343a40", 1.5, "Side"),
        DiagramShape("bolt_dowel", "rect", (183.0, 54.0, 14.0, 92.0), "#e67e22", "#c86816", 1.5, "Bolt"),
    ]
    if "double" in shear_planes.lower():
        shapes.append(
            DiagramShape("side_member_2", "rect", (140.0, 132.0, 180.0, 32.0), "#fde6cf", "#343a40", 1.5, "Side 2")
        )

    dims: List[DiagramDimension] = [
        DiagramDimension("tm", (75.0, 100.0), (75.0, 132.0), _fmt_dim("t_m", t_m, "in."), "t_m", t_m, "in."),
        DiagramDimension("ts", (326.0, 68.0), (326.0, 100.0), _fmt_dim("t_s", t_s, "in."), "t_s", t_s, "in."),
        DiagramDimension("e_end_m", (190.0, 150.0), (240.0, 150.0), _fmt_dim("e_end,m", e_end_m, "in."), "e_end,m", e_end_m, "in.", "#a75815"),
        DiagramDimension("D", (183.0, 48.0), (197.0, 48.0), _fmt_dim("D", d_in, "in."), "D", d_in, "in."),
    ]

    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        p_dem = result.input_parameters.get("P_demand_lbs", result.demand)
        c_delta = result.intermediate_results.get("C_Delta")
        derived = {
            "P_demand_lbs": p_dem,
            "C_Delta": c_delta,
            "C_g": result.intermediate_results.get("C_g"),
            "governing_yield_mode": result.intermediate_results.get("governing_yield_mode"),
            "Z_prime_single_lbs": result.intermediate_results.get("Z_prime_single_lbs"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.extend([
            DiagramForceVector("P_left", (56.0, 116.0), (-1.0, 0.0), f"P = {float(p_dem):.0f} lb{stale_tag}", float(p_dem), "lbs", is_stale=is_stale),
            DiagramForceVector("P_right", (324.0, 84.0), (1.0, 0.0), f"P = {float(p_dem):.0f} lb{stale_tag}", float(p_dem), "lbs", is_stale=is_stale),
        ])
        if c_delta is not None:
            sev = "warning" if float(c_delta) < 1.0 else "info"
            pills.insert(0, DiagramCalloutPill(text=f"C_Δ = {float(c_delta):.2f}{stale_tag}", severity=sev, position="top_right"))

    return DiagramSpec(
        diagram_id="wood_bolt_lateral",
        module_id=module_id,
        title="Bolted Wood Connection Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=tuple(shapes),
        dimensions=tuple(dims),
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_wood_fastener_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    d_in = _safe_float(draft_inputs, "D_in")
    l_in = _safe_float(draft_inputs, "L_in")
    t_s = _safe_float(draft_inputs, "t_s_in")
    n_fast = _safe_float(draft_inputs, "n_fasteners")
    ftype = _safe_str(draft_inputs, "fastener_type")

    geom_params = {
        "D_in": d_in,
        "L_in": l_in,
        "t_s_in": t_s,
        "n_fasteners": n_fast,
        "fastener_type": ftype,
    }
    shapes = (
        DiagramShape("main_wood", "rect", (110.0, 70.0, 130.0, 90.0), "#fde6cf", "#343a40", 1.5, "Main"),
        DiagramShape("side_member", "rect", (70.0, 70.0, 40.0, 90.0), "#e9ecef", "#343a40", 1.5, "Side"),
        DiagramShape("fastener_shank", "rect", (62.0, 108.0, 110.0, 10.0), "#e67e22", "#c86816", 1.5, "Fastener"),
    )
    dims = (
        DiagramDimension("ts", (70.0, 56.0), (110.0, 56.0), _fmt_dim("t_s", t_s, "in."), "t_s", t_s, "in."),
        DiagramDimension("L", (62.0, 172.0), (172.0, 172.0), _fmt_dim("L", l_in, "in."), "L", l_in, "in."),
        DiagramDimension("D", (180.0, 108.0), (180.0, 118.0), _fmt_dim("D", d_in, "in."), "D", d_in, "in."),
    )

    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        v_dem = result.input_parameters.get("V_demand_lbs")
        t_dem = result.input_parameters.get("T_demand_lbs")
        derived = {
            "Z_ref_lbs": result.intermediate_results.get("Z_ref_lbs"),
            "V_demand_lbs": v_dem,
            "T_demand_lbs": t_dem,
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(v_dem, (int, float)) and v_dem > 0:
            forces.append(DiagramForceVector("V_lat", (68.0, 62.0), (0.0, 1.0), f"V = {float(v_dem):.0f} lbs{stale_tag}", float(v_dem), "lbs", is_stale=is_stale))
        if isinstance(t_dem, (int, float)) and t_dem > 0:
            forces.append(DiagramForceVector("T_with", (58.0, 113.0), (-1.0, 0.0), f"T = {float(t_dem):.0f} lbs{stale_tag}", float(t_dem), "lbs", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="wood_fastener_nds",
        module_id=module_id,
        title="Wood Fastener Lateral & Withdrawal Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_shear_wall_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    h_ft = _safe_float(draft_inputs, "h_ft")
    bs_ft = _safe_float(draft_inputs, "bs_ft")
    holdown_model = _safe_str(draft_inputs, "holdown_model")

    geom_params = {"h_ft": h_ft, "bs_ft": bs_ft, "holdown_model": holdown_model}
    shapes = (
        DiagramShape("wall_panel", "rect", (130.0, 40.0, 110.0, 120.0), "#fde6cf", "#343a40", 2.0, "Shear Wall"),
        DiagramShape("holdown_l", "rect", (134.0, 136.0, 12.0, 24.0), "#007bff", "#343a40", 1.0, "HD"),
        DiagramShape("holdown_r", "rect", (224.0, 136.0, 12.0, 24.0), "#007bff", "#343a40", 1.0, "HD"),
    )
    dims = (
        DiagramDimension("h", (252.0, 40.0), (252.0, 160.0), _fmt_dim("h", h_ft, "ft"), "h", h_ft, "ft"),
        DiagramDimension("bs", (130.0, 174.0), (240.0, 174.0), _fmt_dim("b_s", bs_ft, "ft"), "b_s", bs_ft, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        v_dem = result.input_parameters.get("V_asd_lbs", result.intermediate_results.get("V_demand_lbs"))
        t_hd = result.intermediate_results.get("T_holdown_demand_lbs")
        derived = {
            "V_asd_lbs": v_dem,
            "T_holdown_demand_lbs": t_hd,
            "v_unit_demand_plf": result.intermediate_results.get("v_unit_demand_plf"),
            "story_drift_in": result.intermediate_results.get("story_drift_in"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(v_dem, (int, float)):
            forces.append(DiagramForceVector("V_lat", (80.0, 44.0), (1.0, 0.0), f"V = {float(v_dem):.0f} lbs{stale_tag}", float(v_dem), "lbs", is_stale=is_stale))
        if isinstance(t_hd, (int, float)):
            forces.append(DiagramForceVector("T_hd", (140.0, 160.0), (0.0, 1.0), f"T_HD = {float(t_hd):.0f} lbs{stale_tag}", float(t_hd), "lbs", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="wood_shear_wall_sdpws",
        module_id=module_id,
        title="Wood-Frame Shear Wall & Holdown Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_diaphragm_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    l_span = _safe_float(draft_inputs, "L_span_ft")
    w_depth = _safe_float(draft_inputs, "W_depth_ft")
    l_drag = _safe_float(draft_inputs, "unsupported_drag_ft")

    geom_params = {"L_span_ft": l_span, "W_depth_ft": w_depth, "unsupported_drag_ft": l_drag}
    shapes = (
        DiagramShape("diaphragm_plan", "rect", (95.0, 58.0, 180.0, 80.0), "#f8f9fa", "#343a40", 2.0, "Diaphragm"),
    )
    dims = (
        DiagramDimension("L_span", (95.0, 152.0), (275.0, 152.0), _fmt_dim("L", l_span, "ft"), "L", l_span, "ft"),
        DiagramDimension("W_depth", (288.0, 58.0), (288.0, 138.0), _fmt_dim("W", w_depth, "ft"), "W", w_depth, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        v_unit = result.intermediate_results.get("v_unit_demand_plf")
        t_chord = result.intermediate_results.get("T_chord_max_lbs")
        f_drag = result.intermediate_results.get("F_drag_lbs")
        derived = {
            "v_unit_demand_plf": v_unit,
            "T_chord_max_lbs": t_chord,
            "F_drag_lbs": f_drag,
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(t_chord, (int, float)):
            forces.append(DiagramForceVector("T_chord", (185.0, 50.0), (1.0, 0.0), f"T_chord = {float(t_chord):.0f} lbs{stale_tag}", float(t_chord), "lbs", is_stale=is_stale))
        if isinstance(v_unit, (int, float)):
            forces.append(DiagramForceVector("v_unit", (88.0, 98.0), (0.0, 1.0), f"v = {float(v_unit):.1f} plf{stale_tag}", float(v_unit), "plf", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="wood_diaphragm_sdpws",
        module_id=module_id,
        title="Blocked Wood Diaphragm, Chord & Collector Plan",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_simpson_hanger_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    h_joist = _safe_float(draft_inputs, "H_joist_in")
    hanger_model = _safe_str(draft_inputs, "hanger_model")
    tie_model = _safe_str(draft_inputs, "tie_model")

    geom_params = {"H_joist_in": h_joist, "hanger_model": hanger_model, "tie_model": tie_model}
    shapes = (
        DiagramShape("header_beam", "rect", (105.0, 68.0, 55.0, 65.0), "#fde6cf", "#343a40", 2.0, "Header"),
        DiagramShape("carried_joist", "rect", (160.0, 76.0, 110.0, 48.0), "#fde6cf", "#343a40", 2.0, "Joist"),
        DiagramShape("simpson_hanger", "rect", (154.0, 80.0, 14.0, 44.0), "#adb5bd", "#343a40", 1.5, hanger_model or "Hanger"),
    )
    dims = (
        DiagramDimension("H_joist", (280.0, 76.0), (280.0, 124.0), _fmt_dim("H", h_joist, "in."), "H", h_joist, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        r_roof = result.input_parameters.get("R_roof_lbs")
        u_tie = result.input_parameters.get("U_tie_lbs")
        derived = {
            "P_allow_125_lbs": result.intermediate_results.get("P_allow_125_lbs"),
            "U_allow_tie_lbs": result.intermediate_results.get("U_allow_tie_lbs"),
            "unity_U_plus_F2": result.intermediate_results.get("unity_U_plus_F2"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(r_roof, (int, float)):
            forces.append(DiagramForceVector("R_roof", (215.0, 64.0), (0.0, 1.0), f"R = {float(r_roof):.0f} lbs{stale_tag}", float(r_roof), "lbs", is_stale=is_stale))
        if isinstance(u_tie, (int, float)):
            forces.append(DiagramForceVector("U_tie", (215.0, 142.0), (0.0, -1.0), f"U_tie = {float(u_tie):.0f} lbs{stale_tag}", float(u_tie), "lbs", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="wood_simpson_hanger_tie",
        module_id=module_id,
        title="Simpson Joist Hanger & Hurricane Tie Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_parapet_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    h_roof = _safe_float(draft_inputs, "h_roof_ft")
    h_par = _safe_float(draft_inputs, "h_par_ft")
    backspan = _safe_float(draft_inputs, "backspan_ft")

    geom_params = {"h_roof_ft": h_roof, "h_par_ft": h_par, "backspan_ft": backspan}
    shapes = (
        DiagramShape("roof_deck", "rect", (180.0, 100.0, 130.0, 14.0), "#e9ecef", "#343a40", 2.0, "Roof"),
        DiagramShape("ext_wall", "rect", (166.0, 100.0, 14.0, 60.0), "#e9ecef", "#343a40", 2.0, "Wall"),
        DiagramShape("parapet_stud", "rect", (166.0, 35.0, 14.0, 65.0), "#fde6cf", "#343a40", 2.0, "Parapet"),
    )
    dims = (
        DiagramDimension("h_par", (192.0, 35.0), (192.0, 100.0), _fmt_dim("h_par", h_par, "ft"), "h_par", h_par, "ft", "#d96818"),
        DiagramDimension("h_roof", (320.0, 100.0), (320.0, 160.0), _fmt_dim("h", h_roof, "ft"), "h", h_roof, "ft"),
        DiagramDimension("L_back", (180.0, 126.0), (310.0, 126.0), _fmt_dim("L_back", backspan, "ft"), "L_back", backspan, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        p_gov = result.intermediate_results.get("p_gov_unfactored_psf")
        derived = {
            "p_gov_psf": p_gov,
            "q_p_psf": result.intermediate_results.get("q_p_psf"),
            "M_base_lb_ft": result.intermediate_results.get("M_base_lb_ft"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(p_gov, (int, float)):
            forces.append(DiagramForceVector("p_gov", (105.0, 68.0), (1.0, 0.0), f"p_gov = {float(p_gov):.1f} psf{stale_tag}", float(p_gov), "psf", "#007bff", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="cc_parapet",
        module_id=module_id,
        title="Parapet Wind Pressure Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_overhang_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    l_oh = _safe_float(draft_inputs, "L_oh_ft")
    l_back = _safe_float(draft_inputs, "L_back_ft")
    h_roof = _safe_float(draft_inputs, "h_roof_ft")

    geom_params = {"L_oh_ft": l_oh, "L_back_ft": l_back, "h_roof_ft": h_roof}
    shapes = (
        DiagramShape("ext_wall", "rect", (170.0, 92.0, 16.0, 68.0), "#e9ecef", "#343a40", 2.0, "Wall"),
        DiagramShape("rafter", "polygon", (85.0, 112.0, 300.0, 68.0, 300.0, 84.0, 85.0, 128.0), "#fde6cf", "#343a40", 2.0, "Rafter"),
    )
    dims = (
        DiagramDimension("L_oh", (85.0, 74.0), (170.0, 74.0), _fmt_dim("L_oh", l_oh, "ft"), "L_oh", l_oh, "ft"),
        DiagramDimension("L_back", (186.0, 140.0), (300.0, 140.0), _fmt_dim("L_back", l_back, "ft"), "L_back", l_back, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        r_up = result.intermediate_results.get("R_uplift_lbs", result.demand)
        derived = {
            "R_uplift_lbs": r_up,
            "p_oh_uplift_psf": result.intermediate_results.get("p_oh_uplift_psf"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(r_up, (int, float)):
            forces.append(DiagramForceVector("R_uplift", (178.0, 115.0), (0.0, -1.0), f"R_tie = {float(r_up):.0f} lbs{stale_tag}", float(r_up), "lbs", "#007bff", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="cc_overhang",
        module_id=module_id,
        title="Roof Overhang Wind Uplift Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_awning_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    bc_ft = _safe_float(draft_inputs, "Bc_ft")
    hc_ft = _safe_float(draft_inputs, "hc_ft")
    support_type = _safe_str(draft_inputs, "support_type")

    geom_params = {"Bc_ft": bc_ft, "hc_ft": hc_ft, "support_type": support_type}
    shapes = (
        DiagramShape("main_wall", "rect", (120.0, 32.0, 16.0, 130.0), "#e9ecef", "#343a40", 2.0, "Wall"),
        DiagramShape("canopy_deck", "rect", (136.0, 96.0, 120.0, 12.0), "#ced4da", "#343a40", 2.0, "Canopy"),
        DiagramShape("tie_rod", "line", (136.0, 52.0, 235.0, 96.0), "#c86816", "#c86816", 2.0, "Tie-Back"),
    )
    dims = (
        DiagramDimension("B_c", (136.0, 124.0), (256.0, 124.0), _fmt_dim("B_c", bc_ft, "ft"), "B_c", bc_ft, "ft"),
        DiagramDimension("h_c", (104.0, 96.0), (104.0, 162.0), _fmt_dim("h_c", hc_ft, "ft"), "h_c", hc_ft, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        m_wall = max(
            float(result.intermediate_results.get("M_down_wall_lb_ft", 0.0)),
            float(result.intermediate_results.get("M_up_wall_lb_ft", 0.0)),
        )
        derived = {
            "M_wall_lb_ft": m_wall,
            "p_net_pos_psf": result.intermediate_results.get("p_net_pos_psf"),
            "p_net_neg_psf": result.intermediate_results.get("p_net_neg_psf"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(DiagramForceVector("M_wall", (136.0, 102.0), (0.0, -1.0), f"M = {m_wall:.0f} lb-ft{stale_tag}", m_wall, "lb-ft", "#007bff", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="cc_awning",
        module_id=module_id,
        title="Attached Awning & Canopy Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_trellis_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    hp_ft = _safe_float(draft_inputs, "Hp_ft")
    lt_ft = _safe_float(draft_inputs, "Lt_ft")
    bt_ft = _safe_float(draft_inputs, "Bt_ft")

    geom_params = {"Hp_ft": hp_ft, "Lt_ft": lt_ft, "Bt_ft": bt_ft}
    shapes = (
        DiagramShape("post_l", "rect", (110.0, 56.0, 12.0, 96.0), "#fde6cf", "#343a40", 2.0, "Post L"),
        DiagramShape("post_r", "rect", (250.0, 56.0, 12.0, 96.0), "#fde6cf", "#343a40", 2.0, "Post R"),
        DiagramShape("beam", "rect", (100.0, 46.0, 172.0, 10.0), "#fde6cf", "#343a40", 2.0, "Slats"),
    )
    dims = (
        DiagramDimension("H_p", (274.0, 56.0), (274.0, 152.0), _fmt_dim("H_p", hp_ft, "ft"), "H_p", hp_ft, "ft"),
        DiagramDimension("L_t", (110.0, 166.0), (262.0, 166.0), _fmt_dim("L_t", lt_ft, "ft"), "L_t", lt_ft, "ft"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        v_post = result.intermediate_results.get("V_post_lbs")
        derived = {
            "V_post_lbs": v_post,
            "M_base_lb_ft": result.intermediate_results.get("M_base_lb_ft"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(v_post, (int, float)):
            forces.append(DiagramForceVector("V_post", (55.0, 51.0), (1.0, 0.0), f"V_post = {float(v_post):.1f} lbs{stale_tag}", float(v_post), "lbs", "#007bff", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="cc_trellis",
        module_id=module_id,
        title="Open-Frame Trellis & Pergola Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_guardrail_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    h_guard = _safe_float(draft_inputs, "H_guard_in")
    s_post = _safe_float(draft_inputs, "S_post_ft")
    d_bolt = _safe_float(draft_inputs, "d_bolt_in")

    geom_params = {"H_guard_in": h_guard, "S_post_ft": s_post, "d_bolt_in": d_bolt}
    shapes = (
        DiagramShape("deck_slab", "rect", (115.0, 126.0, 140.0, 16.0), "#e9ecef", "#343a40", 2.0, "Deck"),
        DiagramShape("base_plate", "rect", (167.0, 120.0, 36.0, 6.0), "#adb5bd", "#343a40", 1.5, "Plate"),
        DiagramShape("guard_post", "rect", (179.0, 51.0, 12.0, 69.0), "#adb5bd", "#343a40", 2.0, "Post"),
    )
    dims = (
        DiagramDimension("H_guard", (205.0, 51.0), (205.0, 120.0), _fmt_dim("H_guard", h_guard, "in."), "H_guard", h_guard, "in."),
        DiagramDimension("d_bolt", (167.0, 152.0), (203.0, 152.0), _fmt_dim("d_bolt", d_bolt, "in."), "d_bolt", d_bolt, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)

    if result is not None:
        v_gov = result.intermediate_results.get("V_post_gov_lbs")
        t_bolt = result.intermediate_results.get("T_bolt_gov_lbs")
        derived = {
            "V_post_gov_lbs": v_gov,
            "T_bolt_gov_lbs": t_bolt,
            "M_base_gov_lb_ft": result.intermediate_results.get("M_base_gov_lb_ft"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(v_gov, (int, float)):
            forces.append(DiagramForceVector("P_rail", (118.0, 56.0), (1.0, 0.0), f"P = {float(v_gov):.0f} lbs{stale_tag}", float(v_gov), "lbs", "#007bff", is_stale=is_stale))

    return DiagramSpec(
        diagram_id="cc_guardrail",
        module_id=module_id,
        title="Guardrail & Handrail Post Schematic",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_shear_tab_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    t_p = _safe_float(draft_inputs, "t_plate_in")
    d_p = _safe_float(draft_inputs, "d_p_in")
    a_in = _safe_float(draft_inputs, "a_in")
    n_b = _safe_float(draft_inputs, "n_bolts")
    beam_sec = _safe_str(draft_inputs, "beam_section") or "Beam"
    sup_sec = _safe_str(draft_inputs, "support_section") or "Support"

    geom_params = {"t_plate_in": t_p, "d_p_in": d_p, "a_in": a_in, "n_bolts": n_b}
    n_draw = max(1, min(6, int(n_b or 3)))
    plate_h = 84.0 if d_p is None else min(105.0, max(56.0, d_p * 8.0))
    plate_top = 100.0 - plate_h / 2.0

    shapes: List[DiagramShape] = [
        DiagramShape("support_col", "rect", (62.0, 26.0, 44.0, 148.0), "#ced4da", "#343a40", 2.0, sup_sec[:10]),
        DiagramShape("beam_web", "rect", (130.0, 42.0, 190.0, 116.0), "#dee2e6", "#343a40", 1.8, beam_sec[:12]),
        DiagramShape("shear_tab", "rect", (106.0, plate_top, 56.0, plate_h), "#74c0fc", "#1864ab", 2.0, "Plate"),
        DiagramShape("weld_line", "line", (106.0, plate_top, 106.0, plate_top + plate_h), "#e03131", "#e03131", 3.0),
    ]
    for idx in range(n_draw):
        cy = plate_top + (idx + 1) * plate_h / (n_draw + 1)
        shapes.append(DiagramShape(f"bolt_{idx+1}", "circle", (142.0, cy, 5.0), "#495057", "#212529", 1.5))

    dims = (
        DiagramDimension("d_p", (174.0, plate_top), (174.0, plate_top + plate_h), _fmt_dim("d_p", d_p, "in."), "d_p", d_p, "in."),
        DiagramDimension("a", (106.0, plate_top - 14.0), (142.0, plate_top - 14.0), _fmt_dim("a", a_in, "in."), "a", a_in, "in."),
        DiagramDimension("t_p", (106.0, plate_top + plate_h + 14.0), (162.0, plate_top + plate_h + 14.0), _fmt_dim("t_p", t_p, "in."), "t_p", t_p, "in."),
    )

    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        v_dem = result.demand
        derived = {
            "C_icor": result.intermediate_results.get("C_icor"),
            "cap_bolts_kips": result.intermediate_results.get("cap_bolts_kips"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("V_demand", (255.0, 56.0), (0.0, 1.0), f"V = {v_dem:.1f} kips{stale_tag}", float(v_dem), "kips", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="aisc_shear_tab",
        module_id=module_id,
        title="AISC Single-Plate Shear Tab Connection",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=tuple(shapes),
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_bolts_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    d_b = _safe_float(draft_inputs, "d_b_in")
    t_p = _safe_float(draft_inputs, "t_plate_in")
    w_p = _safe_float(draft_inputs, "w_plate_in")
    s_in = _safe_float(draft_inputs, "s_in")
    l_e = _safe_float(draft_inputs, "l_e_in")
    n_row = max(1, min(5, int(_safe_float(draft_inputs, "n_bolts_per_line") or 2)))
    n_lines = max(1, min(4, int(_safe_float(draft_inputs, "n_lines") or 2)))

    geom_params = {"d_b_in": d_b, "t_plate_in": t_p, "w_plate_in": w_p, "s_in": s_in, "l_e_in": l_e}
    shapes: List[DiagramShape] = [
        DiagramShape("left_plate", "rect", (56.0, 58.0, 148.0, 84.0), "#d0ebff", "#1864ab", 2.0, "Plate 1"),
        DiagramShape("right_plate", "rect", (176.0, 62.0, 148.0, 76.0), "#e9ecef", "#343a40", 2.0, "Plate 2"),
    ]
    for r in range(n_lines):
        cy = 62.0 + (r + 1) * 76.0 / (n_lines + 1)
        for c in range(n_row):
            cx = 188.0 + c * 28.0
            shapes.append(DiagramShape(f"b_{r}_{c}", "circle", (cx, cy, 4.5), "#495057", "#212529", 1.5))

    dims = (
        DiagramDimension("w_p", (42.0, 58.0), (42.0, 142.0), _fmt_dim("w_p", w_p, "in."), "w_p", w_p, "in."),
        DiagramDimension("s", (188.0, 44.0), (216.0, 44.0), _fmt_dim("s", s_in, "in."), "s", s_in, "in."),
        DiagramDimension("d_b", (188.0, 156.0), (216.0, 156.0), _fmt_dim("d_b", d_b, "in."), "d_b", d_b, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        v_dem = result.demand
        derived = {
            "cap_bolt_shear_kips": result.intermediate_results.get("cap_bolt_shear_kips"),
            "cap_bearing_kips": result.intermediate_results.get("cap_bearing_kips"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.extend([
            DiagramForceVector("V_left", (56.0, 100.0), (-1.0, 0.0), f"V = {v_dem:.1f} kips{stale_tag}", float(v_dem), "kips", "#d96818", is_stale=is_stale),
            DiagramForceVector("V_right", (324.0, 100.0), (1.0, 0.0), f"V = {v_dem:.1f} kips{stale_tag}", float(v_dem), "kips", "#d96818", is_stale=is_stale),
        ])

    return DiagramSpec(
        diagram_id="aisc_bolt_bearing",
        module_id=module_id,
        title="AISC Bolted Shear & Bearing Splice",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=tuple(shapes),
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_welds_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    w_leg = _safe_float(draft_inputs, "w_leg_in")
    b_w = _safe_float(draft_inputs, "b_w_in")
    d_w = _safe_float(draft_inputs, "d_w_in")
    e_face = _safe_float(draft_inputs, "e_face_in")
    cfg = (_safe_str(draft_inputs, "weld_config") or "C_shape").lower()

    geom_params = {"w_leg_in": w_leg, "b_w_in": b_w, "d_w_in": d_w, "e_face_in": e_face}
    shapes: List[DiagramShape] = [
        DiagramShape("support_col", "rect", (68.0, 26.0, 48.0, 148.0), "#ced4da", "#343a40", 2.0, "Support"),
        DiagramShape("bracket_plate", "rect", (116.0, 52.0, 156.0, 96.0), "#d0ebff", "#1864ab", 2.0, "Bracket"),
        DiagramShape("weld_vert", "line", (116.0, 52.0, 116.0, 148.0), "#e03131", "#e03131", 3.5),
    ]
    if "c" in cfg:
        shapes.append(DiagramShape("weld_top", "line", (116.0, 52.0, 186.0, 52.0), "#e03131", "#e03131", 3.5))
        shapes.append(DiagramShape("weld_bot", "line", (116.0, 148.0, 186.0, 148.0), "#e03131", "#e03131", 3.5))

    dims = (
        DiagramDimension("d_w", (98.0, 52.0), (98.0, 148.0), _fmt_dim("d_w", d_w, "in."), "d_w", d_w, "in."),
        DiagramDimension("b_w", (116.0, 38.0), (186.0, 38.0), _fmt_dim("b_w", b_w, "in."), "b_w", b_w, "in."),
        DiagramDimension("e_face", (116.0, 166.0), (272.0, 166.0), _fmt_dim("e_face", e_face, "in."), "e_face", e_face, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        f_max = result.intermediate_results.get("f_max_kips_per_in")
        derived = {"f_max_kips_per_in": f_max, "L_w_in": result.intermediate_results.get("L_w_in")}
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("V_bracket", (272.0, 52.0), (0.0, 1.0), f"V = {result.demand:.1f} kips{stale_tag}", float(result.demand), "kips", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="aisc_welded_connection",
        module_id=module_id,
        title="AISC Eccentric Fillet Weld Group",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=tuple(shapes),
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_angles_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    l_a = _safe_float(draft_inputs, "L_a_in")
    c_cope = _safe_float(draft_inputs, "c_cope_in")
    dc_cope = _safe_float(draft_inputs, "dc_cope_in")
    n_b = max(1, min(5, int(_safe_float(draft_inputs, "n_bolts") or 2)))

    geom_params = {"L_a_in": l_a, "c_cope_in": c_cope, "dc_cope_in": dc_cope, "n_bolts": n_b}
    shapes: List[DiagramShape] = [
        DiagramShape("support_girder", "rect", (64.0, 30.0, 44.0, 140.0), "#ced4da", "#343a40", 2.0, "Support"),
        DiagramShape("beam_coped", "polygon", (134.0, 74.0, 180.0, 74.0, 180.0, 48.0, 316.0, 48.0, 316.0, 152.0, 134.0, 152.0), "#dee2e6", "#343a40", 1.8, "Beam"),
        DiagramShape("clip_angle", "rect", (108.0, 78.0, 46.0, 68.0), "#74c0fc", "#1864ab", 2.0, "Angle"),
    ]
    for idx in range(n_b):
        cy = 78.0 + (idx + 1) * 68.0 / (n_b + 1)
        shapes.append(DiagramShape(f"bolt_{idx+1}", "circle", (136.0, cy, 4.5), "#495057", "#212529", 1.5))

    dims = (
        DiagramDimension("L_a", (92.0, 78.0), (92.0, 146.0), _fmt_dim("L_a", l_a, "in."), "L_a", l_a, "in."),
        DiagramDimension("c_cope", (134.0, 36.0), (180.0, 36.0), _fmt_dim("c", c_cope, "in."), "c_cope", c_cope, "in."),
        DiagramDimension("dc_cope", (190.0, 48.0), (190.0, 74.0), _fmt_dim("d_c", dc_cope, "in."), "dc_cope", dc_cope, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        derived = {"cap_bolts_kips": result.intermediate_results.get("cap_bolts_kips")}
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("V_beam", (260.0, 56.0), (0.0, 1.0), f"V = {result.demand:.1f} kips{stale_tag}", float(result.demand), "kips", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="aisc_angle_connection",
        module_id=module_id,
        title="AISC Clip Angle & Coped Beam Shear",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=tuple(shapes),
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_base_plate_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    b_in = _safe_float(draft_inputs, "B_in")
    n_in = _safe_float(draft_inputs, "N_in")
    t_p = _safe_float(draft_inputs, "t_p_in")
    d_a = _safe_float(draft_inputs, "d_a_in")
    col_sec = _safe_str(draft_inputs, "column_section") or "Column"

    geom_params = {"B_in": b_in, "N_in": n_in, "t_p_in": t_p, "d_a_in": d_a}
    shapes = (
        DiagramShape("pedestal", "rect", (72.0, 134.0, 236.0, 44.0), "#e9ecef", "#495057", 2.0, "Concrete Pier"),
        DiagramShape("grout", "rect", (102.0, 126.0, 176.0, 8.0), "#dee2e6", "#868e96", 1.0),
        DiagramShape("base_plate", "rect", (102.0, 112.0, 176.0, 14.0), "#74c0fc", "#1864ab", 2.0, "Base Plate"),
        DiagramShape("column", "rect", (152.0, 32.0, 76.0, 80.0), "#adb5bd", "#343a40", 2.0, col_sec[:10]),
        DiagramShape("rod_L", "rect", (118.0, 104.0, 8.0, 56.0), "#495057", "#212529", 1.2),
        DiagramShape("rod_R", "rect", (254.0, 104.0, 8.0, 56.0), "#495057", "#212529", 1.2),
    )
    dims = (
        DiagramDimension("N", (102.0, 186.0), (278.0, 186.0), _fmt_dim("N", n_in, "in."), "N", n_in, "in."),
        DiagramDimension("t_p", (86.0, 112.0), (86.0, 126.0), _fmt_dim("t_p", t_p, "in."), "t_p", t_p, "in."),
        DiagramDimension("d_a", (286.0, 112.0), (286.0, 160.0), _fmt_dim("d_a", d_a, "in."), "d_a", d_a, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        f_p = result.intermediate_results.get("f_p_actual_ksi")
        t_rods = result.intermediate_results.get("T_rods_kips")
        derived = {"f_p_actual_ksi": f_p, "T_rods_kips": t_rods, "Y_brg_in": result.intermediate_results.get("Y_brg_in")}
        stale_tag = " [STALE]" if is_stale else ""
        if isinstance(f_p, (int, float)):
            forces.append(
                DiagramForceVector("f_p", (230.0, 134.0), (0.0, 1.0), f"f_p = {float(f_p):.2f} ksi{stale_tag}", float(f_p), "ksi", "#d96818", is_stale=is_stale)
            )
        if isinstance(t_rods, (int, float)) and float(t_rods) > 0:
            forces.append(
                DiagramForceVector("T_rods", (122.0, 104.0), (0.0, -1.0), f"T = {float(t_rods):.1f} kips{stale_tag}", float(t_rods), "kips", "#e03131", is_stale=is_stale)
            )

    return DiagramSpec(
        diagram_id="aisc_base_plate",
        module_id=module_id,
        title="AISC DG1 Column Base Plate & Anchor Rods",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aisc_hss_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    theta_deg = _safe_float(draft_inputs, "theta_deg")
    chord_sec = _safe_str(draft_inputs, "chord_section") or "HSS Chord"
    branch_sec = _safe_str(draft_inputs, "branch_section") or "HSS Branch"

    geom_params = {"theta_deg": theta_deg, "chord_section": chord_sec, "branch_section": branch_sec}
    shapes = (
        DiagramShape("chord", "rect", (56.0, 114.0, 268.0, 52.0), "#ced4da", "#343a40", 2.0, chord_sec[:14]),
        DiagramShape("branch", "rect", (152.0, 34.0, 76.0, 80.0), "#74c0fc", "#1864ab", 2.0, branch_sec[:14]),
    )
    dims = (
        DiagramDimension("theta", (152.0, 102.0), (112.0, 114.0), _fmt_dim("theta", theta_deg, "deg"), "theta", theta_deg, "deg"),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        derived = {
            "beta": result.intermediate_results.get("beta"),
            "Q_f": result.intermediate_results.get("Q_f"),
            "interaction_ratio": result.intermediate_results.get("interaction_ratio"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("HSS_load", (238.0, 50.0), (0.0, 1.0), f"DCR = {result.dcr:.2f}{stale_tag}", float(result.dcr), "", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="aisc_hss_connection",
        module_id=module_id,
        title="AISC Ch. K HSS-to-HSS Connection",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_aci318_anchors_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    d_a = _safe_float(draft_inputs, "d_a_in")
    h_ef = _safe_float(draft_inputs, "h_ef_in")
    c_a1 = _safe_float(draft_inputs, "c_a1_in")
    h_a = _safe_float(draft_inputs, "h_a_in")

    geom_params = {"d_a_in": d_a, "h_ef_in": h_ef, "c_a1_in": c_a1, "h_a_in": h_a}
    shapes = (
        DiagramShape("concrete_slab", "rect", (56.0, 82.0, 268.0, 92.0), "#e9ecef", "#495057", 2.0, "Concrete"),
        DiagramShape("cone", "polygon", (112.0, 82.0, 186.0, 146.0, 260.0, 82.0), "#fff3bf", "#f08c00", 1.2),
        DiagramShape("anchor_shaft", "rect", (181.0, 52.0, 10.0, 94.0), "#495057", "#212529", 1.5),
        DiagramShape("anchor_head", "rect", (174.0, 142.0, 24.0, 8.0), "#343a40", "#212529", 1.5),
    )
    dims = (
        DiagramDimension("h_ef", (270.0, 82.0), (270.0, 146.0), _fmt_dim("h_ef", h_ef, "in."), "h_ef", h_ef, "in."),
        DiagramDimension("c_a1", (56.0, 68.0), (186.0, 68.0), _fmt_dim("c_a1", c_a1, "in."), "c_a1", c_a1, "in."),
        DiagramDimension("h_a", (42.0, 82.0), (42.0, 174.0), _fmt_dim("h_a", h_a, "in."), "h_a", h_a, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        derived = {
            "A_Nc_in2": result.intermediate_results.get("A_Nc_in2"),
            "N_b_lbs": result.intermediate_results.get("N_b_lbs"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("N_anchor", (186.0, 52.0), (0.0, -1.0), f"DCR = {result.dcr:.2f}{stale_tag}", float(result.dcr), "", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="aci318_anchor_tension_shear",
        module_id=module_id,
        title="ACI 318-19 Ch. 17 Concrete Breakout Cone",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_tms402_cmu_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    t_nom = _safe_float(draft_inputs, "cmu_nominal_in")
    d_b = _safe_float(draft_inputs, "d_b_in")
    l_b = _safe_float(draft_inputs, "l_b_in")
    l_be = _safe_float(draft_inputs, "l_be_shear_in")

    geom_params = {"cmu_nominal_in": t_nom, "d_b_in": d_b, "l_b_in": l_b, "l_be_shear_in": l_be}
    shapes = (
        DiagramShape("cmu_wall", "rect", (130.0, 32.0, 96.0, 144.0), "#dee2e6", "#343a40", 2.0, "Grouted CMU"),
        DiagramShape("breakout", "polygon", (226.0, 58.0, 166.0, 104.0, 226.0, 150.0), "#fff3bf", "#f08c00", 1.2),
        DiagramShape("ledger_plate", "rect", (226.0, 74.0, 16.0, 60.0), "#74c0fc", "#1864ab", 1.8),
        DiagramShape("anchor_bolt", "rect", (166.0, 99.0, 96.0, 10.0), "#495057", "#212529", 1.5),
    )
    dims = (
        DiagramDimension("t_nom", (130.0, 20.0), (226.0, 20.0), _fmt_dim("t_nom", t_nom, "in."), "t_nom", t_nom, "in."),
        DiagramDimension("l_b", (166.0, 184.0), (226.0, 184.0), _fmt_dim("l_b", l_b, "in."), "l_b", l_b, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        derived = {
            "A_pt_in2": result.intermediate_results.get("A_pt_in2"),
            "cap_t_breakout_lbs": result.intermediate_results.get("cap_t_breakout_lbs"),
        }
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("b_af", (262.0, 104.0), (1.0, 0.0), f"DCR = {result.dcr:.2f}{stale_tag}", float(result.dcr), "", "#d96818", is_stale=is_stale)
        )

    return DiagramSpec(
        diagram_id="tms402_cmu_anchorage",
        module_id=module_id,
        title="TMS 402-22 Grouted CMU Anchor Bolt",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


def _build_tms402_embedded_post_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult],
    is_stale: bool,
) -> DiagramSpec:
    h_post = _safe_float(draft_inputs, "H_post_in")
    l_e = _safe_float(draft_inputs, "L_e_in")
    z_b = _safe_float(draft_inputs, "z_b_in")
    post_sec = _safe_str(draft_inputs, "post_section") or "HSS Post"

    geom_params = {"H_post_in": h_post, "L_e_in": l_e, "z_b_in": z_b}
    shapes = (
        DiagramShape("wall_footing", "rect", (120.0, 106.0, 140.0, 74.0), "#dee2e6", "#343a40", 2.0, "CMU / Pier"),
        DiagramShape("steel_post", "rect", (176.0, 30.0, 28.0, 134.0), "#74c0fc", "#1864ab", 2.0, post_sec[:10]),
        DiagramShape("top_rebar", "line", (134.0, 118.0, 246.0, 118.0), "#e03131", "#e03131", 2.5),
        DiagramShape("bot_rebar", "line", (134.0, 156.0, 246.0, 156.0), "#e03131", "#e03131", 2.5),
    )
    dims = (
        DiagramDimension("H_post", (218.0, 30.0), (218.0, 106.0), _fmt_dim("H_post", h_post, "in."), "H_post", h_post, "in."),
        DiagramDimension("L_e", (102.0, 106.0), (102.0, 164.0), _fmt_dim("L_e", l_e, "in."), "L_e", l_e, "in."),
        DiagramDimension("z_b", (276.0, 118.0), (276.0, 156.0), _fmt_dim("z_b", z_b, "in."), "z_b", z_b, "in."),
    )
    derived: Dict[str, Any] = {}
    forces: List[DiagramForceVector] = []
    badge, pills = _build_stale_and_result_extras(result, is_stale)
    if result is not None:
        t_top = result.intermediate_results.get("T_top_kips")
        c_bot = result.intermediate_results.get("C_bot_kips")
        derived = {"T_top_kips": t_top, "C_bot_kips": c_bot, "M_post_kip_in": result.intermediate_results.get("M_post_kip_in")}
        stale_tag = " [STALE]" if is_stale else ""
        forces.append(
            DiagramForceVector("V_top", (130.0, 34.0), (1.0, 0.0), f"DCR = {result.dcr:.2f}{stale_tag}", float(result.dcr), "", "#d96818", is_stale=is_stale)
        )
        if isinstance(t_top, (int, float)):
            forces.append(
                DiagramForceVector("T_couple", (204.0, 118.0), (1.0, 0.0), f"T = {float(t_top):.2f} k{stale_tag}", float(t_top), "kips", "#e03131", is_stale=is_stale)
            )

    return DiagramSpec(
        diagram_id="tms402_embedded_post",
        module_id=module_id,
        title="Cantilever Embedded Steel Post Couple",
        has_geometry=True,
        has_engine_result=result is not None,
        is_stale=is_stale,
        geometry_params=geom_params,
        derived_params=derived,
        shapes=shapes,
        dimensions=dims,
        forces=tuple(forces),
        callouts=tuple(pills),
        summary_badge=badge,
    )


_BUILDER_MAP = {
    "wood_bolt_lateral": _build_wood_bolt_spec,
    "wood_fastener_nds": _build_wood_fastener_spec,
    "wood_nail_lateral": _build_wood_fastener_spec,
    "wood_screw_withdrawal": _build_wood_fastener_spec,
    "wood_combined_lateral_withdrawal": _build_wood_fastener_spec,
    "wood_shear_wall_sdpws": _build_shear_wall_spec,
    "wood_diaphragm_sdpws": _build_diaphragm_spec,
    "wood_simpson_hanger_tie": _build_simpson_hanger_spec,
    "asce7_parapet_wind": _build_parapet_spec,
    "asce7_roof_overhang": _build_overhang_spec,
    "asce7_awning_canopy": _build_awning_spec,
    "asce7_trellis_loads": _build_trellis_spec,
    "ibc_guardrail_loads": _build_guardrail_spec,
    "aisc_shear_tab": _build_aisc_shear_tab_spec,
    "aisc_bolt_bearing": _build_aisc_bolts_spec,
    "aisc_welded_connection": _build_aisc_welds_spec,
    "aisc_angle_connection": _build_aisc_angles_spec,
    "aisc_base_plate": _build_aisc_base_plate_spec,
    "aisc_hss_connection": _build_aisc_hss_spec,
    "aci318_anchor_tension_shear": _build_aci318_anchors_spec,
    "tms402_cmu_anchorage": _build_tms402_cmu_spec,
    "tms402_embedded_post": _build_tms402_embedded_post_spec,
}


def build_diagram_spec(
    module_id: str,
    draft_inputs: Dict[str, Any],
    result: Optional[CalculationResult] = None,
    is_stale: bool = False,
) -> DiagramSpec:
    """Build a Qt-independent DiagramSpec for any registered calculation module."""
    registry = get_module_registry()
    spec = registry.get(module_id)
    canonical_id = spec.module_id if spec is not None else module_id.strip()

    if spec is not None and spec.maturity in (ModuleMaturity.COMING_SOON, ModuleMaturity.UNAVAILABLE):
        return DiagramSpec(
            diagram_id=canonical_id,
            module_id=canonical_id,
            title=spec.title,
            is_empty_state=True,
            empty_message="Schematic diagram unavailable until calculation module is active.",
            has_geometry=False,
            has_engine_result=False,
            is_stale=False,
        )

    builder = _BUILDER_MAP.get(canonical_id)
    if builder is None:
        return DiagramSpec(
            diagram_id=canonical_id,
            module_id=canonical_id,
            title=spec.title if spec else canonical_id,
            is_empty_state=True,
            empty_message="Schematic diagram unavailable until calculation module is active.",
            has_geometry=False,
            has_engine_result=False,
            is_stale=False,
        )

    return builder(canonical_id, draft_inputs, result, is_stale)
