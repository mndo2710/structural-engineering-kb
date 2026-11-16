"""ASCE 7-22 Section 29.4 & Chapter 13/15 Open-Frame Trellis & Pergola Loads Module.

Implements procedures/01_loads_and_seismic/cc_trellis_open_wind_seismic_workflow.md.
Queries ASCE7-22_Figure_29.4-2.csv for open-frame force coefficient Cf,
evaluates horizontal wind drag F_W,horiz, vertical slat uplift, seismic force Fp/Vs,
and cantilevered post base shear and overturning moment demands.
"""

import math
from typing import Any, Dict, List, Optional
import uuid

from app.services.knowledge_base_service import KnowledgeBaseService
from core.asce7.seismic.seismic_loads import calculate_nonstructural_seismic_fp
from core.asce7.wind.velocity_pressure import calculate_velocity_pressure
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


FIGURE_29_4_2_FILE = "ASCE7-22_Figure_29.4-2.csv"


def lookup_open_frame_cf(
    kb: KnowledgeBaseService,
    solidity_ratio_epsilon: float,
    member_shape: str = "Flat-Sided",
    d_sqrt_qz: float = 1.0,
) -> float:
    """
    Lookup Open-Frame Force Coefficient Cf from ASCE7-22_Figure_29.4-2.csv
    based on solidity ratio epsilon = As / Ag and member cross-section shape.
    """
    eps = max(0.0, min(float(solidity_ratio_epsilon), 0.70))
    rows = kb.get_table_as_dicts(FIGURE_29_4_2_FILE)
    is_round = "round" in member_shape.strip().lower()

    for row in rows:
        e_min_str = str(row.get("epsilon_min", "")).strip()
        e_max_str = str(row.get("epsilon_max", "")).strip()
        if not e_min_str or not e_max_str:
            continue
        try:
            e_min = float(e_min_str)
            e_max = float(e_max_str)
        except ValueError:
            continue

        if e_min <= eps <= e_max + 0.001:
            if not is_round:
                return float(row["Cf (Flat-Sided Members)"])
            elif d_sqrt_qz <= 2.5:
                return float(row["Cf (Rounded Members: D*sqrt(qz) <= 2.5)"])
            else:
                return float(row["Cf (Rounded Members: D*sqrt(qz) > 2.5)"])

    return 1.8 if not is_round else 1.3


def calculate_trellis_loads(
    inputs: Dict[str, Any],
    kb: KnowledgeBaseService,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Calculate wind and seismic forces and post base reactions for an open-frame trellis/pergola
    per ASCE 7-22 Section 29.4 (Figure 29.4-2) and Chapter 13/15.
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-trellis-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    v_mph = validate_positive("V_mph", inputs.get("V_mph", 115.0))
    exposure = str(inputs.get("exposure", "C")).strip().upper()
    z_top_ft = validate_positive("z_top_ft", inputs.get("z_top_ft", 10.0))
    hp_ft = validate_positive("Hp_ft", inputs.get("Hp_ft", z_top_ft))
    lt_ft = validate_positive("Lt_ft", inputs.get("Lt_ft", 16.0))
    bt_ft = validate_positive("Bt_ft", inputs.get("Bt_ft", 12.0))
    af_eff_ft2 = validate_positive("Af_eff_ft2", inputs.get("Af_eff_ft2", 28.0))
    epsilon_elev = validate_positive("epsilon_elev", inputs.get("epsilon_elev", 0.18))
    epsilon_plan = validate_non_negative("epsilon_plan", inputs.get("epsilon_plan", 0.25))
    member_shape = str(inputs.get("member_shape", "Flat-Sided")).strip()
    num_posts = int(validate_positive("num_posts", inputs.get("num_posts", 4)))
    w_d_psf = validate_positive("w_D_psf", inputs.get("w_D_psf", 8.0))
    sds_g = validate_non_negative("SDS_g", inputs.get("SDS_g", 1.0))
    support_condition = str(inputs.get("support_condition", "Freestanding")).strip()
    gust_g = validate_positive("G", inputs.get("G", 0.85))
    kzt = validate_positive("Kzt", inputs.get("Kzt", 1.0))
    elevation_ft = validate_non_negative("elevation_ft", inputs.get("elevation_ft", 0.0))

    # Capacities per post base
    m_post_cap_asd = validate_positive("M_post_cap_asd_lb_ft", inputs.get("M_post_cap_asd_lb_ft", 2000.0))
    v_post_cap_asd = validate_positive("V_post_cap_asd_lbs", inputs.get("V_post_cap_asd_lbs", 500.0))

    m_cap = float(inputs.get("M_post_cap_lrfd_lb_ft", m_post_cap_asd * 1.5)) if method == DesignMethod.LRFD else m_post_cap_asd
    v_cap = float(inputs.get("V_post_cap_lrfd_lbs", v_post_cap_asd * 1.5)) if method == DesignMethod.LRFD else v_post_cap_asd

    # 2. Step 1: Velocity pressure qz at trellis height z
    vp_res = calculate_velocity_pressure(
        kb=kb,
        v_mph=v_mph,
        z_ft=z_top_ft,
        exposure=exposure,
        kzt=kzt,
        elevation_ft=elevation_ft,
        structure_type="Open Signs and Single-Plane Open Frames",
    )
    qz_psf = vp_res["qz_psf"]
    kd = vp_res["Kd"]

    # 3. Step 2 & 3: Force Coefficient Cf & Horizontal Wind Drag (ASCE 7-22 Eq. 29.4-1)
    cf = lookup_open_frame_cf(kb, solidity_ratio_epsilon=epsilon_elev, member_shape=member_shape)
    fw_horiz_lbs = qz_psf * kd * gust_g * cf * af_eff_ft2

    # Vertical aerodynamic uplift on horizontal slats
    p_vert_psf = qz_psf * kd * gust_g * 1.5 * epsilon_plan
    fw_vert_lbs = p_vert_psf * lt_ft * bt_ft

    # 4. Step 4: Seismic Lateral Force
    wp_total_lbs = w_d_psf * lt_ft * bt_ft
    if "wall" in support_condition.lower() or "ledger" in support_condition.lower():
        seis = calculate_nonstructural_seismic_fp(
            kb=kb,
            sds_g=sds_g,
            wp_lbs=wp_total_lbs,
            z_ft=z_top_ft,
            h_ft=max(z_top_ft, 15.0),
            element_keyword="Appendages",
        )
        fp_seismic_lbs = seis["Fp_gov_lbs"]
    else:
        # Freestanding cantilevered column system (ASCE 7-22 Table 15.4-2: R = 1.5, Ie = 1.0)
        r_free = float(inputs.get("R_freestanding", 2.5))
        cs = sds_g / r_free
        fp_seismic_lbs = cs * wp_total_lbs

    # 5. Step 5: Factored Post Base Shear & Overturning Moment
    f_w = 0.6 if method == DesignMethod.ASD else 1.0
    f_e = 0.7 if method == DesignMethod.ASD else 1.0

    h_wind_factored = f_w * fw_horiz_lbs
    h_seis_factored = f_e * fp_seismic_lbs
    h_tot_factored = max(h_wind_factored, h_seis_factored)

    v_post_lbs = h_tot_factored / num_posts
    m_base_lb_ft = v_post_lbs * hp_ft

    # 6. Limit States
    limit_states: List[LimitStateResult] = []

    dcr_m = m_base_lb_ft / m_cap
    limit_states.append(LimitStateResult(
        step_id="S1",
        name="Cantilevered Post Base Overturning Moment",
        code_clause="ASCE 7-22 Eq. 29.4-1 & Fig. 29.4-2",
        equation_latex="M_{base} = (\\max(f_W F_{W,horiz}, f_E F_p) / N_p) \\cdot H_p",
        substitution_str=f"({h_tot_factored:.1f} lbs / {num_posts}) . {hp_ft:.1f} ft = {m_base_lb_ft:.1f} lb-ft",
        demand=round(m_base_lb_ft, 2),
        capacity=round(m_cap, 2),
        units="lb-ft",
        dcr=round(dcr_m, 3),
        status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
        notes="Wind governs lateral post design" if h_wind_factored >= h_seis_factored else "Seismic governs lateral post design",
    ))

    dcr_v = v_post_lbs / v_cap
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Post Base Shear per Column",
        code_clause="ASCE 7-22 Sec. 29.4",
        equation_latex="V_{post} = \\max(f_W F_{W,horiz}, f_E F_p) / N_p",
        substitution_str=f"{h_tot_factored:.1f} lbs / {num_posts} = {v_post_lbs:.1f} lbs",
        demand=round(v_post_lbs, 2),
        capacity=round(v_cap, 2),
        units="lbs",
        dcr=round(dcr_v, 3),
        status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    return CalculationResult(
        calculation_id=calc_id,
        module_id="asce7_trellis_loads",
        code_edition="ASCE 7-22",
        design_method=method,
        input_parameters={
            "V_mph": v_mph,
            "exposure": exposure,
            "z_top_ft": z_top_ft,
            "Hp_ft": hp_ft,
            "Lt_ft": lt_ft,
            "Bt_ft": bt_ft,
            "Af_eff_ft2": af_eff_ft2,
            "epsilon_elev": epsilon_elev,
            "epsilon_plan": epsilon_plan,
            "member_shape": member_shape,
            "num_posts": num_posts,
            "w_D_psf": w_d_psf,
            "SDS_g": sds_g,
            "support_condition": support_condition,
        },
        assumptions=[
            f"Open-frame trellis/pergola ({member_shape} members), elevation solidity ratio epsilon = {epsilon_elev:.2f}.",
            f"Rigid open structure Gust Effect Factor G = {gust_g:.2f}, Wind Directionality Factor Kd = {kd:.2f}.",
            f"Design method: {method.value} ({f_w:.1f}W vs. {f_e:.1f}E across {num_posts} posts).",
        ],
        intermediate_results={
            "q_z_psf": qz_psf,
            "K_d": kd,
            "G": gust_g,
            "C_f": cf,
            "F_W_horiz_lbs": round(fw_horiz_lbs, 2),
            "F_W_vert_lbs": round(fw_vert_lbs, 2),
            "W_p_total_lbs": round(wp_total_lbs, 2),
            "F_p_seismic_lbs": round(fp_seismic_lbs, 2),
            "H_wind_factored_lbs": round(h_wind_factored, 2),
            "H_seis_factored_lbs": round(h_seis_factored, 2),
            "V_post_lbs": round(v_post_lbs, 2),
            "M_base_lb_ft": round(m_base_lb_ft, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/asce_7/v7_22/ASCE7-22_Figure_29.4-2.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.10-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv",
            "procedures/01_loads_and_seismic/cc_trellis_open_wind_seismic_workflow.md",
        ],
        warnings=[
            "Detailing Note: Post base anchors resisting overturning moment M_base must have positive mechanical anchorage or embedded socket depth; standard non-moment standoff bases cannot resist freestanding cantilever overturning."
        ],
    )
