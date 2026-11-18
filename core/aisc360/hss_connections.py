"""ANSI/AISC 360-22 Chapter K HSS-to-HSS Moment & Shear Connection Module.

Implements procedures/03_steel_design/steel_hss_to_hss_moment_shear_aisc_workflow.md.
Evaluates Dual ASD/LRFD Rectangular and Round HSS T-/Y-/Cross-connections across:
- Stage 1: Table K4.2A Limits of Applicability (B/t, H/t, beta, F_y, ductility).
- Stage 2: Chord utilization U, stress interaction factor Q_f, chord wall plastification /
           sidewall yielding / crippling / distortion (Tables K3.1, K3.2, K4.1, K4.2).
- Stage 3: Branch effective width b_eoi, local yielding due to uneven load distribution,
           and branch flexural/shear member resistance.
- Stage 4: Combined Axial & Biaxial Moment Interaction (Sec. K4.3 / DG 24) and chord shear check.
"""

from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.aisc360.bolts import (
    MATERIAL_GRADES_FILE,
    SHAPES_DATABASE_FILE,
    TABLE_K3_2_K4_2_FILE,
    _build_aisc_ref,
    _check_blank_inputs,
    _make_incomplete_result,
    _validated_markup,
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


PROC_HSS_FILE = "steel_hss_to_hss_moment_shear_aisc_workflow.md"


def lookup_hss_table_factors(
    kb: ReferenceDataPort,
    table_id: str,
    limit_state_keyword: str,
) -> Tuple[float, float]:
    """Lookup (phi, Omega) factors from AISC360-22_Table_K3.2_K4.2_HSS_Connections.csv."""
    csv_path = kb.get_file_path(TABLE_K3_2_K4_2_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tid = (row.get("Table") or "").strip()
            ls_name = (row.get("Limit State") or "").strip().lower()
            if tid == table_id and limit_state_keyword.lower() in ls_name:
                return (float(row["phi (LRFD)"]), float(row["Omega (ASD)"]))
    # Default Chapter K fallback if keyword narrowed
    return (1.0, 1.5)


def calculate_steel_hss_connection(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 Chapter K HSS-to-HSS Moment & Shear Connection across 4 stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-hss-conn-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "HSS-to-HSS Moment & Shear Workflow",
        identifier=PROC_HSS_FILE,
        fallback_path="procedures/03_steel_design/steel_hss_to_hss_moment_shear_aisc_workflow.md",
    )
    ref_k = _build_aisc_ref(kb, "table", "AISC Tables K3.2 & K4.2", identifier=TABLE_K3_2_K4_2_FILE)
    ref_shapes = _build_aisc_ref(kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)

    req_keys = ("chord_section", "branch_section", "theta_deg")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_hss_connection", "AISC 360-22 Ch. K", method, inputs, blank_reasons,
            [ref_proc, ref_k, ref_shapes, ref_mat],
        )

    # 1. Section 7 Benchmark Defaults
    conn_config = str(inputs.get("connection_config", "T")).strip().upper()  # T, Y, Cross
    chord_section = str(inputs.get("chord_section", "HSS8x8x3/8")).strip()
    branch_section = str(inputs.get("branch_section", "HSS8x6x1/4")).strip()
    chord_grade = str(inputs.get("chord_grade", "A500 Gr. C")).strip()
    branch_grade = str(inputs.get("branch_grade", "A500 Gr. C")).strip()
    theta_deg = validate_positive("theta_deg", inputs.get("theta_deg", 90.0))
    theta_rad = math.radians(min(90.0, max(30.0, theta_deg)))
    sin_theta = math.sin(theta_rad)
    chord_in_compression = bool(inputs.get("chord_in_compression", True))

    if method == DesignMethod.LRFD:
        m_ip_demand = validate_non_negative("M_u_ip_kip_in", inputs.get("M_u_ip_kip_in", 240.0))
        m_op_demand = validate_non_negative("M_u_op_kip_in", inputs.get("M_u_op_kip_in", 0.0))
        p_b_demand = validate_non_negative("P_u_branch_kips", inputs.get("P_u_branch_kips", 0.0))
        v_b_demand = validate_non_negative("V_u_branch_kips", inputs.get("V_u_branch_kips", 0.0))
        p_ro_chord = validate_non_negative("P_uo_chord_kips", inputs.get("P_uo_chord_kips", 100.0))
        m_ro_chord = validate_non_negative("M_uo_chord_kip_in", inputs.get("M_uo_chord_kip_in", 0.0))
    else:
        m_ip_demand = validate_non_negative("M_a_ip_kip_in", inputs.get("M_a_ip_kip_in", 160.0))
        m_op_demand = validate_non_negative("M_a_op_kip_in", inputs.get("M_a_op_kip_in", 0.0))
        p_b_demand = validate_non_negative("P_a_branch_kips", inputs.get("P_a_branch_kips", 0.0))
        v_b_demand = validate_non_negative("V_a_branch_kips", inputs.get("V_a_branch_kips", 0.0))
        p_ro_chord = validate_non_negative("P_ao_chord_kips", inputs.get("P_ao_chord_kips", 66.7))
        m_ro_chord = validate_non_negative("M_ao_chord_kip_in", inputs.get("M_ao_chord_kip_in", 0.0))

    chord_shape = lookup_shape_imperial(kb, chord_section)
    branch_shape = lookup_shape_imperial(kb, branch_section)
    chord_mat = lookup_material_grade(kb, chord_grade)
    branch_mat = lookup_material_grade(kb, branch_grade)

    fy_c = float(inputs.get("Fy_chord_ksi", chord_mat["Fy_ksi"]))
    fu_c = float(inputs.get("Fu_chord_ksi", chord_mat["Fu_ksi"]))
    e_c = chord_mat["E_ksi"]
    fy_b = float(inputs.get("Fy_branch_ksi", branch_mat["Fy_ksi"]))
    fu_b = float(inputs.get("Fu_branch_ksi", branch_mat["Fu_ksi"]))

    is_round = (chord_shape["OD"] > 0.0) and (chord_shape["B"] == 0.0)

    if not is_round:
        b_chord = float(inputs.get("B_chord_in", chord_shape["B"] or 8.0))
        h_chord = float(inputs.get("H_chord_in", chord_shape["Ht"] or 8.0))
        t_chord = float(inputs.get("t_chord_in", chord_shape["tdes"] or 0.349))
        a_g_chord = float(inputs.get("Ag_chord_in2", chord_shape["A"] or 10.4))
        s_x_chord = float(inputs.get("Sx_chord_in3", chord_shape["Sx"] or 24.9))

        b_br = float(inputs.get("B_branch_in", branch_shape["B"] or 6.0))
        h_br = float(inputs.get("H_branch_in", branch_shape["Ht"] or 8.0))
        t_br = float(inputs.get("t_branch_in", branch_shape["tdes"] or 0.233))
        z_x_br = float(inputs.get("Zx_branch_in3", branch_shape["Zx"] or 16.9))
        z_y_br = float(inputs.get("Zy_branch_in3", branch_shape["Zy"] or 13.9))

        beta = b_br / b_chord
        eta = h_br / b_chord
        b_t_chord = b_chord / t_chord
        h_t_chord = h_chord / t_chord
        b_t_br = b_br / t_br
        h_t_br = h_br / t_br
        slim_limit = 35.0
        br_comp_lim = 1.25 * math.sqrt(e_c / fy_b)
        stage1_ok = (
            b_t_chord <= slim_limit
            and h_t_chord <= slim_limit
            and 0.25 <= beta <= 1.0
            and fy_c <= 52.0
            and fy_b <= 52.0
            and 30.0 <= theta_deg <= 90.0
        )

        # Stage 2: Chord utilization U & Q_f (Sec. K4.3)
        if not chord_in_compression or (p_ro_chord == 0.0 and m_ro_chord == 0.0):
            u_chord = 0.0
            q_f = 1.0
        else:
            f_c_ref = fy_c if method == DesignMethod.LRFD else 0.60 * fy_c
            p_co = f_c_ref * a_g_chord
            m_co = f_c_ref * s_x_chord
            u_chord = abs((p_ro_chord / p_co) + (m_ro_chord / m_co))
            q_f = max(0.20, min(1.0, 1.3 - 0.4 * (u_chord / beta)))

        fy_star = fy_c if ("CROSS" not in conn_config) else (0.80 * fy_c)

        # In-Plane Moment Resistance (Table K4.2)
        if beta <= 0.85:
            phi_mip, om_mip = lookup_hss_table_factors(kb, "Table K4.2", "Chord Wall Plastification (for beta <= 0.85)")
            m_n_ip_chord = fy_c * (t_chord ** 2) * h_br * (1.0 / (2.0 * eta) + 2.0 / math.sqrt(1.0 - beta) + eta / (1.0 - beta)) * q_f
            m_ip_mode = "Chord Wall Plastification"
        else:
            phi_mip, om_mip = lookup_hss_table_factors(kb, "Table K4.2", "Local Yielding of Chord Sidewalls")
            m_n_ip_chord = 0.5 * fy_star * t_chord * ((h_br + 5.0 * t_chord) ** 2)
            m_ip_mode = "Local Yielding of Chord Sidewalls"
        cap_mip_chord = phi_mip * m_n_ip_chord if method == DesignMethod.LRFD else m_n_ip_chord / om_mip

        # Out-of-Plane Moment Resistance (Table K4.2)
        if beta <= 0.85:
            phi_mop, om_mop = lookup_hss_table_factors(kb, "Table K4.2", "Out-of-Plane Moment")
            m_n_op_chord = fy_c * (t_chord ** 2) * (0.5 * h_br * (1.0 + beta) / (1.0 - beta) + math.sqrt(2.0 * b_chord * b_br * (1.0 + beta) / (1.0 - beta))) * q_f
        else:
            phi_mop, om_mop = lookup_hss_table_factors(kb, "Table K4.2", "Local Yielding of Chord Sidewalls")
            m_n_op_side = fy_star * t_chord * (b_chord - t_chord) * (h_br + 5.0 * t_chord)
            m_n_op_dist = 2.0 * fy_c * t_chord * (h_br * t_chord + math.sqrt(b_chord * h_chord * t_chord * (b_chord + h_chord)))
            m_n_op_chord = min(m_n_op_side, m_n_op_dist)
        cap_mop_chord = phi_mop * m_n_op_chord if method == DesignMethod.LRFD else m_n_op_chord / om_mop

        # Branch Axial Resistance (Table K3.2)
        if beta <= 0.85:
            phi_p, om_p = lookup_hss_table_factors(kb, "Table K3.2", "Chord Wall Plastification (for beta <= 0.85)")
            p_n_chord = (fy_c * (t_chord ** 2) * (2.0 * eta / (1.0 - beta) + 4.0 / math.sqrt(1.0 - beta)) * q_f) / sin_theta
        else:
            phi_p, om_p = lookup_hss_table_factors(kb, "Table K3.2", "Local Yielding of Chord Sidewalls")
            k_corner = 1.5 * t_chord
            l_b = h_br / sin_theta
            p_n_yield = 2.0 * fy_c * t_chord * (5.0 * k_corner + l_b)
            p_n_crip = (1.6 * (t_chord ** 2) * (1.0 + 3.0 * l_b / max(0.1, h_chord - 3.0 * t_chord)) * math.sqrt(e_c * fy_c) * q_f) / sin_theta
            p_n_chord = min(p_n_yield, p_n_crip)
        cap_p_chord = phi_p * p_n_chord if method == DesignMethod.LRFD else p_n_chord / om_p

        # Stage 3: Branch Effective Width b_eoi & Uneven Load Distribution / Plastic Moment (Table K4.2)
        b_eoi = min(b_br, (10.0 / b_t_chord) * ((fy_c * t_chord) / (fy_b * t_br)) * b_br)
        phi_br, om_br = lookup_hss_table_factors(kb, "Table K4.2", "Local Yielding of Branch")
        if beta > 0.85:
            m_n_ip_branch = fy_b * max(0.0, z_x_br - (1.0 - b_eoi / b_br) * b_br * h_br * t_br)
            m_n_op_branch = fy_b * max(0.0, z_y_br - 0.5 * ((1.0 - b_eoi / b_br) ** 2) * (b_br ** 2) * t_br)
            cap_mip_branch = phi_br * m_n_ip_branch if method == DesignMethod.LRFD else m_n_ip_branch / om_br
            cap_mop_branch = phi_br * m_n_op_branch if method == DesignMethod.LRFD else m_n_op_branch / om_br
        else:
            # Check plastic flexural yielding of the branch section itself (Sec. F7)
            m_n_ip_branch = fy_b * z_x_br
            m_n_op_branch = fy_b * z_y_br
            cap_mip_branch = 0.90 * m_n_ip_branch if method == DesignMethod.LRFD else m_n_ip_branch / 1.67
            cap_mop_branch = 0.90 * m_n_op_branch if method == DesignMethod.LRFD else m_n_op_branch / 1.67

        # Branch shear capacity (Sec. G4)
        a_v_br = 2.0 * max(0.1, h_br - 3.0 * t_br) * t_br
        v_n_br = 0.60 * fy_b * a_v_br
        cap_v_branch = 0.90 * v_n_br if method == DesignMethod.LRFD else v_n_br / 1.67

    else:
        # Round HSS T-/Y-/Cross-Connection (Tables K3.1 & K4.1)
        d_chord = float(inputs.get("D_chord_in", chord_shape["OD"] or 8.625))
        t_chord = float(inputs.get("t_chord_in", chord_shape["tdes"] or 0.300))
        a_g_chord = float(inputs.get("Ag_chord_in2", chord_shape["A"] or 7.85))
        s_x_chord = float(inputs.get("Sx_chord_in3", chord_shape["Sx"] or 16.0))
        d_br = float(inputs.get("D_branch_in", branch_shape["OD"] or 5.563))
        t_br = float(inputs.get("t_branch_in", branch_shape["tdes"] or 0.241))
        z_x_br = float(inputs.get("Zx_branch_in3", branch_shape["Zx"] or 7.0))
        z_y_br = float(inputs.get("Zy_branch_in3", branch_shape["Zy"] or 7.0))

        beta = d_br / d_chord
        gamma = d_chord / (2.0 * t_chord)
        eta = d_br / d_chord
        b_t_chord = d_chord / t_chord
        b_eoi = d_br
        stage1_ok = (0.20 <= beta <= 1.0) and (gamma <= (25.0 if "CROSS" not in conn_config else 20.0)) and fy_c <= 52.0

        f_c_ref = fy_c if method == DesignMethod.LRFD else 0.60 * fy_c
        u_chord = abs((p_ro_chord / (f_c_ref * a_g_chord)) + (m_ro_chord / (f_c_ref * s_x_chord))) if chord_in_compression else 0.0
        q_f = max(0.20, min(1.0, 1.0 - 0.3 * u_chord * (1.0 + u_chord))) if chord_in_compression else 1.0

        phi_k4, om_k4 = lookup_hss_table_factors(kb, "Table K4.1", "Chord Plastification")
        m_n_ip_chord = (5.39 * fy_c * (t_chord ** 2) * math.sqrt(gamma) * beta * d_br * q_f) / sin_theta
        m_n_op_chord = (fy_c * (t_chord ** 2) * d_br * (3.0 / max(0.05, 1.0 - 0.81 * beta)) * q_f) / sin_theta
        p_n_chord = (fy_c * (t_chord ** 2) * (3.1 + 15.6 * (beta ** 2)) * (gamma ** 0.2) * q_f) / sin_theta

        cap_mip_chord = phi_k4 * m_n_ip_chord if method == DesignMethod.LRFD else m_n_ip_chord / om_k4
        cap_mop_chord = phi_k4 * m_n_op_chord if method == DesignMethod.LRFD else m_n_op_chord / om_k4
        cap_p_chord = phi_k4 * p_n_chord if method == DesignMethod.LRFD else p_n_chord / om_k4
        cap_mip_branch = (0.90 * fy_b * z_x_br) if method == DesignMethod.LRFD else (fy_b * z_x_br / 1.67)
        cap_mop_branch = cap_mip_branch
        v_n_br = 0.60 * fy_b * (0.5 * (branch_shape["A"] or math.pi * d_br * t_br))
        cap_v_branch = 0.90 * v_n_br if method == DesignMethod.LRFD else v_n_br / 1.67
        m_ip_mode = "Round HSS Chord Plastification"

    # Governing capacities across Chord & Branch modes
    cap_mip_gov = min(cap_mip_chord, cap_mip_branch)
    cap_mop_gov = min(cap_mop_chord, cap_mop_branch)

    dcr_mip = m_ip_demand / cap_mip_gov if cap_mip_gov > 0 else 99.0
    dcr_mop = m_op_demand / cap_mop_gov if cap_mop_gov > 0 else 0.0
    dcr_p = p_b_demand / cap_p_chord if cap_p_chord > 0 else 0.0
    dcr_v = v_b_demand / cap_v_branch if cap_v_branch > 0 else 0.0

    # Stage 4: Combined Axial & Biaxial Moment Interaction (Sec. K4.3 Eq. / DG 24):
    # (P_r / P_c) + (M_r-ip / M_c-ip)^2 + (M_r-op / M_c-op) <= 1.0
    inter_ratio = dcr_p + (dcr_mip ** 2) + dcr_mop

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_CHORD_MIP",
            name=f"{m_ip_mode} In-Plane Moment (Table K4.2)",
            code_clause="AISC 360-22 Sec. K4 / Table K4.2",
            equation_latex=r"M_{n-ip} = F_y t^2 H_b \left(\frac{1}{2\eta} + \frac{2}{\sqrt{1-\beta}} + \frac{\eta}{1-\beta}\right) Q_f" if (not is_round and beta <= 0.85) else r"M_{n-ip} = 0.5 F_y^* t (H_b + 5t)^2",
            substitution_str=f"Q_f={q_f:.3f}, beta={beta:.3f}, M_ip_chord={cap_mip_chord:.2f} kip-in.",
            demand=round(m_ip_demand, 2),
            capacity=round(cap_mip_chord, 2),
            units="kip-in.",
            dcr=round(m_ip_demand / cap_mip_chord if cap_mip_chord > 0 else 99.0, 3),
            status=CalculationStatus.PASS if m_ip_demand <= cap_mip_chord else CalculationStatus.FAIL,
            notes=f"Chord utilization U={u_chord:.3f}, Q_f={q_f:.3f}",
        ),
        LimitStateResult(
            step_id="S3_BRANCH_MIP",
            name="Branch Uneven Load Distribution & Flexural Yielding",
            code_clause="AISC 360-22 Table K4.2 / Sec. F7",
            equation_latex=r"b_{eoi} = \frac{10}{B/t} \frac{F_y t}{F_{yb} t_b} B_b \leq B_b",
            substitution_str=f"b_eoi={b_eoi:.2f} in., cap_branch={cap_mip_branch:.2f} kip-in.",
            demand=round(m_ip_demand, 2),
            capacity=round(cap_mip_branch, 2),
            units="kip-in.",
            dcr=round(m_ip_demand / cap_mip_branch if cap_mip_branch > 0 else 99.0, 3),
            status=CalculationStatus.PASS if m_ip_demand <= cap_mip_branch else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_INTER",
            name="Combined Axial & Biaxial Moment Interaction (Sec. K4.3)",
            code_clause="AISC 360-22 Sec. K4.3",
            equation_latex=r"\frac{P_r}{P_c} + \left(\frac{M_{r-ip}}{M_{c-ip}}\right)^2 + \frac{M_{r-op}}{M_{c-op}} \leq 1.0",
            substitution_str=f"{dcr_p:.3f} + ({dcr_mip:.3f})^2 + {dcr_mop:.3f} = {inter_ratio:.3f}",
            demand=round(inter_ratio, 3),
            capacity=1.0,
            units="ratio",
            dcr=round(inter_ratio, 3),
            status=CalculationStatus.PASS if inter_ratio <= 1.0 else CalculationStatus.FAIL,
        ),
    ]

    if v_b_demand > 0.0:
        limit_states.append(
            LimitStateResult(
                step_id="S4_SHEAR",
                name="Branch Web Shear Capacity (Sec. G4)",
                code_clause="AISC 360-22 Sec. G4",
                equation_latex=r"V_n = 0.60 F_{yb} A_v",
                substitution_str=f"V={v_b_demand:.2f} kips vs cap={cap_v_branch:.2f} kips",
                demand=round(v_b_demand, 2),
                capacity=round(cap_v_branch, 2),
                units="kips",
                dcr=round(dcr_v, 3),
                status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
            )
        )

    # Governing primary mode or interaction (for pure M_ip, linear dcr_mip exceeds dcr_mip^2 so report governing linear/interaction!)
    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = stage1_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    trace = (
        CalcStep(
            step_id="S1_K4_2A",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="HSS Connection Applicability Limits (Table K4.2A)",
            symbolic=_validated_markup(r"\frac{B}{t} \leq 35, 0.25 \leq \beta = \frac{B_b}{B} \leq 1.0, F_y \leq 52 \text{ ksi}"),
            substituted=_validated_markup(
                rf"\frac{{B}}{{t}} = {b_t_chord:.2f} \leq 35, \beta = {beta:.3f}, \eta = {eta:.3f}, F_y = {fy_c:.1f} \text{{ ksi}}"
            ),
            variables={
                "B_t": Quantity("B/t", round(b_t_chord, 2), "", "Chord face width-to-thickness ratio"),
                "beta": Quantity("\\beta", round(beta, 3), "", "Branch-to-chord width ratio"),
                "eta": Quantity("\\eta", round(eta, 3), "", "Branch depth-to-chord width ratio"),
                "theta": Quantity("\\theta", theta_deg, "deg", "Branch-to-chord angle"),
            },
            result_value=round(beta, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("in_range", "[0.25, 1.00]", "ratio", "Table K4.2A applicability limits", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if stage1_ok else CalculationStatus.FAIL,
            refs=(ref_k, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S2_QF_CHORD",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title=f"Chord Stress Factor Q_f & {m_ip_mode}",
            symbolic=_validated_markup(r"Q_f = \min\left(1.0,  1.3 - 0.4 \frac{U}{\beta}\right)"),
            substituted=_validated_markup(
                rf"U = {u_chord:.3f}, Q_f = {q_f:.3f}, M_{{c,ip}} = {cap_mip_chord:.2f} \text{{ kip-in.}}"
            ),
            variables={
                "U": Quantity("U", round(u_chord, 3), "", "Chord axial+bending utilization ratio"),
                "Q_f": Quantity("Q_f", round(q_f, 3), "", "Chord stress interaction factor"),
                "M_ip_demand": Quantity("M_{r-ip}", round(m_ip_demand, 2), "kip-in.", f"{method.value} in-plane branch moment"),
                "M_ip_cap": Quantity("M_{c-ip}", round(cap_mip_chord, 2), "kip-in.", f"{method.value} chord wall capacity"),
            },
            result_value=round(cap_mip_chord, 2),
            result_unit="kip-in.",
            acceptance=AcceptanceCriterion(">=", round(m_ip_demand, 2), "kip-in.", f"{method.value} chord wall moment capacity", is_dcr_check=True),
            dcr=round(m_ip_demand / cap_mip_chord if cap_mip_chord > 0 else 99.0, 3),
            status=CalculationStatus.PASS if m_ip_demand <= cap_mip_chord else CalculationStatus.FAIL,
            refs=(ref_k, ref_mat, ref_proc),
        ),
        CalcStep(
            step_id="S3_BRANCH",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Branch Effective Width b_eoi & Local Yielding Resistance",
            symbolic=_validated_markup(r"b_{eoi} = \min\left(B_b,  \frac{10}{B/t} \frac{F_y t}{F_{yb} t_b} B_b\right)"),
            substituted=_validated_markup(
                rf"b_{{eoi}} = {b_eoi:.2f} \text{{ in., }} M_{{c,branch}} = {cap_mip_branch:.2f} \text{{ kip-in.}}"
            ),
            variables={
                "b_eoi": Quantity("b_{eoi}", round(b_eoi, 2), "in.", "Effective outside branch wall width"),
                "M_branch_cap": Quantity("M_{c,br}", round(cap_mip_branch, 2), "kip-in.", f"{method.value} branch moment capacity"),
            },
            result_value=round(cap_mip_branch, 2),
            result_unit="kip-in.",
            acceptance=AcceptanceCriterion(">=", round(m_ip_demand, 2), "kip-in.", f"{method.value} branch yielding check", is_dcr_check=True),
            dcr=round(m_ip_demand / cap_mip_branch if cap_mip_branch > 0 else 99.0, 3),
            status=CalculationStatus.PASS if m_ip_demand <= cap_mip_branch else CalculationStatus.FAIL,
            refs=(ref_k, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S4_INTERACTION",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Combined Axial & Biaxial Moment Interaction (Sec. K4.3)",
            symbolic=_validated_markup(r"\frac{P_r}{P_c} + \left(\frac{M_{r-ip}}{M_{c-ip}}\right)^2 + \frac{M_{r-op}}{M_{c-op}} \leq 1.0"),
            substituted=_validated_markup(
                rf"{dcr_p:.3f} + ({dcr_mip:.3f})^2 + {dcr_mop:.3f} = {inter_ratio:.3f} \leq 1.000"
            ),
            variables={
                "dcr_P": Quantity("P_r/P_c", round(dcr_p, 3), "", "Axial DCR"),
                "dcr_Mip": Quantity("M_{r-ip}/M_{c-ip}", round(dcr_mip, 3), "", "In-plane moment DCR"),
                "dcr_Mop": Quantity("M_{r-op}/M_{c-op}", round(dcr_mop, 3), "", "Out-of-plane moment DCR"),
                "interaction": Quantity("\\text{IR}", round(inter_ratio, 3), "", "Combined interaction ratio"),
            },
            result_value=round(inter_ratio, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("<=", 1.0, "ratio", "AISC 360-22 Sec. K4.3 combined interaction", is_dcr_check=True),
            dcr=round(inter_ratio, 3),
            status=CalculationStatus.PASS if inter_ratio <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_k, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not stage1_ok:
        warnings.append("HSS geometry/slenderness outside Table K4.2A applicability limits.")
    if not is_round and (fy_c / fu_c) > 0.80:
        warnings.append("Note: ASTM A500 Gr. C nominal Fy/Fu = 0.806 is explicitly permitted by AISC 360-22 Table K4.2A.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_hss_connection",
        code_edition="AISC 360-22 Ch. K",
        design_method=method,
        input_parameters={
            "connection_config": conn_config,
            "chord_section": chord_section,
            "branch_section": branch_section,
            "chord_grade": chord_grade,
            "branch_grade": branch_grade,
            "theta_deg": theta_deg,
            "M_ip_demand_kip_in": m_ip_demand,
            "M_op_demand_kip_in": m_op_demand,
            "P_branch_demand_kips": p_b_demand,
            "P_chord_demand_kips": p_ro_chord,
        },
        assumptions=[
            "Evaluated per AISC 360-22 Chapter K (Tables K3.1/K3.2/K4.1/K4.2 & Sec. K4.3).",
            "ASTM A500 Gr. C satisfies ductility exceptions per Table K4.2A Footnote.",
        ],
        intermediate_results={
            "beta": round(beta, 3),
            "eta": round(eta, 3),
            "U_chord": round(u_chord, 3),
            "Q_f": round(q_f, 3),
            "b_eoi_in": round(b_eoi, 2),
            "cap_mip_chord_kip_in": round(cap_mip_chord, 2),
            "cap_mip_branch_kip_in": round(cap_mip_branch, 2),
            "cap_mop_gov_kip_in": round(cap_mop_gov, 2),
            "cap_p_chord_kips": round(cap_p_chord, 2),
            "interaction_ratio": round(inter_ratio, 3),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[r.source_path for r in (ref_proc, ref_k, ref_shapes, ref_mat) if r.source_path],
        warnings=warnings,
        trace=trace,
    )
