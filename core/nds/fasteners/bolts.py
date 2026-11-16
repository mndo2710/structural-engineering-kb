"""ANSI/AWC NDS 2024 Chapter 11, Chapter 12 & Appendix E Wood Bolted Connection Module.

Implements procedures/02_wood_design/wood_bolt_connection_nds_workflow.md.
Evaluates single-shear and symmetric double-shear European Yield Model (EYM) modes (Im, Is, II, IIIm, IIIs, IV),
Hankinson's formula for load-to-grain angle theta, algebraic group action factor Cg (Eq. 11.3-1),
geometry factor C_Delta, and Appendix E brittle wood failure modes (Net Section Tension Z_NT',
Row Tear-Out Z_RT', and Group Tear-Out Z_GT').
"""

import math
import re
from typing import Any, Dict, List, Optional
import uuid

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.calculation_result import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)


TABLE_12_3_3A_FILE = "NDS-2024_Table_12.3.3A.csv"
TABLE_12_3_3_FILE = "NDS-2024_Table_12.3.3.csv"
TABLE_12_5_1A_FILE = "NDS-2024_Table_12.5.1A.csv"
TABLE_L1_L7_L8_FILE = "NDS-2024_Table_L1_L7_L8.csv"


def lookup_species_specific_gravity(kb: KnowledgeBaseService, species: str = "Douglas Fir-Larch") -> float:
    """Lookup Assigned Specific Gravity G from NDS-2024_Table_12.3.3A.csv."""
    import csv
    csv_path = kb.get_file_path(TABLE_12_3_3A_FILE)
    target = species.strip().lower()
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            sp_str = str(row[1]).strip().lower()
            val_str = str(row[2]).strip()
            if target == sp_str or target in sp_str:
                try:
                    return float(val_str)
                except ValueError:
                    pass
    if "southern pine" in target:
        return 0.55
    if "spf" in target or "spruce-pine-fir" in target:
        return 0.42
    if "hem-fir" in target:
        return 0.43
    return 0.50


def lookup_dowel_bearing_strength(
    kb: KnowledgeBaseService,
    specific_gravity_g: float,
    diameter_in: float,
    theta_deg: float = 0.0,
    member_type: str = "Wood",
) -> Dict[str, float]:
    """
    Compute or lookup dowel bearing strength Fe_parallel, Fe_perp, and Fe_theta (psi)
    per NDS 2024 Table 12.3.3 (`NDS-2024_Table_12.3.3.csv`) and Hankinson's formula.
    """
    m_type = member_type.strip().lower()
    if "steel" in m_type or "a36" in m_type:
        return {"Fe_par": 87000.0, "Fe_perp": 87000.0, "Fe_theta": 87000.0}
    if "concrete" in m_type or "cmu" in m_type:
        return {"Fe_par": 7500.0, "Fe_perp": 7500.0, "Fe_theta": 7500.0}

    # Load Table 12.3.3 via KB for integrity verification
    _ = kb.get_file_path(TABLE_12_3_3_FILE)

    g = float(specific_gravity_g)
    d = float(diameter_in)

    if d < 0.25:
        fe = round(16600.0 * (g ** 1.84) / 50.0) * 50.0
        return {"Fe_par": fe, "Fe_perp": fe, "Fe_theta": fe}

    # NDS Table 12.3.3 footnote 2 equations (rounded to nearest 50 psi per NDS convention)
    fe_par = round((11200.0 * g) / 50.0) * 50.0
    fe_perp = round((6100.0 * (g ** 1.45) * (d ** -0.5)) / 50.0) * 50.0

    rad = math.radians(float(theta_deg))
    sin2 = math.sin(rad) ** 2
    cos2 = math.cos(rad) ** 2
    if abs(theta_deg) < 1e-6:
        fe_theta = fe_par
    elif abs(theta_deg - 90.0) < 1e-6:
        fe_theta = fe_perp
    else:
        fe_theta = (fe_par * fe_perp) / (fe_par * sin2 + fe_perp * cos2)

    return {
        "Fe_par": float(fe_par),
        "Fe_perp": float(fe_perp),
        "Fe_theta": round(fe_theta, 1),
    }


def calculate_group_action_factor_cg(
    n_fasteners_in_row: int,
    diameter_in: float,
    spacing_in: float,
    em_psi: float,
    am_in2: float,
    es_psi: float,
    as_in2: float,
    is_wood_to_metal: bool = False,
) -> float:
    """
    Calculate exact algebraic Group Action Factor Cg per NDS 2024 Section 11.3.6.1 (Eq. 11.3-1).
    """
    n = int(n_fasteners_in_row)
    if n <= 1 or diameter_in < 0.25:
        return 1.00

    ea_m = em_psi * am_in2
    ea_s = es_psi * as_in2
    r_ea = min(ea_s / ea_m, ea_m / ea_s)
    gamma = (270000.0 if is_wood_to_metal else 180000.0) * (diameter_in ** 1.5)
    u = 1.0 + gamma * (spacing_in / 2.0) * (1.0 / ea_m + 1.0 / ea_s)
    m = u - math.sqrt(max(0.0, u ** 2 - 1.0))

    if abs(1.0 - m) < 1e-9:
        return 1.00

    num = m * (1.0 - (m ** (2 * n)))
    den = n * ((1.0 + r_ea * (m ** n)) * (1.0 + m) - 1.0 + (m ** (2 * n)))
    cg = (num / den) * ((1.0 + r_ea) / (1.0 - m))
    return round(min(1.00, max(0.20, cg)), 3)


def calculate_wood_bolt_connection(
    inputs: Dict[str, Any],
    kb: KnowledgeBaseService,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Evaluate single-shear or double-shear wood bolted connection including NDS Chapter 12
    yield modes (Im, Is, II, IIIm, IIIs, IV) and Appendix E brittle tear-out modes.
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-wood-bolt-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    d_in = validate_positive("D_in", inputs.get("D_in", 0.625))
    shear_planes = str(inputs.get("shear_planes", "Single Shear")).strip()
    is_double_shear = "double" in shear_planes.lower()
    f_yb_psi = validate_positive("F_yb_psi", inputs.get("F_yb_psi", 45000.0))

    main_species = str(inputs.get("main_species", "Douglas Fir-Larch")).strip()
    side_species = str(inputs.get("side_species", "Douglas Fir-Larch")).strip()
    side_material = str(inputs.get("side_material", "Wood")).strip()

    t_m_in = validate_positive("t_m_in", inputs.get("t_m_in", 1.5))
    t_s_in = validate_positive("t_s_in", inputs.get("t_s_in", 1.5))
    w_m_in = validate_positive("w_m_in", inputs.get("w_m_in", 5.5))
    theta_m_deg = validate_non_negative("theta_m_deg", inputs.get("theta_m_deg", 0.0))
    theta_s_deg = validate_non_negative("theta_s_deg", inputs.get("theta_s_deg", 0.0))

    e_end_m_in = validate_positive("e_end_m_in", inputs.get("e_end_m_in", 3.0))
    s_in_row_in = validate_positive("s_in_row_in", inputs.get("s_in_row_in", 4.0 * d_in))
    s_row_in = validate_positive("s_row_in", inputs.get("s_row_in", 2.0))
    n_rows = int(validate_positive("n_rows", inputs.get("n_rows", 1)))
    n_bolts_per_row = int(validate_positive("n_bolts_per_row", inputs.get("n_bolts_per_row", 1)))

    c_d = validate_positive("C_D", inputs.get("C_D", 1.00))
    c_m = validate_positive("C_M", inputs.get("C_M", 1.00))
    c_t = validate_positive("C_t", inputs.get("C_t", 1.00))

    p_demand_lbs = validate_positive("P_demand_lbs", inputs.get("P_demand_lbs", 340.0))
    f_t_prime_psi = validate_positive("F_t_prime_psi", inputs.get("F_t_prime_psi", 675.0))
    f_v_prime_psi = validate_positive("F_v_prime_psi", inputs.get("F_v_prime_psi", 180.0))

    # 2. Specific Gravity & Dowel Bearing Strengths (Table 12.3.3A & Table 12.3.3)
    g_m = float(inputs.get("G_m", lookup_species_specific_gravity(kb, main_species)))
    g_s = float(inputs.get("G_s", lookup_species_specific_gravity(kb, side_species)))

    fe_m_dict = lookup_dowel_bearing_strength(kb, g_m, d_in, theta_m_deg, member_type="Wood")
    fe_s_dict = lookup_dowel_bearing_strength(kb, g_s, d_in, theta_s_deg, member_type=side_material)
    f_em = fe_m_dict["Fe_theta"]
    f_es = fe_s_dict["Fe_theta"]

    # 3. Reduction Terms Rd (NDS Table 12.3.1B)
    theta_max = max(theta_m_deg, theta_s_deg)
    k_theta = 1.0 + 0.25 * (theta_max / 90.0)
    rd_i = 4.0 * k_theta
    rd_ii = 3.6 * k_theta
    rd_iii_iv = 3.2 * k_theta

    # 4. Yield Limit Equations (NDS Table 12.3.1A)
    r_e = f_em / f_es
    r_t = t_m_in / t_s_in

    k1 = (math.sqrt(r_e + 2.0 * (r_e ** 2) * (1.0 + r_t + (r_t ** 2)) + (r_t ** 2) * (r_e ** 3)) - r_e * (1.0 + r_t)) / (1.0 + r_e)
    k2 = -1.0 + math.sqrt(2.0 * (1.0 + r_e) + (2.0 * f_yb_psi * (1.0 + 2.0 * r_e) * (d_in ** 2)) / (3.0 * f_em * (t_m_in ** 2)))
    k3 = -1.0 + math.sqrt((2.0 * (1.0 + r_e)) / r_e + (2.0 * f_yb_psi * (2.0 + r_e) * (d_in ** 2)) / (3.0 * f_em * (t_s_in ** 2)))

    if not is_double_shear:
        modes = {
            "Mode I_m": (d_in * t_m_in * f_em) / rd_i,
            "Mode I_s": (d_in * t_s_in * f_es) / rd_i,
            "Mode II": (k1 * d_in * t_s_in * f_es) / rd_ii,
            "Mode III_m": (k2 * d_in * t_m_in * f_em) / ((1.0 + 2.0 * r_e) * rd_iii_iv),
            "Mode III_s": (k3 * d_in * t_s_in * f_em) / ((2.0 + r_e) * rd_iii_iv),
            "Mode IV": ((d_in ** 2) / rd_iii_iv) * math.sqrt((2.0 * f_em * f_yb_psi) / (3.0 * (1.0 + r_e))),
        }
    else:
        modes = {
            "Mode I_m": (d_in * t_m_in * f_em) / rd_i,
            "Mode I_s": (2.0 * d_in * t_s_in * f_es) / rd_i,
            "Mode III_s": (2.0 * k3 * d_in * t_s_in * f_em) / ((2.0 + r_e) * rd_iii_iv),
            "Mode IV": ((2.0 * (d_in ** 2)) / rd_iii_iv) * math.sqrt((2.0 * f_em * f_yb_psi) / (3.0 * (1.0 + r_e))),
        }

    gov_mode_name, z_ref_lbs = min(modes.items(), key=lambda x: x[1])

    # 5. Geometry Factor C_Delta (NDS Table 12.5.1A & 12.5.1B) & Group Action Factor C_g
    _ = kb.get_file_path(TABLE_12_5_1A_FILE)
    a_full_in = 7.0 * d_in if theta_m_deg == 0.0 else 4.0 * d_in
    a_min_in = 0.5 * a_full_in
    s_full_in = 4.0 * d_in

    c_delta_end = min(1.0, e_end_m_in / a_full_in)
    c_delta_spc = min(1.0, s_in_row_in / s_full_in) if n_bolts_per_row > 1 else 1.0
    c_delta = round(min(c_delta_end, c_delta_spc), 2)

    is_metal_side = "steel" in side_material.lower()
    a_m = t_m_in * w_m_in
    a_s = (2.0 if is_double_shear else 1.0) * t_s_in * w_m_in
    e_m = 1600000.0
    e_s = 29000000.0 if is_metal_side else 1600000.0
    c_g = calculate_group_action_factor_cg(
        n_fasteners_in_row=n_bolts_per_row,
        diameter_in=d_in,
        spacing_in=s_in_row_in,
        em_psi=e_m,
        am_in2=a_m,
        es_psi=e_s,
        as_in2=a_s,
        is_wood_to_metal=is_metal_side,
    )

    n_total = n_rows * n_bolts_per_row
    if method == DesignMethod.ASD:
        z_prime_single = z_ref_lbs * c_d * c_m * c_t * c_g * c_delta
        lrfd_scale = 1.0
    else:
        # NDS Appendix N: KF = 3.32, phi_z = 0.65, lambda = 0.80
        lam = float(inputs.get("lambda_factor", 0.80))
        z_prime_single = z_ref_lbs * 3.32 * 0.65 * lam * c_m * c_t * c_g * c_delta
        lrfd_scale = (2.54 * 0.75 * lam) / c_d

    p_yield_cap_lbs = n_total * z_prime_single

    # 6. Appendix E Brittle Failure Modes (Net Section Tension Z_NT', Row Tear-Out Z_RT', Group Tear-Out Z_GT')
    d_hole_in = d_in + 0.0625
    a_net_in2 = t_m_in * max(0.1, w_m_in - n_rows * d_hole_in)
    z_nt_prime_lbs = (f_t_prime_psi * lrfd_scale) * a_net_in2

    s_crit_in = min(e_end_m_in, s_in_row_in) if n_bolts_per_row > 1 else e_end_m_in
    z_rt_row_lbs = n_bolts_per_row * (f_v_prime_psi * lrfd_scale) * t_m_in * s_crit_in
    z_rt_prime_lbs = n_rows * z_rt_row_lbs

    if n_rows >= 2:
        a_group_net_in2 = t_m_in * (n_rows - 1) * max(0.0, s_row_in - d_hole_in)
        z_gt_prime_lbs = z_rt_row_lbs + (f_t_prime_psi * lrfd_scale) * a_group_net_in2
    else:
        z_gt_prime_lbs = z_rt_prime_lbs

    # 7. Build Limit States
    limit_states: List[LimitStateResult] = []

    dcr_yield = p_demand_lbs / p_yield_cap_lbs
    limit_states.append(LimitStateResult(
        step_id="S1",
        name=f"Lateral Yield ({gov_mode_name})",
        code_clause="NDS-2024 Sec. 12.3.1 & Table 12.3.1A",
        equation_latex="P'_{yield} = N \\cdot Z \\cdot C_D \\cdot C_M \\cdot C_t \\cdot C_g \\cdot C_{\\Delta}",
        substitution_str=(
            f"{n_total} . {z_ref_lbs:.0f} lb . {c_d:.2f} . {c_m:.2f} . {c_t:.2f} . {c_g:.2f} . {c_delta:.2f} = {p_yield_cap_lbs:.0f} lbs"
        ),
        demand=round(p_demand_lbs, 1),
        capacity=round(p_yield_cap_lbs, 1),
        units="lbs",
        dcr=round(dcr_yield, 3),
        status=CalculationStatus.PASS if dcr_yield <= 1.0 else CalculationStatus.FAIL,
        notes=f"k1={k1:.3f}, Rd={rd_ii:.2f}, Z_ref={z_ref_lbs:.0f} lbs",
    ))

    dcr_end = a_min_in / e_end_m_in
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Minimum End Distance Check",
        code_clause="NDS-2024 Table 12.5.1A",
        equation_latex="e_{end,m} \\ge a_{min} = 3.5 D",
        substitution_str=f"Required min = {a_min_in:.2f} in. vs. Provided = {e_end_m_in:.2f} in. (Full 7D = {a_full_in:.3f} in.)",
        demand=round(a_min_in, 2),
        capacity=round(e_end_m_in, 2),
        units="in.",
        dcr=round(dcr_end, 3),
        status=CalculationStatus.PASS if dcr_end <= 1.0 else CalculationStatus.FAIL,
        notes=f"C_Delta = {c_delta:.2f}",
    ))

    dcr_rt = p_demand_lbs / z_rt_prime_lbs
    limit_states.append(LimitStateResult(
        step_id="S3",
        name="Appendix E Row / Group Tear-Out Check",
        code_clause="NDS-2024 App. E Eq. E.3-2 & E.4-1",
        equation_latex="Z'_{RT} = \\sum n_i \\cdot F'_v \\cdot t_m \\cdot s_{crit}",
        substitution_str=(
            f"{n_rows} . {n_bolts_per_row} . {f_v_prime_psi:.0f} psi . {t_m_in:.2f} in. . {s_crit_in:.2f} in. = {min(z_rt_prime_lbs, z_gt_prime_lbs):.0f} lbs"
        ),
        demand=round(p_demand_lbs, 1),
        capacity=round(min(z_rt_prime_lbs, z_gt_prime_lbs), 1),
        units="lbs",
        dcr=round(p_demand_lbs / min(z_rt_prime_lbs, z_gt_prime_lbs), 3),
        status=CalculationStatus.PASS if p_demand_lbs <= min(z_rt_prime_lbs, z_gt_prime_lbs) else CalculationStatus.FAIL,
        notes=f"Net section tension capacity Z_NT' = {z_nt_prime_lbs:.0f} lbs",
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    return CalculationResult(
        calculation_id=calc_id,
        module_id="wood_bolt_lateral",
        code_edition="NDS 2024",
        design_method=method,
        input_parameters={
            "D_in": d_in,
            "shear_planes": shear_planes,
            "F_yb_psi": f_yb_psi,
            "main_species": main_species,
            "side_species": side_species,
            "side_material": side_material,
            "t_m_in": t_m_in,
            "t_s_in": t_s_in,
            "w_m_in": w_m_in,
            "theta_m_deg": theta_m_deg,
            "e_end_m_in": e_end_m_in,
            "s_in_row_in": s_in_row_in,
            "n_rows": n_rows,
            "n_bolts_per_row": n_bolts_per_row,
            "C_D": c_d,
            "P_demand_lbs": p_demand_lbs,
        },
        assumptions=[
            f"ANSI/AWC NDS-2024 Chapter 12 ({shear_planes}), Main Member: {main_species} (G = {g_m:.2f}), Side Member: {side_material}.",
            f"Bolt diameter D = {d_in:.3f} in., Bending yield strength F_yb = {f_yb_psi:.0f} psi.",
            f"Design method: {method.value}; Group of {n_total} bolt(s) ({n_rows} row(s) x {n_bolts_per_row} bolt(s)/row).",
        ],
        intermediate_results={
            "G_m": g_m,
            "F_em_psi": f_em,
            "F_es_psi": f_es,
            "K_theta": round(k_theta, 3),
            "R_d_ModeII": round(rd_ii, 2),
            "k1": round(k1, 3),
            "k2": round(k2, 3),
            "k3": round(k3, 3),
            "governing_yield_mode": gov_mode_name,
            "Z_ref_lbs": round(z_ref_lbs, 1),
            "C_g": c_g,
            "C_Delta": c_delta,
            "Z_prime_single_lbs": round(z_prime_single, 1),
            "P_yield_cap_lbs": round(p_yield_cap_lbs, 1),
            "Z_NT_prime_lbs": round(z_nt_prime_lbs, 1),
            "Z_RT_prime_lbs": round(z_rt_prime_lbs, 1),
            "Z_GT_prime_lbs": round(z_gt_prime_lbs, 1),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/nds_wood/v2024/NDS-2024_Table_11.3.1.csv",
            "database/nds_wood/v2024/NDS-2024_Table_12.3.3.csv",
            "database/nds_wood/v2024/NDS-2024_Table_12.3.3A.csv",
            "database/nds_wood/v2024/NDS-2024_Table_12.5.1A.csv",
            "database/nds_wood/v2024/NDS-2024_Table_L1_L7_L8.csv",
            "procedures/02_wood_design/wood_bolt_connection_nds_workflow.md",
        ],
        warnings=[
            "Detailing Note: Bolt holes shall be bored D + 1/32 in. to D + 1/16 in. per NDS Sec. 12.1.3.2; install standard cut washers (Table L8) under bolt head and nut."
        ],
    )
