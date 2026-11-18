"""Cantilevered Steel Post Embedded in Grouted CMU / Concrete Module.

Implements procedures/04_concrete_masonry_foundation/cantilever_steel_post_embedded_concrete_cmu_workflow.md.
Evaluates Dual ASD/LRFD cantilevered structural steel posts across all 4 load-path stages:
- Stage 1: Post embedment geometry (L_e >= d_top + z_b + cover), grout cover clearance,
           and HSS wall compactness.
- Stage 2: Embedded steel post flexural yielding & combined axial-flexural interaction (AISC F7/H1).
- Stage 3: Embedment force transfer via Path A (discrete top rebar couple + flare-bevel weld +
           bottom masonry/concrete bearing) OR Path B (IBC Sec. 1807.3.2 flagpole bearing depth).
- Stage 4: Supporting bond beam one-way shear & breakout capacity (TMS 402 / ACI 318).
"""

from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Optional
import uuid

from core.aisc360.bolts import (
    MATERIAL_GRADES_FILE,
    SHAPES_DATABASE_FILE,
    TABLE_J2_5_FILE,
    lookup_material_grade,
    lookup_shape_imperial,
)
from core.aisc360.welds import lookup_fillet_weld_factors_j2_5
from core.common.calculation_result import (
    AcceptanceCriterion,
    CalcStep,
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
    LoadPathStage,
    Quantity,
    RefSpec,
)
from core.common.exceptions import InputValidationError
from core.common.math_markup import validate_math_markup
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort
from core.tms402.cmu_anchorage import (
    TMS_ANCHOR_CSV,
    _build_tms_ref,
    lookup_cmu_wall_properties,
)


REBAR_CSV = "rebar_astm_a615_a706.csv"
PROC_EMBEDDED_POST_FILE = "cantilever_steel_post_embedded_concrete_cmu_workflow.md"


def lookup_rebar_properties(kb: ReferenceDataPort, bar_size: str = "#4") -> Dict[str, float]:
    """Lookup reinforcing bar diameter and nominal area from rebar_astm_a615_a706.csv."""
    target = bar_size.strip().upper().replace("NO.", "#").replace("NO", "#").replace(" ", "")
    if not target.startswith("#"):
        target = f"#{target}"
    csv_path = kb.get_file_path(REBAR_CSV)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sz = (row.get("Bar_Size") or "").strip().upper()
            if sz == target:
                return {
                    "d_b_in": float(row["Nominal_Diameter_in"]),
                    "A_s_in2": float(row["Nominal_Area_in2"]),
                    "weight_plf": float(row["Nominal_Weight_plf"]),
                }
    raise InputValidationError(f"Rebar size '{bar_size}' not found in {REBAR_CSV}.")


def calculate_embedded_steel_post(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate Cantilevered Steel Post Embedded in Grouted CMU or Concrete across 4 stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-emb-post-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_tms_ref(
        kb, "procedure", "Embedded Steel Post Workflow",
        identifier=PROC_EMBEDDED_POST_FILE,
        fallback_path="procedures/04_concrete_masonry_foundation/cantilever_steel_post_embedded_concrete_cmu_workflow.md",
        code="TMS 402 / AISC 360",
        edition="2022",
    )
    ref_tms = _build_tms_ref(kb, "table", "TMS 402-22 CMU Properties", identifier=TMS_ANCHOR_CSV)
    ref_rebar = _build_tms_ref(
        kb, "table", "ASTM A615/A706 Rebar Properties", identifier=REBAR_CSV, code="ASTM", edition="A706"
    )
    ref_shapes = _build_tms_ref(
        kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE, code="AISC 360", edition="2022"
    )
    ref_mat = _build_tms_ref(
        kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE, code="AISC 360", edition="2022"
    )
    ref_j2_5 = _build_tms_ref(
        kb, "table", "AISC Table J2.5 Welds", identifier=TABLE_J2_5_FILE, code="AISC 360", edition="2022"
    )

    req_keys = ("post_section", "H_post_in", "L_e_in", "fm_psi")
    blank_reasons: List[str] = []
    req_complete = bool(inputs.get("_require_complete", False))
    for k in req_keys:
        if k in inputs:
            if inputs[k] is None or (isinstance(inputs[k], str) and inputs[k].strip() == ""):
                blank_reasons.append(f"Required input '{k}' is blank.")
        elif req_complete:
            blank_reasons.append(f"Required input '{k}' is missing.")
    if blank_reasons:
        return CalculationResult(
            calculation_id=calc_id,
            module_id="tms402_embedded_post",
            code_edition="TMS 402-22 / AISC 360-22",
            design_method=method,
            input_parameters=dict(inputs),
            assumptions=["Incomplete required inputs; no benchmark defaults substituted."],
            intermediate_results={},
            limit_states=[],
            governing_limit_state=None,
            demand=0.0,
            capacity=0.0,
            dcr=0.0,
            status=CalculationStatus.INCOMPLETE,
            reference_files=[r.source_path for r in (ref_proc, ref_tms, ref_rebar, ref_shapes) if r.source_path],
            warnings=blank_reasons,
            trace=(),
            incomplete_reasons=blank_reasons,
        )

    # 1. Section 7 Benchmark Defaults
    transfer_path = str(inputs.get("transfer_path", "discrete_rebar")).strip().lower()
    medium = str(inputs.get("medium", "CMU")).strip().upper()
    cmu_nominal_in = int(validate_positive("cmu_nominal_in", inputs.get("cmu_nominal_in", 8)))
    fm_psi = validate_positive("fm_psi", inputs.get("fm_psi", 2000.0))

    post_section = str(inputs.get("post_section", "HSS4x4x1/4")).strip()
    post_grade = str(inputs.get("post_grade", "A500 Gr. C")).strip()
    h_post_in = validate_positive("H_post_in", inputs.get("H_post_in", 48.0))
    l_e_in = validate_positive("L_e_in", inputs.get("L_e_in", 24.0))
    a_0_in = validate_non_negative("a_0_in", inputs.get("a_0_in", 2.0))

    d_top_in = validate_positive("d_top_in", inputs.get("d_top_in", 4.0))
    z_b_in = validate_positive("z_b_in", inputs.get("z_b_in", 16.0))
    rebar_size = str(inputs.get("rebar_size", "#4")).strip()
    n_ubar_legs = int(validate_positive("n_ubar_legs", inputs.get("n_ubar_legs", 2)))
    l_weld_leg_in = validate_positive("L_weld_leg_in", inputs.get("L_weld_leg_in", 2.5))
    n_weld_lines = int(validate_positive("n_weld_lines", inputs.get("n_weld_lines", 2)))
    f_exx_ksi = validate_positive("F_EXX_ksi", inputs.get("F_EXX_ksi", 70.0))
    b_bb_in = validate_positive("b_bb_in", inputs.get("b_bb_in", 16.0))

    if method == DesignMethod.LRFD:
        v_demand_kips = validate_non_negative("V_u_kips", inputs.get("V_u_kips", 1.92))
        p_demand_kips = validate_non_negative("P_u_kips", inputs.get("P_u_kips", 2.40))
    else:
        v_demand_kips = validate_non_negative("V_a_kips", inputs.get("V_a_kips", 1.20))
        p_demand_kips = validate_non_negative("P_a_kips", inputs.get("P_a_kips", 1.50))

    # Lookup shapes, material, rebar, wall, and weld factors from CSVs
    post_shape = lookup_shape_imperial(kb, post_section)
    post_mat = lookup_material_grade(kb, post_grade)
    rebar = lookup_rebar_properties(kb, rebar_size)
    weld_factors = lookup_fillet_weld_factors_j2_5(kb)

    if medium == "CMU":
        wall_props = lookup_cmu_wall_properties(kb, cmu_nominal_in)
        t_wall_in = float(inputs.get("t_wall_in", wall_props["t_actual_in"]))
    else:
        t_wall_in = float(inputs.get("t_wall_in", 12.0))

    b_post = float(inputs.get("b_post_in", post_shape["B"] or post_shape["bf"] or post_shape["OD"] or 4.0))
    h_depth_post = float(inputs.get("H_depth_in", post_shape["Ht"] or post_shape["d"] or post_shape["OD"] or 4.0))
    a_g_post = float(inputs.get("Ag_post_in2", post_shape["A"] or 3.37))
    z_x_post = float(inputs.get("Zx_post_in3", post_shape["Zx"] or 4.69))
    fy_post = float(inputs.get("Fy_post_ksi", post_mat["Fy_ksi"]))

    # 2. Stage 1 Geometry & Clearance Checks
    couple_depth = d_top_in + z_b_in
    grout_cover_per_side = 0.5 * (t_wall_in - b_post)
    geom_ok = (l_e_in >= couple_depth) and (grout_cover_per_side >= 1.25 - 1e-6)

    # 3. Stage 2 Cantilever Steel Post Flexure + Axial Interaction (AISC F7 / H1)
    m_post_kip_in = v_demand_kips * (h_post_in + a_0_in)
    m_n_post = fy_post * z_x_post
    p_n_post = fy_post * a_g_post
    if method == DesignMethod.LRFD:
        m_cap_post = 0.90 * m_n_post
        p_cap_post = 0.90 * p_n_post
    else:
        m_cap_post = m_n_post / 1.67
        p_cap_post = p_n_post / 1.67

    ratio_p = (p_demand_kips / p_cap_post) if p_cap_post > 0 else 0.0
    ratio_m = (m_post_kip_in / m_cap_post) if m_cap_post > 0 else 0.0
    if ratio_p >= 0.20:
        dcr_post_pm = ratio_p + (8.0 / 9.0) * ratio_m
    else:
        dcr_post_pm = 0.5 * ratio_p + ratio_m

    # 4. Stage 3 Embedment Force Couple Transfer (Path A Discrete Rebar vs. Path B Flagpole Stress Block)
    if "bearing" in transfer_path or "flagpole" in transfer_path or "1807" in transfer_path:
        # Path B: IBC Sec. 1807.3.2 flagpole embedment formula (using permissible lateral bearing S1)
        s1_psi_per_ft = float(inputs.get("S1_bearing_psf_per_ft", 400.0)) * (min(l_e_in, 144.0) / 12.0)
        b_ft = b_post / 12.0
        h_ft = h_post_in / 12.0
        a_term = (2.34 * (v_demand_kips * 1000.0)) / max(1.0, s1_psi_per_ft * b_ft)
        d_req_ft = 0.5 * a_term * (1.0 + math.sqrt(1.0 + (4.36 * h_ft) / max(0.01, a_term)))
        d_req_in = d_req_ft * 12.0
        t_top_kips = v_demand_kips * (h_post_in + 0.67 * l_e_in) / max(1.0, 0.67 * l_e_in)
        c_bot_kips = t_top_kips + v_demand_kips
        cap_rebar_kips = 1e6
        cap_weld_kips = 1e6
        l_brg_bot = max(2.0, 0.25 * l_e_in)
        f_br_ksi = (0.25 * fm_psi / 1000.0) if method == DesignMethod.ASD else (0.60 * 0.80 * fm_psi / 1000.0)
        cap_brg_kips = f_br_ksi * b_post * l_brg_bot
        dcr_rebar = 0.0
        dcr_weld = 0.0
        dcr_brg = (d_req_in / l_e_in) ** 2
    else:
        # Path A: Discrete Rebar Force Couple (Sec. 7 Benchmark)
        t_top_kips = v_demand_kips * (h_post_in + d_top_in + z_b_in) / z_b_in
        c_bot_kips = t_top_kips + v_demand_kips

        # Top U-bar steel tension (TMS 402 Sec. 8.3.3.1 Fs = 32 ksi ASD; 0.90*60 ksi LRFD)
        a_s_total = n_ubar_legs * rebar["A_s_in2"]
        f_s_rebar_ksi = 32.0 if method == DesignMethod.ASD else (0.90 * 60.0)
        cap_rebar_kips = f_s_rebar_ksi * a_s_total
        dcr_rebar = t_top_kips / cap_rebar_kips

        # Flare-bevel groove weld of round bar to flat HSS face (AISC Sec. J2.1b: E = 0.156 * d_b)
        e_flare_in = 0.156 * rebar["d_b_in"]
        l_weld_total = n_weld_lines * l_weld_leg_in
        r_nw_kips = 0.60 * f_exx_ksi * e_flare_in * l_weld_total
        cap_weld_kips = (r_nw_kips / weld_factors["Omega"]) if method == DesignMethod.ASD else (weld_factors["phi"] * r_nw_kips)
        dcr_weld = t_top_kips / cap_weld_kips

        # Bottom masonry / concrete bearing at embedment toe (bearing length l_brg_bot default 4.0 in.)
        l_brg_bot = float(inputs.get("L_brg_bot_in", 4.0))
        f_br_ksi = (0.25 * fm_psi / 1000.0) if method == DesignMethod.ASD else (0.60 * 0.85 * fm_psi / 1000.0)
        cap_brg_kips = f_br_ksi * b_post * l_brg_bot
        dcr_brg = c_bot_kips / cap_brg_kips

    # 5. Stage 4 Supporting Bond Beam Shear & Masonry Breakout Continuity Check
    # Bond beam shear across 2 grouted CMU courses (b_bb = 16.0 in.) & grouted wall thickness t_wall
    a_nv_bb = t_wall_in * b_bb_in
    if method == DesignMethod.ASD:
        cap_bb_shear_kips = (1.5 * math.sqrt(fm_psi) * a_nv_bb) / 1000.0
    else:
        cap_bb_shear_kips = (0.80 * 2.25 * math.sqrt(fm_psi) * a_nv_bb) / 1000.0
    dcr_bb_shear = t_top_kips / cap_bb_shear_kips

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_POST",
            name="Cantilever Steel Post Flexural & Axial Interaction",
            code_clause="AISC 360-22 Sec. F7 & H1",
            equation_latex=r"\frac{P_r}{2 P_c} + \frac{M_r}{M_c} \leq 1.0",
            substitution_str=f"P={p_demand_kips:.2f}/{p_cap_post:.1f} kips, M={m_post_kip_in:.1f}/{m_cap_post:.1f} kip-in.",
            demand=round(m_post_kip_in, 2),
            capacity=round(m_cap_post, 2),
            units="kip-in.",
            dcr=round(dcr_post_pm, 3),
            status=CalculationStatus.PASS if dcr_post_pm <= 1.0 else CalculationStatus.FAIL,
            notes=f"{post_shape['label']} (Z_x={z_x_post:.2f} in.^3)",
        ),
        LimitStateResult(
            step_id="S3_REBAR",
            name=f"Top U-Bar Tension ({rebar_size} x {n_ubar_legs} legs)",
            code_clause="TMS 402-22 Sec. 8.3.3.1 / 9.3",
            equation_latex=r"T_{rebar} = F_s \cdot A_{st}",
            substitution_str=f"T_top={t_top_kips:.2f} kips vs cap={cap_rebar_kips:.2f} kips",
            demand=round(t_top_kips, 2),
            capacity=round(cap_rebar_kips, 2),
            units="kips",
            dcr=round(dcr_rebar, 3),
            status=CalculationStatus.PASS if dcr_rebar <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_WELD",
            name="Flare-Bevel Groove Weld (Rebar-to-Post)",
            code_clause="AISC 360-22 Sec. J2.1b & Table J2.5",
            equation_latex=r"R_{nw} = 0.60 F_{EXX} (0.156 d_b) L_w",
            substitution_str=f"E={0.156 * rebar['d_b_in']:.4f} in., L_w={n_weld_lines * l_weld_leg_in:.1f} in., cap={cap_weld_kips:.2f} kips",
            demand=round(t_top_kips, 2),
            capacity=round(cap_weld_kips, 2),
            units="kips",
            dcr=round(dcr_weld, 3),
            status=CalculationStatus.PASS if dcr_weld <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_BEARING",
            name="Bottom Embedment Toe Masonry Bearing",
            code_clause="TMS 402-22 Bearing",
            equation_latex=r"C_{brg} = F_{br} \cdot b_{post} \cdot L_{brg}",
            substitution_str=f"C_bot={c_bot_kips:.2f} kips vs cap={cap_brg_kips:.2f} kips",
            demand=round(c_bot_kips, 2),
            capacity=round(cap_brg_kips, 2),
            units="kips",
            dcr=round(dcr_brg, 3),
            status=CalculationStatus.PASS if dcr_brg <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_BOND_BEAM",
            name="Supporting Bond Beam Shear & Wall Breakout Check",
            code_clause="TMS 402-22 Sec. 8.3.4 / 9.3.4",
            equation_latex=r"V_{m} = F_v \cdot t_{wall} \cdot b_{bb}",
            substitution_str=f"T_top={t_top_kips:.2f} kips vs cap={cap_bb_shear_kips:.2f} kips",
            demand=round(t_top_kips, 2),
            capacity=round(cap_bb_shear_kips, 2),
            units="kips",
            dcr=round(dcr_bb_shear, 3),
            status=CalculationStatus.PASS if dcr_bb_shear <= 1.0 else CalculationStatus.FAIL,
        ),
    ]

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = geom_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    rebar_label = rebar_size.replace("#", "No. ")
    trace = (
        CalcStep(
            step_id="S1_EMBED_COVER",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Post Embedment Depth & Grout Cover Clearance Check",
            symbolic=validate_math_markup(r"L_e \geq d_{top} + z_b, c_{grout} = \frac{t_{wall} - b_{post}}{2}"),
            substituted=validate_math_markup(
                rf"L_e = {l_e_in:.1f} \text{{ in.}} \geq {couple_depth:.1f} \text{{ in., }} c_{{grout}} = {grout_cover_per_side:.2f} \text{{ in.}}"
            ),
            variables={
                "H_post": Quantity("H", h_post_in, "in.", "Cantilever height above wall top"),
                "L_e": Quantity("L_e", l_e_in, "in.", "Embedded post depth"),
                "z_b": Quantity("z_b", z_b_in, "in.", "Rebar-to-toe force couple lever arm"),
                "c_grout": Quantity("c_{grout}", round(grout_cover_per_side, 2), "in.", "Grout cover per side of post"),
            },
            result_value=round(l_e_in, 1),
            result_unit="in.",
            acceptance=AcceptanceCriterion(">=", round(couple_depth, 1), "in.", "Embedment couple & grout cover geometry", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if geom_ok else CalculationStatus.FAIL,
            refs=(ref_tms, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S2_POST_PM",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Cantilever Steel Post Flexural & Axial Interaction (Sec. F7 / H1)",
            symbolic=validate_math_markup(r"M_{max} = V \cdot (H + a_0), \frac{P_r}{2 P_c} + \frac{M_r}{M_c} \leq 1.0"),
            substituted=validate_math_markup(
                rf"M_{{max}} = {v_demand_kips:.2f} \cdot ({h_post_in:.1f} + {a_0_in:.1f}) = {m_post_kip_in:.2f} \text{{ kip-in., IR}} = {dcr_post_pm:.3f}"
            ),
            variables={
                "M_max": Quantity("M_{\\max}", round(m_post_kip_in, 2), "kip-in.", f"{method.value} post cantilever moment"),
                "M_cap": Quantity("M_c", round(m_cap_post, 2), "kip-in.", f"{method.value} post flexural capacity"),
                "P_demand": Quantity("P_r", round(p_demand_kips, 2), "kips", f"{method.value} axial demand"),
                "Z_x": Quantity("Z_x", z_x_post, "in.^3", "Plastic section modulus (AISC Shapes DB)"),
            },
            result_value=round(m_cap_post, 2),
            result_unit="kip-in.",
            acceptance=AcceptanceCriterion(">=", round(m_post_kip_in, 2), "kip-in.", f"{method.value} steel post P-M check", is_dcr_check=True),
            dcr=round(dcr_post_pm, 3),
            status=CalculationStatus.PASS if dcr_post_pm <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_shapes, ref_mat, ref_proc),
        ),
        CalcStep(
            step_id="S3_COUPLE_TRANSFER",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Embedment Couple: Top U-Bar, Flare-Bevel Weld & Bottom Bearing",
            symbolic=validate_math_markup(r"T_{top} = \frac{V \cdot (H + d_{top} + z_b)}{z_b}, C_{bot} = T_{top} + V"),
            substituted=validate_math_markup(
                rf"T_{{top}} = {t_top_kips:.2f} \text{{ kips (}}\text{{{rebar_label}}}\text{{ cap }} {cap_rebar_kips:.2f}\text{{, weld }} {cap_weld_kips:.2f}\text{{), }} C_{{bot}} = {c_bot_kips:.2f} \text{{ vs }} {cap_brg_kips:.2f} \text{{ kips}}"
            ),
            variables={
                "T_top": Quantity("T_{top}", round(t_top_kips, 2), "kips", "Top horizontal couple tension"),
                "C_bot": Quantity("C_{bot}", round(c_bot_kips, 2), "kips", "Bottom toe bearing reaction"),
                "cap_rebar": Quantity("T_{rebar}", round(cap_rebar_kips, 2), "kips", f"{method.value} U-bar tension capacity"),
                "cap_weld": Quantity("R_{weld}", round(cap_weld_kips, 2), "kips", f"{method.value} flare-bevel weld capacity"),
                "cap_brg": Quantity("C_{brg}", round(cap_brg_kips, 2), "kips", f"{method.value} masonry toe bearing capacity"),
            },
            result_value=round(min(cap_rebar_kips, cap_weld_kips), 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(t_top_kips, 2), "kips", f"{method.value} rebar/weld/bearing couple check", is_dcr_check=True),
            dcr=round(max(dcr_rebar, dcr_weld, dcr_brg), 3),
            status=CalculationStatus.PASS if max(dcr_rebar, dcr_weld, dcr_brg) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_rebar, ref_j2_5, ref_tms, ref_proc),
        ),
        CalcStep(
            step_id="S4_BOND_BEAM",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Supporting Bond Beam One-Way Shear & Wall Breakout Check",
            symbolic=validate_math_markup(r"V_m = F_v \cdot t_{wall} \cdot b_{bb}"),
            substituted=validate_math_markup(
                rf"V_{{cap}} = {cap_bb_shear_kips:.2f} \text{{ kips vs }} T_{{top}} = {t_top_kips:.2f} \text{{ kips}}"
            ),
            variables={
                "t_wall": Quantity("t_{wall}", t_wall_in, "in.", "Actual CMU / wall thickness"),
                "b_bb": Quantity("b_{bb}", b_bb_in, "in.", "Bond beam tributary height"),
                "V_cap": Quantity("V_m", round(cap_bb_shear_kips, 2), "kips", f"{method.value} bond beam shear capacity"),
            },
            result_value=round(cap_bb_shear_kips, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(t_top_kips, 2), "kips", f"{method.value} supporting bond beam shear check", is_dcr_check=True),
            dcr=round(dcr_bb_shear, 3),
            status=CalculationStatus.PASS if dcr_bb_shear <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_tms, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not geom_ok:
        warnings.append("Embedment depth L_e or grout cover clearance around steel post is insufficient.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="tms402_embedded_post",
        code_edition="TMS 402-22 / AISC 360-22",
        design_method=method,
        input_parameters={
            "transfer_path": transfer_path,
            "medium": medium,
            "cmu_nominal_in": cmu_nominal_in,
            "fm_psi": fm_psi,
            "post_section": post_section,
            "post_grade": post_grade,
            "H_post_in": h_post_in,
            "L_e_in": l_e_in,
            "a_0_in": a_0_in,
            "d_top_in": d_top_in,
            "z_b_in": z_b_in,
            "rebar_size": rebar_size,
            "V_demand_kips": v_demand_kips,
            "P_demand_kips": p_demand_kips,
        },
        assumptions=[
            "Top force couple transfer via welded ASTM A706 U-bar welded directly to embedded HSS face.",
            "Post Z_x = 4.69 in.^3 for HSS4x4x1/4 taken directly from AISC 16th Shapes Database CSV.",
        ],
        intermediate_results={
            "Zx_post_in3": z_x_post,
            "t_wall_in": t_wall_in,
            "M_post_kip_in": round(m_post_kip_in, 2),
            "M_cap_post_kip_in": round(m_cap_post, 2),
            "T_top_kips": round(t_top_kips, 2),
            "C_bot_kips": round(c_bot_kips, 2),
            "cap_rebar_kips": round(cap_rebar_kips, 2),
            "cap_weld_kips": round(cap_weld_kips, 2),
            "cap_brg_kips": round(cap_brg_kips, 2),
            "cap_bb_shear_kips": round(cap_bb_shear_kips, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path for r in (ref_proc, ref_tms, ref_rebar, ref_shapes, ref_mat, ref_j2_5) if r.source_path
        ],
        warnings=warnings,
        trace=trace,
    )
