"""ANSI/AISC 360-22 Sec. J8 & Design Guide 1 Column Base Plate and Anchor Rod Module.

Implements procedures/03_steel_design/steel_column_base_plate_aisc_dg1_workflow.md.
Evaluates Dual ASD/LRFD column base plates under axial compression + moment + shear:
- Stage 1: Base plate plan geometry, DG1 Table 2.3 oversized holes & plate washers,
           and OSHA 29 CFR 1926.755 minimum 4-anchor-rod erection mandate.
- Stage 2: Concrete bearing stress block (Sec. J8 Eq. J8-2, small-moment vs. large-moment
           triangular block), anchor rod tension & shear + tension-shear interaction.
- Stage 3: Base plate flexural yielding thickness (bearing & tension interfaces per DG1).
- Stage 4: Pedestal confinement / global equilibrium & OSHA 300 lb @ 18 in. moment check.
"""

from __future__ import annotations

import csv
import math
import re
from typing import Any, Dict, List, Optional
import uuid

from core.aisc360.bolts import (
    DG1_BASE_PLATE_FILE,
    MATERIAL_GRADES_FILE,
    SHAPES_DATABASE_FILE,
    TABLE_J3_2_FILE,
    _build_aisc_ref,
    _check_blank_inputs,
    _make_incomplete_result,
    _parse_fraction,
    _validated_markup,
    lookup_bolt_properties,
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
from core.common.exceptions import InputValidationError
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort


PROC_BASE_PLATE_FILE = "steel_column_base_plate_aisc_dg1_workflow.md"


def lookup_dg1_anchor_rod(kb: ReferenceDataPort, d_a_in: float, rod_grade: str = "F1554 Gr. 36") -> Dict[str, Any]:
    """Lookup DG1 anchor rod area, hole dia, washer specs, and tension capacities."""
    csv_path = kb.get_file_path(DG1_BASE_PLATE_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    grade_u = rod_grade.upper()
    matched: Optional[List[str]] = None
    for row in rows[1:10]:
        if len(row) < 12:
            continue
        if abs(_parse_fraction(row[0], -1.0) - d_a_in) <= 1e-4:
            matched = row
            break

    if matched is None:
        raise InputValidationError(f"Anchor rod diameter {d_a_in} in. not found in AISC DG1 CSV.")

    if re.search(r"\b105\b", grade_u):
        phi_rn = float(matched[9])
        rn_omega = float(matched[10])
    elif re.search(r"\b55\b", grade_u):
        phi_rn = float(matched[7])
        rn_omega = float(matched[8])
    else:
        phi_rn = float(matched[5])
        rn_omega = float(matched[6])

    return {
        "A_b_in2": float(matched[1]),
        "d_h_oversized_in": _parse_fraction(matched[2]),
        "washer_size": matched[3].strip(),
        "washer_thick_in": _parse_fraction(matched[4]),
        "phi_R_nt_kips": phi_rn,
        "R_nt_omega_kips": rn_omega,
        "tolerance": matched[11].strip(),
    }


def calculate_steel_base_plate(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 Sec. J8 & Design Guide 1 Steel Column Base Plate across 4 stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-base-plate-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "Column Base Plate DG1 Workflow",
        identifier=PROC_BASE_PLATE_FILE,
        fallback_path="procedures/03_steel_design/steel_column_base_plate_aisc_dg1_workflow.md",
    )
    ref_dg1 = _build_aisc_ref(kb, "table", "AISC DG1 Base Plate & Anchor Rods", identifier=DG1_BASE_PLATE_FILE)
    ref_j3_2 = _build_aisc_ref(kb, "table", "Table J3.2", identifier=TABLE_J3_2_FILE)
    ref_shapes = _build_aisc_ref(kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)

    req_keys = ("column_section", "B_in", "N_in", "t_p_in", "fc_ksi", "d_a_in")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_base_plate", "AISC 360-22 / DG1", method, inputs, blank_reasons,
            [ref_proc, ref_dg1, ref_shapes, ref_mat],
        )

    # 1. Section 7 Benchmark Defaults
    col_section = str(inputs.get("column_section", "W10x49")).strip()
    plate_grade = str(inputs.get("plate_grade", "A36")).strip()
    b_in = validate_positive("B_in", inputs.get("B_in", 16.0))
    n_in = validate_positive("N_in", inputs.get("N_in", 16.0))
    t_p = validate_positive("t_p_in", inputs.get("t_p_in", 1.625))

    fc_ksi = validate_positive("fc_ksi", inputs.get("fc_ksi", 4.0))
    ratio_a2_a1 = validate_positive("ratio_A2_A1", inputs.get("ratio_A2_A1", 4.0))
    confinement_sqrt = min(2.0, math.sqrt(max(1.0, ratio_a2_a1)))

    d_a_in = validate_positive("d_a_in", inputs.get("d_a_in", 1.0))
    rod_grade = str(inputs.get("rod_grade", "F1554 Gr. 36")).strip()
    n_rods_total = int(validate_positive("n_rods_total", inputs.get("n_rods_total", 4)))
    n_rods_tens = int(validate_positive("n_rods_tension", inputs.get("n_rods_tension", max(1, n_rods_total // 2))))
    f_dist_in = validate_positive("f_dist_in", inputs.get("f_dist_in", 6.25))
    mu_friction = validate_non_negative("mu_friction", inputs.get("mu_friction", 0.55))
    has_grout_pad = bool(inputs.get("has_grout_pad", True))
    welded_washers = bool(inputs.get("welded_washers", True))

    if method == DesignMethod.LRFD:
        p_demand = validate_non_negative("P_u_kips", inputs.get("P_u_kips", 120.0))
        m_demand = validate_non_negative("M_u_kip_in", inputs.get("M_u_kip_in", 900.0))
        v_demand = validate_non_negative("V_u_kips", inputs.get("V_u_kips", 12.0))
    else:
        p_demand = validate_non_negative("P_a_kips", inputs.get("P_a_kips", 80.0))
        m_demand = validate_non_negative("M_a_kip_in", inputs.get("M_a_kip_in", 600.0))
        v_demand = validate_non_negative("V_a_kips", inputs.get("V_a_kips", 8.0))

    col_shape = lookup_shape_imperial(kb, col_section)
    plate_mat = lookup_material_grade(kb, plate_grade)
    rod_mat = lookup_material_grade(kb, rod_grade)
    dg1_rod = lookup_dg1_anchor_rod(kb, d_a_in, rod_grade)
    rod_j3_2 = lookup_bolt_properties(kb, rod_grade, "N", d_a_in, fu_rod_ksi=rod_mat["Fu_ksi"])

    d_col = float(inputs.get("d_col_in", col_shape["d"] or 10.0))
    bf_col = float(inputs.get("bf_col_in", col_shape["bf"] or col_shape["B"] or 10.0))
    tf_col = float(inputs.get("tf_col_in", col_shape["tf"] or col_shape["tdes"] or 0.560))
    fy_p = float(inputs.get("Fy_plate_ksi", plate_mat["Fy_ksi"]))

    # 2. Stage 1 Geometry & OSHA 4-Rod Erection Check
    osha_rods_ok = n_rods_total >= 4
    geom_ok = (b_in >= bf_col) and (n_in >= d_col) and (f_dist_in < 0.5 * n_in)
    stage1_ok = osha_rods_ok and geom_ok

    # 3. Stage 2 Concrete Bearing (Sec. J8 Eq. J8-2) & Anchor Rod Force Equilibrium
    a1 = b_in * n_in
    f_p_nom_max = 0.85 * fc_ksi * confinement_sqrt
    f_p_max = 0.65 * f_p_nom_max if method == DesignMethod.LRFD else f_p_nom_max / 2.31
    q_max = f_p_max * b_in

    ecc = (m_demand / p_demand) if p_demand > 1e-6 else (1e6 if m_demand > 0 else 0.0)
    e_crit = (0.5 * n_in - p_demand / (2.0 * q_max)) if q_max > 0 else 0.0

    crushed_flag = False
    if m_demand == 0.0:
        # Pure concentric axial compression
        y_brg = n_in
        f_p_actual = p_demand / a1
        c_comp = p_demand
        t_rods_total = 0.0
    elif p_demand == 0.0:
        # Pure bending moment couple
        lever = 0.5 * n_in + f_dist_in - 0.5
        t_rods_total = m_demand / lever
        c_comp = t_rods_total
        y_brg = min(n_in, c_comp / q_max) if q_max > 0 else n_in
        f_p_actual = c_comp / (b_in * y_brg) if y_brg > 0 else f_p_max * 10.0
    elif ecc <= e_crit + 1e-9:
        # Small moment (no anchor tension)
        y_brg = max(0.01, n_in - 2.0 * ecc)
        f_p_actual = p_demand / (b_in * y_brg)
        c_comp = p_demand
        t_rods_total = 0.0
    else:
        # Large moment (concrete compression block + anchor tension)
        half_nf = f_dist_in + 0.5 * n_in
        disc = half_nf ** 2 - (2.0 * p_demand * (ecc + f_dist_in)) / q_max
        if disc < 0.0:
            crushed_flag = True
            y_brg = half_nf
            f_p_actual = f_p_max * 1.5
            c_comp = q_max * y_brg
            t_rods_total = max(0.0, c_comp - p_demand)
        else:
            y_brg = half_nf - math.sqrt(disc)
            f_p_actual = f_p_max
            c_comp = q_max * y_brg
            t_rods_total = max(0.0, c_comp - p_demand)

    dcr_bearing = (1.5 if crushed_flag else (f_p_actual / f_p_max))

    # Anchor Rod Tension Capacity (from DG1 CSV)
    cap_rod_tens_single = dg1_rod["phi_R_nt_kips"] if method == DesignMethod.LRFD else dg1_rod["R_nt_omega_kips"]
    cap_rods_tens = n_rods_tens * cap_rod_tens_single
    dcr_rod_tens = (t_rods_total / cap_rods_tens) if t_rods_total > 0 else 0.0

    # Anchor Rod / Friction Shear Check (Sec. J3.6 / J3.7 & DG1)
    v_friction_nom = mu_friction * c_comp
    v_friction_cap = (0.75 * v_friction_nom if method == DesignMethod.LRFD else v_friction_nom / 2.00) if c_comp > 0 else 0.0
    v_shear_net_on_rods = max(0.0, v_demand - v_friction_cap)

    grout_factor = 0.80 if has_grout_pad else 1.00
    n_shear_rods = n_rods_total if welded_washers else max(2, n_rods_total // 2)
    r_nv_rod = rod_j3_2["F_nv_ksi"] * dg1_rod["A_b_in2"] * grout_factor
    cap_rod_shear_single = 0.75 * r_nv_rod if method == DesignMethod.LRFD else r_nv_rod / 2.00
    cap_rods_shear = v_friction_cap + n_shear_rods * cap_rod_shear_single

    # Combined tension + shear interaction on tension-side anchor rods
    f_rv_rod = (v_shear_net_on_rods / (n_shear_rods * dg1_rod["A_b_in2"])) if v_shear_net_on_rods > 0 else 0.0
    f_nt_rod = rod_j3_2["F_nt_ksi"]
    f_nv_rod_eff = rod_j3_2["F_nv_ksi"] * grout_factor
    if method == DesignMethod.LRFD:
        f_nt_prime = min(f_nt_rod, 1.3 * f_nt_rod - (f_nt_rod / (0.75 * f_nv_rod_eff)) * f_rv_rod)
        cap_tens_inter = n_rods_tens * 0.75 * max(0.0, f_nt_prime) * dg1_rod["A_b_in2"]
    else:
        f_nt_prime = min(f_nt_rod, 1.3 * f_nt_rod - (2.00 * f_nt_rod / f_nv_rod_eff) * f_rv_rod)
        cap_tens_inter = n_rods_tens * (max(0.0, f_nt_prime) * dg1_rod["A_b_in2"]) / 2.00

    dcr_shear = v_demand / cap_rods_shear if cap_rods_shear > 0 else 99.0
    dcr_rod_inter = (t_rods_total / cap_tens_inter) if (t_rods_total > 0 and cap_tens_inter > 0) else dcr_rod_tens

    # 4. Stage 3 Base Plate Cantilever Bending Thickness Check (DG1)
    m_cant = max(0.0, 0.5 * (n_in - 0.95 * d_col))
    n_cant = max(0.0, 0.5 * (b_in - 0.80 * bf_col))
    n_prime = 0.25 * math.sqrt(d_col * bf_col)
    q_ratio_dg1 = min(1.0, (4.0 * d_col * bf_col / ((d_col + bf_col) ** 2)) * (p_demand / (f_p_max * a1)) if f_p_max * a1 > 0 else 1.0)
    lam_dg1 = min(1.0, 2.0 * math.sqrt(q_ratio_dg1) / (1.0 + math.sqrt(1.0 - q_ratio_dg1))) if q_ratio_dg1 < 1.0 else 1.0

    # Bearing side plate bending moment per inch width
    if y_brg >= m_cant:
        m_pl_brg = 0.5 * f_p_actual * (m_cant ** 2)
    else:
        m_pl_brg = f_p_actual * y_brg * (m_cant - 0.5 * y_brg)

    # Transverse cantilever n bending: full n when bearing depth Y >= m_cant; limited to min(n, Y) for narrow toe strip
    if y_brg >= m_cant:
        m_pl_n = 0.5 * f_p_actual * (n_cant ** 2)
    else:
        n_eff = min(n_cant, y_brg)
        m_pl_n = 0.5 * f_p_actual * (n_eff ** 2)
    # Tension side anchor-rod bending moment per inch effective width (2*x_t,45 or B/2)
    x_tens = max(0.0, f_dist_in - 0.5 * d_col + 0.5 * tf_col)
    b_eff_tens = min(b_in, max(b_in * 0.5, 2.0 * x_tens))
    m_pl_tens = (t_rods_total * x_tens / b_eff_tens) if (t_rods_total > 0 and b_eff_tens > 0) else 0.0

    m_pl_gov = max(m_pl_brg, m_pl_n, m_pl_tens)
    if method == DesignMethod.LRFD:
        t_req_in = math.sqrt((4.0 * m_pl_gov) / (0.90 * fy_p)) if m_pl_gov > 0 else 0.25
        m_pl_cap_per_in = 0.90 * fy_p * (t_p ** 2) / 4.0
    else:
        t_req_in = math.sqrt((4.0 * m_pl_gov * 1.67) / fy_p) if m_pl_gov > 0 else 0.25
        m_pl_cap_per_in = (fy_p * (t_p ** 2) / 4.0) / 1.67
    dcr_plate_bend = (t_req_in / t_p) ** 2  # Equals M_pl_demand / M_pl_capacity linearly in load!

    # 5. Stage 4 Supporting Pedestal & OSHA 300 lb @ 18 in. Erection Moment Check
    m_osha_kip_in = 0.300 * (0.5 * d_col + 18.0)  # Minimum OSHA 300 lb eccentric erection moment
    m_cap_osha = (n_rods_tens * cap_rod_tens_single * (0.5 * n_in + f_dist_in - 1.0))
    dcr_osha = m_osha_kip_in / m_cap_osha if m_cap_osha > 0 else 99.0

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_BEARING",
            name="Concrete Pedestal Bearing Stress (Sec. J8)",
            code_clause="AISC 360-22 Sec. J8 Eq. J8-2",
            equation_latex=r"f_{p,\max} = \phi_c 0.85 f'_c \sqrt{A_2 / A_1}" if method == DesignMethod.LRFD else r"f_{p,\max} = \frac{0.85 f'_c \sqrt{A_2 / A_1}}{\Omega_c}",
            substitution_str=f"f_p={f_p_actual:.3f} ksi vs f_p,max={f_p_max:.3f} ksi (Y={y_brg:.2f} in.)",
            demand=round(f_p_actual, 3),
            capacity=round(f_p_max, 3),
            units="ksi",
            dcr=round(dcr_bearing, 3),
            status=CalculationStatus.PASS if (dcr_bearing <= 1.0 and not crushed_flag) else CalculationStatus.FAIL,
            notes=f"e={ecc:.2f} in., e_crit={e_crit:.2f} in.",
        ),
        LimitStateResult(
            step_id="S2_RODS",
            name="Anchor Rod Tension & Shear Interaction (DG1)",
            code_clause="AISC DG1 Table 2.3 & Sec. J3.7",
            equation_latex=r"T \leq n_t \cdot T_{cap,\text{rod}}",
            substitution_str=f"T_total={t_rods_total:.2f} kips vs cap={cap_tens_inter:.2f} kips; V={v_demand:.2f} vs {cap_rods_shear:.2f} kips",
            demand=round(t_rods_total, 2),
            capacity=round(cap_tens_inter, 2),
            units="kips",
            dcr=round(max(dcr_rod_inter, dcr_shear), 3),
            status=CalculationStatus.PASS if max(dcr_rod_inter, dcr_shear) <= 1.0 else CalculationStatus.FAIL,
            notes=f"{n_rods_total}x {d_a_in:.3f} in. {rod_grade} (hole d_h={dg1_rod['d_h_oversized_in']:.3f} in.)",
        ),
        LimitStateResult(
            step_id="S3_PLATE",
            name="Base Plate Flexural Yielding Thickness (DG1)",
            code_clause="AISC DG1 Sec. 3",
            equation_latex=r"t_{p,req} = \sqrt{\frac{4 M_{pl}}{\phi_b F_y}}" if method == DesignMethod.LRFD else r"t_{p,req} = \sqrt{\frac{4 \Omega_b M_{pl}}{F_y}}",
            substitution_str=f"M_pl={m_pl_gov:.2f} kip-in./in. vs cap={m_pl_cap_per_in:.2f} (t_req={t_req_in:.3f} <= t_p={t_p:.3f} in.)",
            demand=round(m_pl_gov, 2),
            capacity=round(m_pl_cap_per_in, 2),
            units="kip-in./in.",
            dcr=round(dcr_plate_bend, 3),
            status=CalculationStatus.PASS if t_p >= t_req_in - 1e-6 else CalculationStatus.FAIL,
            notes=f"m={m_cant:.2f} in., n={n_cant:.2f} in., lambda*n'={lam_dg1 * n_prime:.2f} in.",
        ),
        LimitStateResult(
            step_id="S4_OSHA",
            name="Pedestal Confinement & OSHA Erection Stability",
            code_clause="29 CFR 1926.755 & AISC Sec. J8",
            equation_latex=r"M_{OSHA} = 0.30 \text{ kips} \cdot \left(\frac{d}{2} + 18 \text{ in.}\right)",
            substitution_str=f"M_OSHA={m_osha_kip_in:.2f} vs M_cap={m_cap_osha:.2f} kip-in.",
            demand=round(m_osha_kip_in, 2),
            capacity=round(m_cap_osha, 2),
            units="kip-in.",
            dcr=round(dcr_osha, 3),
            status=CalculationStatus.PASS if (osha_rods_ok and dcr_osha <= 1.0) else CalculationStatus.FAIL,
            notes=f"sqrt(A2/A1)={confinement_sqrt:.2f}",
        ),
    ]

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = stage1_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    trace = (
        CalcStep(
            step_id="S1_DG1_OSHA",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Base Plate Geometry, Oversized Hole Washers & OSHA 4-Rod Mandate",
            symbolic=_validated_markup(r"n_{rods} \geq 4, B \geq b_f, N \geq d"),
            substituted=_validated_markup(
                rf"n_{{rods}} = {n_rods_total} \geq 4, B = {b_in:.2f} \text{{ in.}}, N = {n_in:.2f} \text{{ in.}}"
            ),
            variables={
                "B": Quantity("B", b_in, "in.", "Base plate width"),
                "N": Quantity("N", n_in, "in.", "Base plate length"),
                "d_h_ovs": Quantity("d_h", round(dg1_rod["d_h_oversized_in"], 3), "in.", "DG1 oversized anchor hole dia."),
                "t_washer": Quantity("t_w", round(dg1_rod["washer_thick_in"], 3), "in.", "Min square plate washer thickness"),
            },
            result_value=n_rods_total,
            result_unit="rods",
            acceptance=AcceptanceCriterion(">=", 4, "rods", "OSHA 29 CFR 1926.755 & DG1 geometry check", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if stage1_ok else CalculationStatus.FAIL,
            refs=(ref_dg1, ref_shapes, ref_proc),
        ),
        CalcStep(
            step_id="S2_CONC_RODS",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Concrete Bearing Stress Block & Anchor Rod Force Equilibrium",
            symbolic=_validated_markup(
                r"f_{p,\max} = \phi_c 0.85 f'_c \sqrt{\frac{A_2}{A_1}}, T = q_{\max} Y - P"
                if method == DesignMethod.LRFD
                else r"f_{p,\max} = \frac{0.85 f'_c \sqrt{A_2 / A_1}}{\Omega_c}, T = q_{\max} Y - P"
            ),
            substituted=_validated_markup(
                rf"f_{{p,\max}} = {f_p_max:.3f} \text{{ ksi, }} Y = {y_brg:.2f} \text{{ in., }} T = {t_rods_total:.2f} \text{{ kips}}"
            ),
            variables={
                "f_p_max": Quantity("f_{p,\\max}", round(f_p_max, 3), "ksi", f"{method.value} allowable concrete bearing"),
                "Y": Quantity("Y", round(y_brg, 2), "in.", "Concrete bearing length"),
                "T_rods": Quantity("T", round(t_rods_total, 2), "kips", "Required anchor rod group tension"),
                "T_cap": Quantity("T_{cap}", round(cap_tens_inter, 2), "kips", f"{method.value} anchor rod group capacity"),
                "V_cap": Quantity("V_{cap}", round(cap_rods_shear, 2), "kips", f"{method.value} combined shear resistance"),
            },
            result_value=round(f_p_actual, 3),
            result_unit="ksi",
            acceptance=AcceptanceCriterion("<=", round(f_p_max, 3), "ksi", f"{method.value} concrete bearing check", is_dcr_check=True),
            dcr=round(max(dcr_bearing, dcr_rod_inter, dcr_shear), 3),
            status=CalculationStatus.PASS if max(dcr_bearing, dcr_rod_inter, dcr_shear) <= 1.0 and not crushed_flag else CalculationStatus.FAIL,
            refs=(ref_dg1, ref_j3_2, ref_proc),
        ),
        CalcStep(
            step_id="S3_PLATE_BEND",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Base Plate Cantilever Bending Thickness Verification (DG1)",
            symbolic=_validated_markup(
                r"t_{p,req} = \sqrt{\frac{4 M_{pl}}{0.90 F_y}}"
                if method == DesignMethod.LRFD
                else r"t_{p,req} = \sqrt{\frac{4 \cdot 1.67 \cdot M_{pl}}{F_y}}"
            ),
            substituted=_validated_markup(
                rf"t_{{p,req}} = {t_req_in:.3f} \text{{ in.}} \leq t_p = {t_p:.3f} \text{{ in. (}} M_{{pl}} = {m_pl_gov:.2f} \text{{ kip-in./in.)}}"
            ),
            variables={
                "m": Quantity("m", round(m_cant, 2), "in.", "Cantilever bearing projection"),
                "n": Quantity("n", round(n_cant, 2), "in.", "Lateral bearing projection"),
                "M_pl": Quantity("M_{pl}", round(m_pl_gov, 2), "kip-in./in.", "Governing plate unit bending moment"),
                "t_req": Quantity("t_{p,req}", round(t_req_in, 3), "in.", "Minimum required base plate thickness"),
            },
            result_value=round(m_pl_cap_per_in, 2),
            result_unit="kip-in./in.",
            acceptance=AcceptanceCriterion(">=", round(m_pl_gov, 2), "kip-in./in.", f"{method.value} base plate bending check", is_dcr_check=True),
            dcr=round(dcr_plate_bend, 3),
            status=CalculationStatus.PASS if t_p >= t_req_in - 1e-6 else CalculationStatus.FAIL,
            refs=(ref_mat, ref_dg1, ref_proc),
        ),
        CalcStep(
            step_id="S4_CONFINEMENT",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Pedestal Confinement & OSHA Erection Overturning Check",
            symbolic=_validated_markup(r"M_{OSHA} = 0.30 \cdot \left(\frac{d}{2} + 18\right) \leq M_{cap}"),
            substituted=_validated_markup(
                rf"M_{{OSHA}} = {m_osha_kip_in:.2f} \text{{ kip-in.}} \leq M_{{cap}} = {m_cap_osha:.2f} \text{{ kip-in.}}"
            ),
            variables={
                "sqrt_A2_A1": Quantity("\\sqrt{A_2/A_1}", round(confinement_sqrt, 2), "", "Concrete confinement factor"),
                "M_OSHA": Quantity("M_{OSHA}", round(m_osha_kip_in, 2), "kip-in.", "OSHA minimum erection moment"),
                "M_cap": Quantity("M_{cap}", round(m_cap_osha, 2), "kip-in.", "Anchor group erection moment capacity"),
            },
            result_value=round(m_cap_osha, 2),
            result_unit="kip-in.",
            acceptance=AcceptanceCriterion(">=", round(m_osha_kip_in, 2), "kip-in.", "OSHA erection stability check", is_dcr_check=True),
            dcr=round(dcr_osha, 3),
            status=CalculationStatus.PASS if osha_rods_ok and dcr_osha <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_dg1, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not osha_rods_ok:
        warnings.append("OSHA 29 CFR 1926.755 requires at least 4 anchor rods on structural columns.")
    if crushed_flag:
        warnings.append("Base plate concrete bearing equilibrium has no real solution; increase B, N, or f'c.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_base_plate",
        code_edition="AISC 360-22 / Design Guide 1",
        design_method=method,
        input_parameters={
            "column_section": col_section,
            "plate_grade": plate_grade,
            "B_in": b_in,
            "N_in": n_in,
            "t_p_in": t_p,
            "fc_ksi": fc_ksi,
            "ratio_A2_A1": ratio_a2_a1,
            "d_a_in": d_a_in,
            "rod_grade": rod_grade,
            "n_rods_total": n_rods_total,
            "f_dist_in": f_dist_in,
            "P_demand_kips": p_demand,
            "M_demand_kip_in": m_demand,
            "V_demand_kips": v_demand,
        },
        assumptions=[
            "Rigid base plate assumption per AISC Design Guide 1 (2nd Edition).",
            f"DG1 Table 2.3 oversized hole dia. {dg1_rod['d_h_oversized_in']:.3f} in. with {dg1_rod['washer_size']} x {dg1_rod['washer_thick_in']:.3f} in. welded plate washers.",
        ],
        intermediate_results={
            "e_in": round(ecc, 2),
            "e_crit_in": round(e_crit, 2),
            "f_p_max_ksi": round(f_p_max, 3),
            "f_p_actual_ksi": round(f_p_actual, 3),
            "Y_brg_in": round(y_brg, 3),
            "C_comp_kips": round(c_comp, 2),
            "T_rods_kips": round(t_rods_total, 2),
            "t_req_in": round(t_req_in, 3),
            "cap_rods_tens_kips": round(cap_tens_inter, 2),
            "cap_rods_shear_kips": round(cap_rods_shear, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path for r in (ref_proc, ref_dg1, ref_j3_2, ref_shapes, ref_mat) if r.source_path
        ],
        warnings=warnings,
        trace=trace,
    )
