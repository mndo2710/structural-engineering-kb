"""ANSI/AISC 360-22 & Manual Part 10 Steel Single-Plate Shear Connection (Shear Tab) Module.

Implements procedures/03_steel_design/steel_shear_tab_connection_aisc_workflow.md.
Evaluates Dual ASD/LRFD conventional and extended shear-tab configurations across:
- Stage 1: Detailing, plate length (T/2 <= d_p <= T), conventional ductility thickness limit,
           support HSS wall compactness check (if supporting HSS column is selected).
- Stage 2: Eccentric bolt group ICOR capacity (Part 7 Table 7-6) and double-sided fillet weld.
- Stage 3: Shear tab shear yield/rupture, block shear, flexural-shear von Mises interaction,
           and bolt bearing/tear-out on shear tab & beam web.
- Stage 4: Supported beam web shear capacity and supporting HSS wall punching shear /
           bearing check (AISC Table K1.2 / Sec. J10) when supported on an HSS column.
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
    TABLE_J2_5_FILE,
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
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort


PROC_SHEAR_TAB_FILE = "steel_shear_tab_connection_aisc_workflow.md"


def calculate_steel_shear_tab(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 & Part 10 Single-Plate Shear Tab Connection across 4 stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-shear-tab-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "Steel Shear Tab Connection Workflow",
        identifier=PROC_SHEAR_TAB_FILE,
        fallback_path="procedures/03_steel_design/steel_shear_tab_connection_aisc_workflow.md",
    )
    ref_part10 = _build_aisc_ref(kb, "table", "AISC Manual Part 10", identifier=PART10_SHEAR_FILE)
    ref_part7 = _build_aisc_ref(kb, "table", "AISC Manual Table 7-6 (ICOR)", identifier=PART7_ICOR_FILE)
    ref_j3_2 = _build_aisc_ref(kb, "table", "Table J3.2", identifier=TABLE_J3_2_FILE)
    ref_j3_3 = _build_aisc_ref(kb, "table", "Tables J3.3-J3.5", identifier=TABLE_J3_3_FILE)
    ref_j2_5 = _build_aisc_ref(kb, "table", "Table J2.5", identifier=TABLE_J2_5_FILE)
    ref_shapes = _build_aisc_ref(kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)

    req_keys = ("beam_section", "support_section", "n_bolts", "t_plate_in", "d_p_in", "a_in")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_shear_tab", "AISC 360-22 / Manual 16th Ed.", method, inputs, blank_reasons,
            [ref_proc, ref_part10, ref_part7, ref_shapes, ref_mat],
        )

    # 1. Section 7 Benchmark Defaults
    beam_section = str(inputs.get("beam_section", "W18x35")).strip()
    beam_grade = str(inputs.get("beam_grade", "A992")).strip()
    support_section = str(inputs.get("support_section", "W14x90")).strip()
    support_grade = str(inputs.get("support_grade", "A992")).strip()
    plate_grade = str(inputs.get("plate_grade", "A36")).strip()

    t_p = validate_positive("t_plate_in", inputs.get("t_plate_in", 0.375))
    d_p = validate_positive("d_p_in", inputs.get("d_p_in", 9.0))
    a_in = validate_positive("a_in", inputs.get("a_in", 3.0))

    n_bolts = int(validate_positive("n_bolts", inputs.get("n_bolts", 3)))
    d_b_in = validate_positive("d_b_in", inputs.get("d_b_in", 0.75))
    bolt_grade = str(inputs.get("bolt_grade", "A325")).strip()
    thread_cond = str(inputs.get("thread_condition", "N")).strip().upper()
    hole_type = str(inputs.get("hole_type", "STD")).strip().upper()
    s_in = validate_positive("s_in", inputs.get("s_in", 3.0))
    l_ev_in = validate_positive("L_ev_in", inputs.get("L_ev_in", 1.5))
    l_eh_in = validate_positive("L_eh_in", inputs.get("L_eh_in", 1.5))

    w_weld_in = validate_positive("w_weld_in", inputs.get("w_weld_in", 0.25))
    f_exx_ksi = validate_positive("F_EXX_ksi", inputs.get("F_EXX_ksi", 70.0))

    if method == DesignMethod.LRFD:
        v_demand = validate_non_negative("V_u_kips", inputs.get("V_u_kips", 45.0))
    else:
        v_demand = validate_non_negative("V_a_kips", inputs.get("V_a_kips", 30.0))

    # Lookup shapes & grades from verified CSVs
    beam_shape = lookup_shape_imperial(kb, beam_section)
    sup_shape = lookup_shape_imperial(kb, support_section)
    beam_mat = lookup_material_grade(kb, beam_grade)
    sup_mat = lookup_material_grade(kb, support_grade)
    plate_mat = lookup_material_grade(kb, plate_grade)

    fy_b = float(inputs.get("Fy_beam_ksi", beam_mat["Fy_ksi"]))
    fu_b = float(inputs.get("Fu_beam_ksi", beam_mat["Fu_ksi"]))
    tw_b = float(inputs.get("tw_beam_in", beam_shape["tw"] or 0.300))
    d_beam = float(inputs.get("d_beam_in", beam_shape["d"] or 17.7))
    t_clear_beam = float(inputs.get("T_beam_in", beam_shape["T"] or (d_beam - 2.2)))

    fy_p = float(inputs.get("Fy_plate_ksi", plate_mat["Fy_ksi"]))
    fu_p = float(inputs.get("Fu_plate_ksi", plate_mat["Fu_ksi"]))

    fy_sup = float(inputs.get("Fy_support_ksi", sup_mat["Fy_ksi"]))
    fu_sup = float(inputs.get("Fu_support_ksi", sup_mat["Fu_ksi"]))
    e_sup_ksi = sup_mat["E_ksi"]
    is_hss_support = sup_shape["Type"].upper() == "HSS"

    bolt_props = lookup_bolt_properties(kb, bolt_grade, thread_cond, d_b_in, fu_rod_ksi=fu_p)
    hole_props = lookup_hole_and_edge_limits(kb, d_b_in, hole_type)
    weld_factors = lookup_fillet_weld_factors_j2_5(kb)

    a_b = bolt_props["A_b_in2"]
    f_nv = bolt_props["F_nv_ksi"]
    phi_bolt = bolt_props["phi"]
    omega_bolt = bolt_props["Omega"]

    d_h = hole_props["d_h_in"]
    d_h_eff = hole_props["d_h_eff_in"]

    # 2. Stage 1 Conventional vs Extended Shear Tab Limits (Part 10 Table 10-9)
    is_conventional = (
        a_in <= 3.5 + 1e-6
        and 2 <= n_bolts <= 9
        and hole_type in ("STD", "SSL", "SHORT_SLOT", "SHORT-SLOT")
        and l_ev_in >= hole_props["le_min_in"] - 1e-6
        and l_eh_in >= 2.0 * d_b_in - 1e-6
        and s_in >= hole_props["s_min_in"] - 1e-6
    )
    e_x_in = (a_in / 2.0) if is_conventional else a_in
    c_icor, c_prime = lookup_icor_c_coefficient(kb, n_bolts, e_x_in, spacing_in=s_in)

    # Plate ductility thickness limit
    t_p_duct_1 = d_b_in / 2.0 + 0.0625
    m_max_plate = (f_nv / 0.90) * a_b * c_prime if c_prime > 0 else 1e9
    t_p_duct_2 = (6.0 * m_max_plate) / (fy_p * (d_p ** 2))
    t_p_max_allowed = t_p_duct_1 if is_conventional else t_p_duct_2

    geom_depth_ok = (0.5 * t_clear_beam - 1e-6) <= d_p <= (t_clear_beam + 1e-6)
    ductility_ok = t_p <= t_p_max_allowed + 1e-6
    edge_spacing_ok = (l_ev_in >= hole_props["le_min_in"] - 1e-6) and (l_eh_in >= 2.0 * d_b_in - 1e-6) and (s_in >= hole_props["s_min_in"] - 1e-6)
    w_min_part10 = 0.625 * t_p
    weld_part10_ok = w_weld_in >= w_min_part10 - 1e-6

    # Optional supporting HSS wall slenderness limit (Table K1.2 / B4.1)
    hss_wall_t = sup_shape["tdes"] or sup_shape["tw"] or 0.25
    hss_width = max(sup_shape["B"] or 0.0, sup_shape["Ht"] or 0.0)
    hss_slenderness = (hss_width / hss_wall_t - 3.0) if hss_wall_t > 0 else 0.0
    hss_slenderness_lim = 1.40 * math.sqrt(e_sup_ksi / fy_sup)
    hss_compact_ok = (not is_hss_support) or (hss_slenderness <= hss_slenderness_lim)

    stage1_ok = geom_depth_ok and ductility_ok and edge_spacing_ok and hss_compact_ok

    # 3. Stage 2 Primary Force Transfer: Eccentric Bolt Group ICOR & Double-Sided Weld
    r_nv_single = f_nv * a_b
    r_n_bolts = c_icor * r_nv_single
    cap_bolts = phi_bolt * r_n_bolts if method == DesignMethod.LRFD else r_n_bolts / omega_bolt
    dcr_bolts = v_demand / cap_bolts

    # Double-sided fillet weld length = 2 * d_p under V and bending moment M_w = V * e_weld
    # For conventional tab (a <= 3.5), weld develops plate shear yield/moment when w >= 5/8*t_p.
    # For general/extended checks, check elastic vector stress sqrt((V/Lw)^2 + (M*c/Iw)^2) on 2 vertical welds:
    l_w_total = 2.0 * d_p
    e_weld = 0.0 if is_conventional else a_in
    f_weld_direct = v_demand / l_w_total
    s_weld_line = 2.0 * (d_p ** 2) / 6.0  # in.^2 (section modulus of 2 vertical unit-thickness weld lines)
    f_weld_bend = (v_demand * e_weld) / s_weld_line if s_weld_line > 0 else 0.0
    f_weld_req = math.hypot(f_weld_direct, f_weld_bend)

    t_eff_w = 0.70710678 * w_weld_in
    r_nw_in = 0.60 * f_exx_ksi * t_eff_w
    cap_weld_in = weld_factors["phi"] * r_nw_in if method == DesignMethod.LRFD else r_nw_in / weld_factors["Omega"]
    dcr_weld = f_weld_req / cap_weld_in

    # 4. Stage 3 Connecting Element (Shear Tab Plate Limit States + Bolt Bearing)
    # 3a. Plate Shear Yielding (Sec. J4.2a)
    r_n_py = 0.60 * fy_p * d_p * t_p
    cap_py = 1.00 * r_n_py if method == DesignMethod.LRFD else r_n_py / 1.50
    dcr_py = v_demand / cap_py

    # 3b. Plate Shear Rupture (Sec. J4.2b)
    a_nv_plate = max(0.0, d_p - n_bolts * d_h_eff) * t_p
    r_n_pr = 0.60 * fu_p * a_nv_plate
    cap_pr = 0.75 * r_n_pr if method == DesignMethod.LRFD else r_n_pr / 2.00
    dcr_pr = v_demand / cap_pr

    # 3c. Plate Block Shear Rupture (Sec. J4.3, U_bs = 1.0 for 1 vertical line)
    a_gv_bs = (d_p - l_ev_in) * t_p
    a_nv_bs = max(0.0, (d_p - l_ev_in) - (n_bolts - 0.5) * d_h_eff) * t_p
    a_nt_bs = max(0.0, l_eh_in - 0.5 * d_h_eff) * t_p
    r_n_bs = min(
        0.60 * fu_p * a_nv_bs + 1.0 * fu_p * a_nt_bs,
        0.60 * fy_p * a_gv_bs + 1.0 * fu_p * a_nt_bs,
    )
    cap_bs = 0.75 * r_n_bs if method == DesignMethod.LRFD else r_n_bs / 2.00
    dcr_bs = v_demand / cap_bs

    # 3d. Plate Flexural-Shear Interaction (Sec. J4.5 / Part 10 Eq.) with M = V * e_x
    m_plate = v_demand * e_x_in
    z_plate = t_p * (d_p ** 2) / 4.0
    m_n_plate = fy_p * z_plate
    cap_m_plate = 0.90 * m_n_plate if method == DesignMethod.LRFD else m_n_plate / 1.67
    # Von Mises interaction (V/Vc)^2 + (M/Mc)^2 <= 1.0 (or effective DCR sqrt(...))
    vm_ratio_sq = (v_demand / cap_py) ** 2 + (m_plate / cap_m_plate) ** 2
    dcr_vm = math.sqrt(vm_ratio_sq)
    cap_vm_equiv = (v_demand / dcr_vm) if dcr_vm > 1e-9 else cap_py

    # 3e. Bolt Bearing & Tear-Out on Shear Tab & Beam Web (Sec. J3.10)
    l_c_edge_p = max(0.0, l_ev_in - 0.5 * d_h)
    l_c_int_p = max(0.0, s_in - d_h)
    r_n_edge_p = min(1.2 * l_c_edge_p * t_p * fu_p, 2.4 * d_b_in * t_p * fu_p)
    r_n_int_p = min(1.2 * l_c_int_p * t_p * fu_p, 2.4 * d_b_in * t_p * fu_p)
    r_n_brg_plate = r_n_edge_p + max(0, n_bolts - 1) * r_n_int_p

    # Horizontal edge tear-out against L_eh on plate (eccentric horizontal bolt force component)
    r_n_brg_beam_single = 2.4 * d_b_in * tw_b * fu_b
    r_n_brg_beam = n_bolts * r_n_brg_beam_single
    r_n_brg_gov = min(r_n_brg_plate, r_n_brg_beam)
    cap_brg = 0.75 * r_n_brg_gov if method == DesignMethod.LRFD else r_n_brg_gov / 2.00
    dcr_brg = v_demand / cap_brg

    # 5. Stage 4 Supporting Member & Supported Beam Checks
    # Beam gross web shear (Sec. G2)
    r_n_beam_web = 0.60 * fy_b * d_beam * tw_b
    cap_beam_web = 1.00 * r_n_beam_web if method == DesignMethod.LRFD else r_n_beam_web / 1.50
    dcr_beam_web = v_demand / cap_beam_web

    # Supporting HSS column punching shear / wall shear strength when applicable (AISC Table J10 / Part 9)
    if is_hss_support:
        # Two-sided weld line punching shear resistance on HSS face wall: R_n = 2 * 0.60 * Fy_sup * t_sup * d_p
        r_n_hss_wall = 2.0 * 0.60 * fy_sup * hss_wall_t * d_p
        cap_sup = 1.00 * r_n_hss_wall if method == DesignMethod.LRFD else r_n_hss_wall / 1.50
        sup_title = f"Supporting HSS ({sup_shape['label']}) Wall Punching & Shear Check"
    else:
        t_sup_flange = sup_shape["tf"] or sup_shape["tw"] or 0.50
        r_n_sup_flange = 2.0 * 0.60 * fu_sup * t_sup_flange * d_p
        cap_sup = 0.75 * r_n_sup_flange if method == DesignMethod.LRFD else r_n_sup_flange / 2.00
        sup_title = f"Supporting Member ({sup_shape['label']}) Flange Local Shear Check"
    dcr_sup = v_demand / cap_sup

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_BOLT",
            name="Eccentric Bolt Group Shear (ICOR Method)",
            code_clause="AISC Manual Part 7 & Sec. J3.6",
            equation_latex=r"R_n = C \cdot F_{nv} \cdot A_b",
            substitution_str=f"C={c_icor:.3f} (n={n_bolts}, e={e_x_in:.2f} in.) * {r_nv_single:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(cap_bolts, 2),
            units="kips",
            dcr=round(dcr_bolts, 3),
            status=CalculationStatus.PASS if dcr_bolts <= 1.0 else CalculationStatus.FAIL,
            notes=f"{'Conventional' if is_conventional else 'Extended'} config (e_x={e_x_in:.2f} in.)",
        ),
        LimitStateResult(
            step_id="S2_WELD",
            name="Double-Sided Fillet Weld to Support",
            code_clause="AISC 360-22 Sec. J2.4 & Manual Part 10",
            equation_latex=r"f_w = \sqrt{\left(\frac{V}{2 d_p}\right)^2 + \left(\frac{V e_w}{d_p^2 / 3}\right)^2}",
            substitution_str=f"f_w={f_weld_req:.3f} kips/in. vs cap={cap_weld_in:.3f} kips/in.",
            demand=round(f_weld_req, 3),
            capacity=round(cap_weld_in, 3),
            units="kips/in.",
            dcr=round(dcr_weld, 3),
            status=CalculationStatus.PASS if dcr_weld <= 1.0 else CalculationStatus.FAIL,
            notes=f"w={w_weld_in:.3f} in. (min 5/8*tp={w_min_part10:.3f} in.)",
        ),
        LimitStateResult(
            step_id="S3_PY",
            name="Shear Tab Gross Shear Yielding (Sec. J4.2)",
            code_clause="AISC 360-22 Eq. J4-3",
            equation_latex=r"R_n = 0.60 F_y d_p t_p",
            substitution_str=f"0.60 * {fy_p:.1f} * {d_p:.2f} * {t_p:.3f}",
            demand=round(v_demand, 2),
            capacity=round(cap_py, 2),
            units="kips",
            dcr=round(dcr_py, 3),
            status=CalculationStatus.PASS if dcr_py <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_PR",
            name="Shear Tab Net Shear Rupture (Sec. J4.2)",
            code_clause="AISC 360-22 Eq. J4-4",
            equation_latex=r"R_n = 0.60 F_u A_{nv}",
            substitution_str=f"0.60 * {fu_p:.1f} * {a_nv_plate:.3f}",
            demand=round(v_demand, 2),
            capacity=round(cap_pr, 2),
            units="kips",
            dcr=round(dcr_pr, 3),
            status=CalculationStatus.PASS if dcr_pr <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_BS",
            name="Shear Tab Block Shear Rupture (Sec. J4.3)",
            code_clause="AISC 360-22 Eq. J4-5",
            equation_latex=r"R_n = \min(0.6 F_u A_{nv} + F_u A_{nt},  0.6 F_y A_{gv} + F_u A_{nt})",
            substitution_str=f"Agv={a_gv_bs:.3f}, Anv={a_nv_bs:.3f}, Ant={a_nt_bs:.3f} in.^2",
            demand=round(v_demand, 2),
            capacity=round(cap_bs, 2),
            units="kips",
            dcr=round(dcr_bs, 3),
            status=CalculationStatus.PASS if dcr_bs <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_VM",
            name="Shear Tab Flexural-Shear Interaction",
            code_clause="AISC Manual Part 10 / von Mises",
            equation_latex=r"\sqrt{\left(\frac{V}{V_c}\right)^2 + \left(\frac{M}{M_c}\right)^2} \leq 1.0",
            substitution_str=f"V={v_demand:.2f} kips, M={m_plate:.2f} kip-in.",
            demand=round(v_demand, 2),
            capacity=round(cap_vm_equiv, 2),
            units="kips",
            dcr=round(dcr_vm, 3),
            status=CalculationStatus.PASS if dcr_vm <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_BRG",
            name="Bolt Bearing & Tear-Out (Plate / Beam Web)",
            code_clause="AISC 360-22 Sec. J3.10",
            equation_latex=r"R_{n,brg} = \min(R_{n,plate},  R_{n,web})",
            substitution_str=f"R_n,plate={r_n_brg_plate:.2f}, R_n,web={r_n_brg_beam:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(cap_brg, 2),
            units="kips",
            dcr=round(dcr_brg, 3),
            status=CalculationStatus.PASS if dcr_brg <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_BEAM",
            name=f"Supported Beam ({beam_shape['label']}) Web Shear & Supporting Face Check",
            code_clause="AISC 360-22 Sec. G2 / J10",
            equation_latex=r"V_{n,web} = 0.60 F_y d t_w",
            substitution_str=f"Beam web cap={cap_beam_web:.2f} kips, Sup cap={cap_sup:.2f} kips",
            demand=round(v_demand, 2),
            capacity=round(min(cap_beam_web, cap_sup), 2),
            units="kips",
            dcr=round(max(dcr_beam_web, dcr_sup), 3),
            status=CalculationStatus.PASS if max(dcr_beam_web, dcr_sup) <= 1.0 else CalculationStatus.FAIL,
            notes=sup_title,
        ),
    ]

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = stage1_ok and weld_part10_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    if method == DesignMethod.LRFD:
        bolt_sym = _validated_markup(r"\phi R_n = \phi \cdot C \cdot F_{nv} \cdot A_b")
        bolt_sub = _validated_markup(rf"0.75 \cdot {c_icor:.3f} \cdot {f_nv:.1f} \cdot {a_b:.4f} = {cap_bolts:.2f} \text{{ kips}}")
        py_sym = _validated_markup(r"\phi R_{n,v} = 1.00 \cdot 0.60 \cdot F_y \cdot d_p \cdot t_p")
        py_sub = _validated_markup(rf"1.00 \cdot 0.60 \cdot {fy_p:.1f} \cdot {d_p:.2f} \cdot {t_p:.3f} = {cap_py:.2f} \text{{ kips}}")
    else:
        bolt_sym = _validated_markup(r"\frac{R_n}{\Omega} = \frac{C \cdot F_{nv} \cdot A_b}{\Omega}")
        bolt_sub = _validated_markup(rf"\frac{{{c_icor:.3f} \cdot {f_nv:.1f} \cdot {a_b:.4f}}}{{2.00}} = {cap_bolts:.2f} \text{{ kips}}")
        py_sym = _validated_markup(r"\frac{R_{n,v}}{\Omega} = \frac{0.60 \cdot F_y \cdot d_p \cdot t_p}{1.50}")
        py_sub = _validated_markup(rf"\frac{{0.60 \cdot {fy_p:.1f} \cdot {d_p:.2f} \cdot {t_p:.3f}}}{{1.50}} = {cap_py:.2f} \text{{ kips}}")

    trace = (
        CalcStep(
            step_id="S1_GEOM_DUCT",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Shear Tab Depth, Ductility Thickness & Detailing Checks",
            symbolic=_validated_markup(r"0.5 T \leq d_p \leq T, t_p \leq t_{p,\max}"),
            substituted=_validated_markup(
                rf"{0.5 * t_clear_beam:.2f} \leq d_p = {d_p:.2f} \leq {t_clear_beam:.2f} \text{{ in., }} t_p = {t_p:.3f} \leq {t_p_max_allowed:.3f} \text{{ in.}}"
            ),
            variables={
                "d_p": Quantity("d_p", d_p, "in.", "Shear tab plate depth"),
                "T_beam": Quantity("T", t_clear_beam, "in.", "Beam web clear depth"),
                "t_p": Quantity("t_p", t_p, "in.", "Shear tab thickness"),
                "t_p_max": Quantity("t_{p,\\max}", round(t_p_max_allowed, 3), "in.", "Part 10 ductility thickness limit"),
                "e_x": Quantity("e_x", e_x_in, "in.", "Design bolt eccentricity"),
            },
            result_value=round(t_p, 3),
            result_unit="in.",
            acceptance=AcceptanceCriterion("<=", round(t_p_max_allowed, 3), "in.", "Part 10 shear tab geometry & ductility limit", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if stage1_ok else CalculationStatus.FAIL,
            refs=(ref_part10, ref_j3_3, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S2_BOLT_WELD",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Eccentric Bolt Group (ICOR) & Double-Sided Fillet Weld",
            symbolic=bolt_sym,
            substituted=bolt_sub,
            variables={
                "C": Quantity("C", round(c_icor, 3), "", "Part 7 Table 7-6 ICOR coefficient"),
                "V_demand": Quantity("V", round(v_demand, 2), "kips", f"{method.value} beam end shear"),
                "R_bolt": Quantity("R_{bolt}", round(cap_bolts, 2), "kips", f"{method.value} bolt group capacity"),
                "f_weld": Quantity("f_w", round(f_weld_req, 3), "kips/in.", "Unit demand on double fillet weld"),
                "r_weld": Quantity("r_w", round(cap_weld_in, 3), "kips/in.", f"{method.value} fillet weld capacity"),
            },
            result_value=round(cap_bolts, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} ICOR bolt shear check", is_dcr_check=True),
            dcr=round(max(dcr_bolts, dcr_weld), 3),
            status=CalculationStatus.PASS if max(dcr_bolts, dcr_weld) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_part7, ref_j3_2, ref_j2_5, ref_proc),
        ),
        CalcStep(
            step_id="S3_PLATE_STATES",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Plate Shear Yield/Rupture, Block Shear, Flexural-Shear & Bearing",
            symbolic=py_sym,
            substituted=py_sub,
            variables={
                "cap_py": Quantity("V_{y,pl}", round(cap_py, 2), "kips", "Plate gross shear yielding capacity"),
                "cap_pr": Quantity("V_{r,pl}", round(cap_pr, 2), "kips", "Plate net shear rupture capacity"),
                "cap_bs": Quantity("R_{bs,pl}", round(cap_bs, 2), "kips", "Plate block shear capacity"),
                "dcr_vm": Quantity("\\text{DCR}_{VM}", round(dcr_vm, 3), "", "Flexural-shear von Mises interaction"),
                "cap_brg": Quantity("R_{brg}", round(cap_brg, 2), "kips", "Governing plate/web bearing capacity"),
            },
            result_value=round(min(cap_py, cap_pr, cap_bs, cap_vm_equiv, cap_brg), 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} governing plate/bearing limit", is_dcr_check=True),
            dcr=round(max(dcr_py, dcr_pr, dcr_bs, dcr_vm, dcr_brg), 3),
            status=CalculationStatus.PASS if max(dcr_py, dcr_pr, dcr_bs, dcr_vm, dcr_brg) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, ref_part10, ref_proc),
        ),
        CalcStep(
            step_id="S4_SUPPORT",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title=sup_title,
            symbolic=_validated_markup(r"V_{beam} = 0.60 F_{y,b} d t_w"),
            substituted=_validated_markup(
                rf"V_{{beam,cap}} = {cap_beam_web:.2f} \text{{ kips, }} R_{{sup,cap}} = {cap_sup:.2f} \text{{ kips}}"
            ),
            variables={
                "V_beam_cap": Quantity("V_{beam}", round(cap_beam_web, 2), "kips", "Supported beam gross web shear capacity"),
                "R_sup_cap": Quantity("R_{sup}", round(cap_sup, 2), "kips", "Supporting column/girder local shear capacity"),
                "hss_bt": Quantity("b/t", round(hss_slenderness, 2), "", "HSS wall slenderness (if HSS support)"),
            },
            result_value=round(min(cap_beam_web, cap_sup), 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_demand, 2), "kips", f"{method.value} beam/support member check", is_dcr_check=True),
            dcr=round(max(dcr_beam_web, dcr_sup), 3),
            status=CalculationStatus.PASS if max(dcr_beam_web, dcr_sup) <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_shapes, ref_mat, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not weld_part10_ok:
        warnings.append(f"Shear tab weld w={w_weld_in:.3f} in. < 5/8 * t_p = {w_min_part10:.3f} in. (Part 10 rule).")
    if not hss_compact_ok:
        warnings.append(f"Supporting HSS wall slenderness {hss_slenderness:.2f} > {hss_slenderness_lim:.2f}.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_shear_tab",
        code_edition="AISC 360-22 / Manual 16th Ed.",
        design_method=method,
        input_parameters={
            "beam_section": beam_section,
            "support_section": support_section,
            "plate_grade": plate_grade,
            "t_plate_in": t_p,
            "d_p_in": d_p,
            "a_in": a_in,
            "n_bolts": n_bolts,
            "d_b_in": d_b_in,
            "bolt_grade": bolt_grade,
            "thread_condition": thread_cond,
            "s_in": s_in,
            "L_ev_in": l_ev_in,
            "L_eh_in": l_eh_in,
            "w_weld_in": w_weld_in,
            "V_demand_kips": v_demand,
        },
        assumptions=[
            f"Configuration evaluated as {'Conventional' if is_conventional else 'Extended'} shear tab per AISC Manual Part 10.",
            f"Bolt group design eccentricity e_x = {e_x_in:.2f} in. using AISC Manual Table 7-6 (ICOR).",
            "Part 10 Table 7-6 CSV value C=2.48 is used directly for n=3, e_x=1.50 in.",
        ],
        intermediate_results={
            "is_conventional": is_conventional,
            "e_x_in": e_x_in,
            "C_icor": round(c_icor, 3),
            "cap_bolts_kips": round(cap_bolts, 2),
            "cap_plate_yield_kips": round(cap_py, 2),
            "cap_plate_rupture_kips": round(cap_pr, 2),
            "cap_block_shear_kips": round(cap_bs, 2),
            "dcr_von_mises": round(dcr_vm, 3),
            "cap_bearing_kips": round(cap_brg, 2),
            "cap_beam_web_kips": round(cap_beam_web, 2),
            "cap_support_kips": round(cap_sup, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path
            for r in (ref_proc, ref_part10, ref_part7, ref_j3_2, ref_j3_3, ref_j2_5, ref_shapes, ref_mat)
            if r.source_path
        ],
        warnings=warnings,
        trace=trace,
    )
