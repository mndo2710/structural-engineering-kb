"""ANSI/AISC 360-22 & Manual Part 9/10 Single/Double Angle Shear Connection Module.

Implements procedures/03_steel_design/steel_single_double_angle_shear_aisc_workflow.md.
Evaluates Dual ASD/LRFD single-angle and double-angle shear connections across:
- Stage 1: Bolt edge/spacing detailing, angle leg rotational ductility (t_a <= 5/8 in. & db/2+1/16),
           and coped beam geometric limits (c <= 2d, dc <= d/2).
- Stage 2: Beam-side bolts (single/double shear) & support-side eccentric ICOR bolts.
- Stage 3: Angle leg shear yielding/rupture, block shear, and bolt bearing on angle/beam web.
- Stage 4: Coped beam web flexural local buckling & coped block shear (Manual Part 9)
           plus supporting girder web bearing check.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import uuid

from core.aisc360.bolts import (
    MATERIAL_GRADES_FILE,
    PART7_ICOR_FILE,
    PART10_SHEAR_FILE,
    SHAPES_DATABASE_FILE,
    TABLE_J3_2_FILE,
    TABLE_J3_3_FILE,
    _build_aisc_ref,
    _check_blank_inputs,
    _make_incomplete_result,
    _validated_markup,
    lookup_bolt_properties,
    lookup_hole_and_edge_limits,
    lookup_icor_c_coefficient,
    lookup_material_grade,
    lookup_shape_imperial,
)
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
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort


PROC_ANGLES_FILE = "steel_single_double_angle_shear_aisc_workflow.md"


def calculate_steel_angle_connection(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 & Part 10 Single or Double Angle Shear Connection."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-angle-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "Single & Double Angle Shear Workflow",
        identifier=PROC_ANGLES_FILE,
        fallback_path="procedures/03_steel_design/steel_single_double_angle_shear_aisc_workflow.md",
    )
    ref_part10 = _build_aisc_ref(kb, "table", "AISC Manual Part 10", identifier=PART10_SHEAR_FILE)
    ref_part7 = _build_aisc_ref(kb, "table", "AISC Manual Table 7-6 (ICOR)", identifier=PART7_ICOR_FILE)
    ref_j3_2 = _build_aisc_ref(kb, "table", "Table J3.2", identifier=TABLE_J3_2_FILE)
    ref_j3_3 = _build_aisc_ref(kb, "table", "Tables J3.3-J3.5", identifier=TABLE_J3_3_FILE)
    ref_shapes = _build_aisc_ref(kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)

    req_keys = ("angle_section", "beam_section", "support_section", "L_a_in", "n_bolts")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_angle_connection", "AISC 360-22 / Manual 16th Ed.", method, inputs, blank_reasons,
            [ref_proc, ref_part10, ref_part7, ref_shapes, ref_mat],
        )

    # 1. Section 7 Benchmark Defaults
    conn_type = str(inputs.get("connection_type", "Single Angle")).strip()
    is_double_angle = "double" in conn_type.lower() or "2l" in conn_type.lower()
    n_angles = 2 if is_double_angle else 1

    angle_section = str(inputs.get("angle_section", "L4x3x3/8")).strip()
    angle_grade = str(inputs.get("angle_grade", "A36")).strip()
    l_a = validate_positive("L_a_in", inputs.get("L_a_in", 5.5))

    beam_section = str(inputs.get("beam_section", "W12x14")).strip()
    beam_grade = str(inputs.get("beam_grade", "A992")).strip()
    support_section = str(inputs.get("support_section", "W18x35")).strip()
    support_grade = str(inputs.get("support_grade", "A992")).strip()

    n_bolts = int(validate_positive("n_bolts", inputs.get("n_bolts", 2)))
    d_b_in = validate_positive("d_b_in", inputs.get("d_b_in", 0.75))
    bolt_grade = str(inputs.get("bolt_grade", "A325")).strip()
    thread_cond = str(inputs.get("thread_condition", "N")).strip().upper()
    hole_type = str(inputs.get("hole_type", "STD")).strip().upper()
    s_in = validate_positive("s_in", inputs.get("s_in", 3.0))
    l_ev_in = validate_positive("L_ev_in", inputs.get("L_ev_in", 1.25))
    l_eh_in = validate_positive("L_eh_in", inputs.get("L_eh_in", 1.5))
    g_sup_in = validate_positive("g_sup_in", inputs.get("g_sup_in", 1.75))
    g_beam_in = validate_positive("g_beam_in", inputs.get("g_beam_in", 2.25))

    is_coped = bool(inputs.get("is_coped", True))
    c_cope = validate_non_negative("c_cope_in", inputs.get("c_cope_in", 4.0 if is_coped else 0.0))
    dc_cope = validate_non_negative("dc_cope_in", inputs.get("dc_cope_in", 1.5 if is_coped else 0.0))

    if method == DesignMethod.LRFD:
        v_demand = validate_non_negative("V_u_kips", inputs.get("V_u_kips", 18.0))
    else:
        v_demand = validate_non_negative("V_a_kips", inputs.get("V_a_kips", 12.0))

    # Lookup shapes and materials from CSVs
    angle_shape = lookup_shape_imperial(kb, angle_section)
    beam_shape = lookup_shape_imperial(kb, beam_section)
    sup_shape = lookup_shape_imperial(kb, support_section)

    angle_mat = lookup_material_grade(kb, angle_grade)
    beam_mat = lookup_material_grade(kb, beam_grade)
    sup_mat = lookup_material_grade(kb, support_grade)

    t_a = float(inputs.get("t_a_in", angle_shape["t"] or 0.375))
    fy_a = float(inputs.get("Fy_angle_ksi", angle_mat["Fy_ksi"]))
    fu_a = float(inputs.get("Fu_angle_ksi", angle_mat["Fu_ksi"]))

    d_beam = float(inputs.get("d_beam_in", beam_shape["d"] or 11.9))
    tw_beam = float(inputs.get("tw_beam_in", beam_shape["tw"] or 0.200))
    fy_b = float(inputs.get("Fy_beam_ksi", beam_mat["Fy_ksi"]))
    fu_b = float(inputs.get("Fu_beam_ksi", beam_mat["Fu_ksi"]))
    e_mod_beam = beam_mat["E_ksi"]
    bf_beam = float(inputs.get("bf_beam_in", beam_shape["bf"] or 3.97))
    tf_beam = float(inputs.get("tf_beam_in", beam_shape["tf"] or 0.225))

    tw_sup = float(inputs.get("tw_support_in", sup_shape["tw"] or sup_shape["tdes"] or 0.300))
    fu_sup = float(inputs.get("Fu_support_ksi", sup_mat["Fu_ksi"]))

    bolt_props = lookup_bolt_properties(kb, bolt_grade, thread_cond, d_b_in, fu_rod_ksi=fu_a)
    hole_props = lookup_hole_and_edge_limits(kb, d_b_in, hole_type)
    a_b = bolt_props["A_b_in2"]
    f_nv = bolt_props["F_nv_ksi"]
    phi_bolt = bolt_props["phi"]
    omega_bolt = bolt_props["Omega"]
    d_h = hole_props["d_h_in"]
    d_h_eff = hole_props["d_h_eff_in"]

    # 2. Stage 1 Detailing, Ductility Thickness & Cope Limits
    t_a_max_duct = min(0.625, d_b_in / 2.0 + 0.0625)
    duct_ok = t_a <= t_a_max_duct + 1e-6
    edge_spacing_ok = (l_ev_in >= hole_props["le_min_in"] - 1e-6) and (l_eh_in >= hole_props["le_min_in"] - 1e-6) and (s_in >= hole_props["s_min_in"] - 1e-6)
    cope_geom_ok = (not is_coped) or (c_cope <= 2.0 * d_beam and dc_cope <= 0.5 * d_beam)
    stage1_ok = duct_ok and edge_spacing_ok and cope_geom_ok

    # 3. Stage 2 Primary Force Transfer: Beam-Side & Support-Side Bolt Groups (Part 10)
    r_nv_single = f_nv * a_b
    if is_double_angle:
        # Double shear on beam web; concentric on support legs (2 vertical rows)
        r_n_beam_bolts = float(n_bolts) * 2.0 * r_nv_single
        r_n_sup_bolts = float(2 * n_bolts) * r_nv_single
        e_beam = 0.0
        e_sup = 0.0
        c_beam = float(n_bolts)
        c_sup = float(n_bolts)
    else:
        # Single angle Part 10 rules: e_beam = 0 if a_b <= 3.0 in.; e_sup = g_sup + tw/2
        e_beam = 0.0 if g_beam_in <= 3.0 + 1e-6 else g_beam_in
        e_sup = g_sup_in + 0.5 * tw_beam
        c_beam, _ = lookup_icor_c_coefficient(kb, n_bolts, e_beam, spacing_in=s_in)
        c_sup, _ = lookup_icor_c_coefficient(kb, n_bolts, e_sup, spacing_in=s_in)
        r_n_beam_bolts = c_beam * r_nv_single
        r_n_sup_bolts = c_sup * r_nv_single

    cap_beam_bolts = phi_bolt * r_n_beam_bolts if method == DesignMethod.LRFD else r_n_beam_bolts / omega_bolt
    cap_sup_bolts = phi_bolt * r_n_sup_bolts if method == DesignMethod.LRFD else r_n_sup_bolts / omega_bolt
    cap_bolts_gov = min(cap_beam_bolts, cap_sup_bolts)
    dcr_bolts = v_demand / cap_bolts_gov

    # 4. Stage 3 Connecting Angle(s): Shear Yield, Shear Rupture, Block Shear, Bearing
    # 3a. Angle Gross Shear Yielding
    r_n_ay = n_angles * 0.60 * fy_a * l_a * t_a
    cap_ay = 1.00 * r_n_ay if method == DesignMethod.LRFD else r_n_ay / 1.50
    dcr_ay = v_demand / cap_ay

    # 3b. Angle Net Shear Rupture
    a_nv_a = n_angles * max(0.0, l_a - n_bolts * d_h_eff) * t_a
    r_n_ar = 0.60 * fu_a * a_nv_a
    cap_ar = 0.75 * r_n_ar if method == DesignMethod.LRFD else r_n_ar / 2.00
    dcr_ar = v_demand / cap_ar

    # 3c. Angle Block Shear Rupture (Sec. J4.3)
    a_gv_a = n_angles * (l_a - l_ev_in) * t_a
    a_nv_bs_a = n_angles * max(0.0, (l_a - l_ev_in) - (n_bolts - 0.5) * d_h_eff) * t_a
    a_nt_bs_a = n_angles * max(0.0, l_eh_in - 0.5 * d_h_eff) * t_a
    r_n_bs_a = min(
        0.60 * fu_a * a_nv_bs_a + 1.0 * fu_a * a_nt_bs_a,
        0.60 * fy_a * a_gv_a + 1.0 * fu_a * a_nt_bs_a,
    )
    cap_bs_a = 0.75 * r_n_bs_a if method == DesignMethod.LRFD else r_n_bs_a / 2.00
    dcr_bs_a = v_demand / cap_bs_a

    # 3d. Bolt Bearing on Angles and Beam Web
    l_c_edge = max(0.0, l_ev_in - 0.5 * d_h)
    l_c_int = max(0.0, s_in - d_h)
    r_n_brg_angles = n_angles * (
        min(1.2 * l_c_edge * t_a * fu_a, 2.4 * d_b_in * t_a * fu_a)
        + max(0, n_bolts - 1) * min(1.2 * l_c_int * t_a * fu_a, 2.4 * d_b_in * t_a * fu_a)
    )
    r_n_brg_web = (
        min(1.2 * l_c_edge * tw_beam * fu_b, 2.4 * d_b_in * tw_beam * fu_b)
        + max(0, n_bolts - 1) * min(1.2 * l_c_int * tw_beam * fu_b, 2.4 * d_b_in * tw_beam * fu_b)
    )
    r_n_brg_gov = min(r_n_brg_angles, r_n_brg_web)
    cap_brg = 0.75 * r_n_brg_gov if method == DesignMethod.LRFD else r_n_brg_gov / 2.00
    dcr_brg = v_demand / cap_brg

    # 5. Stage 4 Supporting Beam Web & Coped Beam Local Web Buckling / Block Shear (Part 9)
    h_0 = max(0.5, d_beam - dc_cope)
    if is_coped and c_cope > 0.0 and dc_cope > 0.0:
        if "S_net_in3" in inputs:
            s_net_cope = float(inputs["S_net_in3"])
        elif bf_beam > 0.0 and tf_beam > 0.0 and h_0 > tf_beam:
            a_fl = bf_beam * tf_beam
            y_fl = 0.5 * tf_beam
            h_web_rem = h_0 - tf_beam
            a_wb = h_web_rem * tw_beam
            y_wb = tf_beam + 0.5 * h_web_rem
            y_cg = (a_fl * y_fl + a_wb * y_wb) / (a_fl + a_wb)
            i_net = (
                (bf_beam * (tf_beam ** 3) / 12.0 + a_fl * ((y_cg - y_fl) ** 2))
                + (tw_beam * (h_web_rem ** 3) / 12.0 + a_wb * ((y_wb - y_cg) ** 2))
            )
            s_net_cope = i_net / max(y_cg, h_0 - y_cg)
        else:
            s_net_cope = (tw_beam * (h_0 ** 2)) / 4.5
        f_factor = (2.0 * c_cope / d_beam) if (c_cope / d_beam <= 1.0) else (1.0 + c_cope / d_beam)
        k1_factor = (2.2 * (h_0 / c_cope) ** 1.65) if (c_cope / h_0 <= 1.0) else (2.2 * (h_0 / c_cope))
        f_cr = min(fy_b, (0.62 * math.pi * e_mod_beam * (tw_beam ** 2) / (c_cope * h_0)) * f_factor * k1_factor)
        m_n_cope = f_cr * s_net_cope
        e_cope = c_cope + g_beam_in
        r_n_cope_flex = m_n_cope / e_cope if e_cope > 0 else 1e6
        cap_cope_flex = 0.90 * r_n_cope_flex if method == DesignMethod.LRFD else r_n_cope_flex / 1.67

        # Coped beam web block shear (distance from end of beam to bolt = L_eh_beam ~ 1.5 in.)
        l_eh_beam = float(inputs.get("L_eh_beam_in", l_eh_in))
        l_ev_beam = float(inputs.get("L_ev_beam_in", l_ev_in))
        a_gv_w = (l_ev_beam + (n_bolts - 1) * s_in) * tw_beam
        a_nv_w = max(0.0, (l_ev_beam + (n_bolts - 1) * s_in) - (n_bolts - 0.5) * d_h_eff) * tw_beam
        a_nt_w = max(0.0, l_eh_beam - 0.5 * d_h_eff) * tw_beam
        r_n_cope_bs = min(
            0.60 * fu_b * a_nv_w + 1.0 * fu_b * a_nt_w,
            0.60 * fy_b * a_gv_w + 1.0 * fu_b * a_nt_w,
        )
        cap_cope_bs = 0.75 * r_n_cope_bs if method == DesignMethod.LRFD else r_n_cope_bs / 2.00
        cap_beam_end = min(cap_cope_flex, cap_cope_bs)
    else:
        s_net_cope = 0.0
        f_cr = fy_b
        cap_cope_flex = 1.00 * (0.60 * fy_b * d_beam * tw_beam) if method == DesignMethod.LRFD else (0.60 * fy_b * d_beam * tw_beam) / 1.50
        cap_cope_bs = cap_cope_flex
        cap_beam_end = cap_cope_flex
    dcr_beam_end = v_demand / cap_beam_end

    # Supporting girder web bearing check (n_bolts bolts on tw_sup)
    r_n_sup_brg = n_angles * n_bolts * 2.4 * d_b_in * tw_sup * fu_sup
    cap_sup_brg = 0.75 * r_n_sup_brg if method == DesignMethod.LRFD else r_n_sup_brg / 2.00
    dcr_sup_brg = v_demand / cap_sup_brg

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_BOLT",
            name=f"{conn_type} Bolt Group Shear (Beam/Support Legs)",
            code_clause="AISC Manual Part 10 & Sec. J3.6",
            equation_latex=r"R_n = \min(C_{beam},  C_{sup}) \cdot F_{nv} \cdot A_b",
            substitution_str=f"cap_beam={cap_beam_bolts:.2f}, cap_sup={cap_sup_bolts:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(cap_bolts_gov, 2),
            units="kips",
            dcr=round(dcr_bolts, 3),
            status=CalculationStatus.PASS if dcr_bolts <= 1.0 else CalculationStatus.FAIL,
            notes=f"e_sup={e_sup:.2f} in., C_sup={c_sup:.3f}",
        ),
        LimitStateResult(
            step_id="S3_ANGLE_SHEAR",
            name=f"{conn_type} Shear Yield / Rupture / Block Shear",
            code_clause="AISC 360-22 Sec. J4.2 & J4.3",
            equation_latex=r"R_{angle} = \min(R_{yield},  R_{rupture},  R_{bs})",
            substitution_str=f"min(yield={cap_ay:.2f}, rup={cap_ar:.2f}, bs={cap_bs_a:.2f}) kips",
            demand=round(v_demand, 2),
            capacity=round(min(cap_ay, cap_ar, cap_bs_a), 2),
            units="kips",
            dcr=round(max(dcr_ay, dcr_ar, dcr_bs_a), 3),
            status=CalculationStatus.PASS if max(dcr_ay, dcr_ar, dcr_bs_a) <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_BEARING",
            name="Bolt Bearing & Tear-Out (Angle & Beam Web)",
            code_clause="AISC 360-22 Sec. J3.10",
            equation_latex=r"R_{n,brg} = \min(R_{n,angle},  R_{n,web})",
            substitution_str=f"cap_brg={cap_brg:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(cap_brg, 2),
            units="kips",
            dcr=round(dcr_brg, 3),
            status=CalculationStatus.PASS if dcr_brg <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_COPE_SUP",
            name="Coped Beam Web Buckling / Block Shear & Support Bearing",
            code_clause="AISC Manual Part 9 / Sec. J3.10",
            equation_latex=r"F_{cr} = \frac{0.62 \pi E t_w^2}{c h_0} f k_1" if is_coped else r"V_{web} = 0.60 F_y d t_w",
            substitution_str=f"cap_beam_end={cap_beam_end:.2f}, cap_sup={cap_sup_brg:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(min(cap_beam_end, cap_sup_brg), 2),
            units="kips",
            dcr=round(max(dcr_beam_end, dcr_sup_brg), 3),
            status=CalculationStatus.PASS if max(dcr_beam_end, dcr_sup_brg) <= 1.0 else CalculationStatus.FAIL,
            notes=f"F_cr={f_cr:.2f} ksi, h0={h_0:.2f} in." if is_coped else "Uncoped beam web",
        ),
    ]

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = stage1_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    trace = (
        CalcStep(
            step_id="S1_ANGLE_LIMITS",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Angle Ductility Thickness, Detailing & Cope Geometry Checks",
            symbolic=_validated_markup(r"t_a \leq \min\left(0.625,  \frac{d_b}{2} + 0.0625\right)"),
            substituted=_validated_markup(
                rf"t_a = {t_a:.3f} \text{{ in.}} \leq {t_a_max_duct:.4f} \text{{ in., }} c = {c_cope:.2f} \text{{ in., }} d_c = {dc_cope:.2f} \text{{ in.}}"
            ),
            variables={
                "t_a": Quantity("t_a", t_a, "in.", "Angle leg thickness"),
                "t_a_max": Quantity("t_{a,\\max}", round(t_a_max_duct, 4), "in.", "Max angle ductility thickness"),
                "c": Quantity("c", c_cope, "in.", "Cope length"),
                "d_c": Quantity("d_c", dc_cope, "in.", "Cope depth"),
            },
            result_value=round(t_a, 3),
            result_unit="in.",
            acceptance=AcceptanceCriterion("<=", round(t_a_max_duct, 4), "in.", "Part 10 angle ductility & detailing check", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if stage1_ok else CalculationStatus.FAIL,
            refs=(ref_part10, ref_j3_3, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S2_BOLT_LEGS",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title=f"{conn_type} Beam-Side & Support-Side Bolt Shear Capacity",
            symbolic=_validated_markup(
                r"\phi R_n = \min\left(\phi R_{n,beam},  \phi R_{n,sup}\right)"
                if method == DesignMethod.LRFD
                else r"\frac{R_n}{\Omega} = \min\left(\frac{R_{n,beam}}{\Omega},  \frac{R_{n,sup}}{\Omega}\right)"
            ),
            substituted=_validated_markup(
                rf"\min({cap_beam_bolts:.2f}, {cap_sup_bolts:.2f}) = {cap_bolts_gov:.2f} \text{{ kips}}"
            ),
            variables={
                "e_sup": Quantity("e_{sup}", round(e_sup, 2), "in.", "Support leg eccentricity (Part 10)"),
                "C_sup": Quantity("C_{sup}", round(c_sup, 3), "", "Support leg ICOR / active bolts"),
                "C_beam": Quantity("C_{beam}", round(c_beam, 3), "", "Beam leg active bolt coefficient"),
                "R_bolts": Quantity("R_{bolts}", round(cap_bolts_gov, 2), "kips", f"{method.value} governing bolt capacity"),
            },
            result_value=round(cap_bolts_gov, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} angle bolt shear check", is_dcr_check=True),
            dcr=round(dcr_bolts, 3),
            status=CalculationStatus.PASS if dcr_bolts <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_part7, ref_part10, ref_j3_2, ref_proc),
        ),
        CalcStep(
            step_id="S3_ANGLE_STEEL",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Angle Shear Yield/Rupture, Block Shear & Bolt Bearing",
            symbolic=_validated_markup(r"R_{gov,S3} = \min\left(R_{yield},  R_{rupture},  R_{bs},  R_{brg}\right)"),
            substituted=_validated_markup(
                rf"\min({cap_ay:.2f}, {cap_ar:.2f}, {cap_bs_a:.2f}, {cap_brg:.2f}) = {min(cap_ay, cap_ar, cap_bs_a, cap_brg):.2f} \text{{ kips}}"
            ),
            variables={
                "cap_yield": Quantity("R_{ay}", round(cap_ay, 2), "kips", "Angle gross shear yield capacity"),
                "cap_rup": Quantity("R_{ar}", round(cap_ar, 2), "kips", "Angle net shear rupture capacity"),
                "cap_bs": Quantity("R_{bs}", round(cap_bs_a, 2), "kips", "Angle block shear capacity"),
                "cap_brg": Quantity("R_{brg}", round(cap_brg, 2), "kips", "Governing bolt bearing capacity"),
            },
            result_value=round(min(cap_ay, cap_ar, cap_bs_a, cap_brg), 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} angle/bearing strength", is_dcr_check=True),
            dcr=round(max(dcr_ay, dcr_ar, dcr_bs_a, dcr_brg), 3),
            status=CalculationStatus.PASS if max(dcr_ay, dcr_ar, dcr_bs_a, dcr_brg) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, ref_part10, ref_proc),
        ),
        CalcStep(
            step_id="S4_COPED_BEAM",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Coped Beam Web Local Buckling/Block Shear & Support Check",
            symbolic=_validated_markup(
                r"F_{cr} = \min\left(F_y,  \frac{0.62 \pi E t_w^2}{c h_0} f k_1\right)"
                if is_coped
                else r"V_{web} = 0.60 F_y d t_w"
            ),
            substituted=_validated_markup(
                rf"cap_{{beam}} = {cap_beam_end:.2f} \text{{ kips, }} cap_{{sup}} = {cap_sup_brg:.2f} \text{{ kips}}"
            ),
            variables={
                "h_0": Quantity("h_0", round(h_0, 2), "in.", "Reduced beam web height at cope"),
                "F_cr": Quantity("F_{cr}", round(f_cr, 2), "ksi", "Coped web local buckling critical stress"),
                "cap_cope_flex": Quantity("V_{cope}", round(cap_cope_flex, 2), "kips", "Coped flexural buckling shear capacity"),
                "cap_cope_bs": Quantity("R_{bs,web}", round(cap_cope_bs, 2), "kips", "Beam web coped block shear capacity"),
            },
            result_value=round(min(cap_beam_end, cap_sup_brg), 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} coped beam & support check", is_dcr_check=True),
            dcr=round(max(dcr_beam_end, dcr_sup_brg), 3),
            status=CalculationStatus.PASS if max(dcr_beam_end, dcr_sup_brg) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_shapes, ref_mat, ref_part10, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not stage1_ok:
        warnings.append("Detailing / ductility / cope geometry check failed in Stage 1.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_angle_connection",
        code_edition="AISC 360-22 / Manual 16th Ed.",
        design_method=method,
        input_parameters={
            "connection_type": conn_type,
            "angle_section": angle_section,
            "beam_section": beam_section,
            "support_section": support_section,
            "L_a_in": l_a,
            "n_bolts": n_bolts,
            "d_b_in": d_b_in,
            "is_coped": is_coped,
            "c_cope_in": c_cope,
            "dc_cope_in": dc_cope,
            "V_demand_kips": v_demand,
        },
        assumptions=[
            f"Evaluated as {conn_type} ({n_angles} angle(s)) per AISC Manual Part 10.",
            "Coped beam web local buckling and block shear evaluated per AISC Manual Part 9." if is_coped else "Uncoped beam section.",
        ],
        intermediate_results={
            "is_double_angle": is_double_angle,
            "t_a_in": t_a,
            "h_0_in": round(h_0, 2),
            "F_cr_ksi": round(f_cr, 2),
            "e_sup_in": round(e_sup, 2),
            "cap_bolts_kips": round(cap_bolts_gov, 2),
            "cap_cope_flex_kips": round(cap_cope_flex, 2),
            "cap_cope_bs_kips": round(cap_cope_bs, 2),
            "cap_angle_bs_kips": round(cap_bs_a, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path
            for r in (ref_proc, ref_part10, ref_part7, ref_j3_2, ref_j3_3, ref_shapes, ref_mat)
            if r.source_path
        ],
        warnings=warnings,
        trace=trace,
    )
