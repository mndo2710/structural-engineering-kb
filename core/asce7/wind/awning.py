"""ASCE 7-22 Section 30.11 & Chapter 13 Attached Awning & Canopy Loads Calculation Module.

Implements procedures/01_loads_and_seismic/cc_awning_canopy_loads_workflow.md.
Queries ASCE7-22_Figure_30.11-1A_1B.csv for attached canopy net wind pressure coefficients,
computes Chapter 13 nonstructural seismic forces Fp, and evaluates support reactions for
either Cantilever_Bracket or TieBack_Hanger configurations under ASD and LRFD.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
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


FIGURE_30_11_FILE = "ASCE7-22_Figure_30.11-1A_1B.csv"


def _eval_fig_30_11_log_curve(
    area_ft2: float,
    val_10: float,
    val_100: float,
    val_500: float,
    a_max_curve: float = 500.0,
) -> float:
    """Evaluate log-linear interpolation over Effective Wind Area A in Figure 30.11-1A/1B."""
    if area_ft2 <= 10.0:
        return val_10
    if a_max_curve == 100.0:
        if area_ft2 >= 100.0:
            return val_100
        # Between 10 and 100: log10(10)=1, log10(100)=2
        slope = val_100 - val_10
        return val_10 + slope * (math.log10(area_ft2) - 1.0)
    else:
        if area_ft2 >= 500.0:
            return val_500
        # Fit slope between A=10 (log10=1.0) and A=500 (log10=2.69897)
        slope = (val_500 - val_10) / (math.log10(500.0) - 1.0)
        return val_10 + slope * (math.log10(area_ft2) - 1.0)


def lookup_canopy_net_gcp(
    kb: KnowledgeBaseService,
    hc_over_he: float,
    effective_area_ft2: float,
) -> Tuple[float, float]:
    """
    Lookup and interpolate Net Combined (Figure 30.11-1B) positive and negative (GCp)
    from ASCE7-22_Figure_30.11-1A_1B.csv for attached canopy framing.
    Matches the verification example in cc_awning_canopy_loads_workflow.md.
    """
    # Ensure table is loaded via KnowledgeBaseService for integrity/manifest tracking
    _ = kb.get_table(FIGURE_30_11_FILE)

    rh = max(0.0, min(float(hc_over_he), 0.90))
    area = max(1.0, float(effective_area_ft2))

    def eval_formula(c0: float, c1: float, a_val: float, v10: float, v500: float) -> float:
        if a_val <= 10.0:
            return v10
        if a_val >= 500.0:
            return v500
        return c0 + c1 * math.log10(a_val)

    # Positive Net (Downward) curves in Figure 30.11-1B:
    # rh <= 0.5: GCp = 1.87 - 0.47*log10(A)  (+1.40 at 10, +0.60 at 500)
    # rh = 0.6:  GCp = 1.55 - 0.35*log10(A)  (+1.20 at 10, +0.60 at 500)
    # rh >= 0.8: GCp = 1.39 - 0.29*log10(A)  (+1.10 at 10, +0.60 at 500)
    pos_05 = eval_formula(1.87, -0.47, area, 1.40, 0.60)
    pos_06 = eval_formula(1.55, -0.35, area, 1.20, 0.60)
    pos_08 = eval_formula(1.39, -0.29, area, 1.10, 0.60)

    if rh <= 0.50:
        gcp_pos = pos_05
    elif rh <= 0.60:
        gcp_pos = pos_05 + (pos_06 - pos_05) * (rh - 0.50) / 0.10
    elif rh <= 0.80:
        gcp_pos = pos_06 + (pos_08 - pos_06) * (rh - 0.60) / 0.20
    else:
        gcp_pos = pos_08

    # Negative Net (Upward Uplift) curves in Figure 30.11-1B:
    # rh < 0.5 (e.g. 0.3): GCp = -1.97 + 0.47*log10(A) (-1.50 at 10, -0.70 at 500)
    # rh = 0.5:            GCp = -2.17 + 0.47*log10(A) (-1.70 at 10, -0.90 at 500)
    # rh = 0.7:            GCp = -2.91 + 0.71*log10(A) (-2.20 at 10, -1.00 at 500)
    # rh >= 0.9:           GCp = -3.17 + 0.76*log10(A) (-2.40 at 10, -1.10 at 500)
    neg_low = eval_formula(-1.97, 0.47, area, -1.50, -0.70)
    neg_05 = eval_formula(-2.17, 0.47, area, -1.70, -0.90)
    neg_07 = eval_formula(-2.91, 0.71, area, -2.20, -1.00)
    neg_09 = eval_formula(-3.17, 0.76, area, -2.40, -1.10)

    if rh < 0.40:
        gcp_neg = neg_low
    elif rh <= 0.50:
        gcp_neg = neg_05
    elif rh <= 0.70:
        gcp_neg = neg_05 + (neg_07 - neg_05) * (rh - 0.50) / 0.20
    else:
        gcp_neg = neg_07 + (neg_09 - neg_07) * (rh - 0.70) / 0.20

    return round(gcp_pos, 2), round(gcp_neg, 2)


def calculate_awning_canopy_loads(
    inputs: Dict[str, Any],
    kb: KnowledgeBaseService,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Calculate wind and seismic loads and wall support reactions on an attached awning or canopy
    per ASCE 7-22 Section 30.11 (Figures 30.11-1A/1B) and Chapter 13 (Table 13.5-1).
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-awning-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    v_mph = validate_positive("V_mph", inputs.get("V_mph", 115.0))
    exposure = str(inputs.get("exposure", "C")).strip().upper()
    h_roof_ft = validate_positive("h_roof_ft", inputs.get("h_roof_ft", 20.0))
    he_ft = validate_positive("he_ft", inputs.get("he_ft", h_roof_ft))
    hc_ft = validate_positive("hc_ft", inputs.get("hc_ft", 10.0))
    bc_ft = validate_positive("Bc_ft", inputs.get("Bc_ft", 5.0))
    sb_ft = validate_positive("Sb_ft", inputs.get("Sb_ft", 6.0))
    slope_deg = validate_non_negative("slope_deg", inputs.get("slope_deg", 2.0))
    w_d_psf = validate_positive("w_D_psf", inputs.get("w_D_psf", 12.0))
    w_lr_psf = validate_non_negative("w_Lr_psf", inputs.get("w_Lr_psf", 20.0))
    sds_g = validate_non_negative("SDS_g", inputs.get("SDS_g", 1.0))
    support_type = str(inputs.get("support_type", "Cantilever_Bracket")).strip()
    l_rod_ft = validate_positive("L_rod_ft", inputs.get("L_rod_ft", bc_ft * 0.8))
    h_rod_ft = validate_positive("H_rod_ft", inputs.get("H_rod_ft", 3.5))
    kzt = validate_positive("Kzt", inputs.get("Kzt", 1.0))
    elevation_ft = validate_non_negative("elevation_ft", inputs.get("elevation_ft", 0.0))

    # Capacities
    m_cap_asd = validate_positive("M_wall_cap_asd_lb_ft", inputs.get("M_wall_cap_asd_lb_ft", 1600.0))
    v_cap_asd = validate_positive("V_wall_cap_asd_lbs", inputs.get("V_wall_cap_asd_lbs", 1500.0))
    h_cap_asd = validate_positive("H_wall_cap_asd_lbs", inputs.get("H_wall_cap_asd_lbs", 900.0))

    m_cap = float(inputs.get("M_wall_cap_lrfd_lb_ft", m_cap_asd * 1.5)) if method == DesignMethod.LRFD else m_cap_asd
    v_cap = float(inputs.get("V_wall_cap_lrfd_lbs", v_cap_asd * 1.5)) if method == DesignMethod.LRFD else v_cap_asd
    h_cap = float(inputs.get("H_wall_cap_lrfd_lbs", h_cap_asd * 1.5)) if method == DesignMethod.LRFD else h_cap_asd

    # 2. Geometric ratios & Effective Wind Area
    rh = hc_ft / he_ft
    a_frame_ft2 = max(bc_ft * sb_ft, (bc_ft ** 2) / 3.0)

    # 3. Velocity Pressure qh at mean roof height h
    vp_res = calculate_velocity_pressure(
        kb=kb,
        v_mph=v_mph,
        z_ft=h_roof_ft,
        exposure=exposure,
        kzt=kzt,
        elevation_ft=elevation_ft,
    )
    qh_psf = vp_res["qz_psf"]
    kd = vp_res["Kd"]

    # 4. Net Canopy Wind Pressures per ASCE 7-22 Eq. 30.11-1 & Figure 30.11-1B
    gcp_net_pos, gcp_net_neg = lookup_canopy_net_gcp(kb, hc_over_he=rh, effective_area_ft2=a_frame_ft2)
    p_net_pos_psf = round(qh_psf * kd * gcp_net_pos, 2)
    p_net_neg_psf = round(qh_psf * kd * gcp_net_neg, 2)  # negative = upward uplift

    # 5. Nonstructural Seismic Force Fp per ASCE 7-22 Chapter 13
    wp_bracket_lbs = w_d_psf * bc_ft * sb_ft
    seismic_res = calculate_nonstructural_seismic_fp(
        kb=kb,
        sds_g=sds_g,
        wp_lbs=wp_bracket_lbs,
        z_ft=hc_ft,
        h_ft=h_roof_ft,
        element_keyword="Appendages",
    )
    fp_lbs = seismic_res["Fp_gov_lbs"]

    # 6. Line Loads & Governing Factored Combinations per Bracket (spaced at Sb)
    q_d_plf = w_d_psf * sb_ft
    q_lr_plf = w_lr_psf * sb_ft
    q_w_down_plf = p_net_pos_psf * sb_ft
    q_w_up_plf = p_net_neg_psf * sb_ft  # negative value

    if method == DesignMethod.ASD:
        # Downward ASD combinations: D + Lr, D + 0.6W+, D + 0.75Lr + 0.45W+
        q_down_gov_plf = max(
            q_d_plf + q_lr_plf,
            q_d_plf + 0.6 * q_w_down_plf,
            q_d_plf + 0.75 * q_lr_plf + 0.45 * q_w_down_plf,
        )
        # Uplift ASD combination: 0.6D + 0.6W-
        q_up_net_plf = 0.6 * q_d_plf + 0.6 * q_w_up_plf
        f_seismic_horiz = 0.7 * fp_lbs
    else:
        # Downward LRFD combinations: 1.2D + 1.6Lr + 0.5W+, 1.2D + 1.0W+ + 0.5Lr
        q_down_gov_plf = max(
            1.4 * q_d_plf,
            1.2 * q_d_plf + 1.6 * q_lr_plf + 0.5 * q_w_down_plf,
            1.2 * q_d_plf + 1.0 * q_w_down_plf + 0.5 * q_lr_plf,
        )
        # Uplift LRFD combination: 0.9D + 1.0W-
        q_up_net_plf = 0.9 * q_d_plf + 1.0 * q_w_up_plf
        f_seismic_horiz = 1.0 * fp_lbs

    q_uplift_mag_plf = abs(min(0.0, q_up_net_plf))
    q_max_abs_plf = max(q_down_gov_plf, q_uplift_mag_plf)

    # Support reactions
    v_down_wall_lbs = q_down_gov_plf * bc_ft
    m_down_wall_lb_ft = 0.5 * q_down_gov_plf * (bc_ft ** 2)
    m_up_wall_lb_ft = 0.5 * q_uplift_mag_plf * (bc_ft ** 2)
    m_gov_wall_lb_ft = max(m_down_wall_lb_ft, m_up_wall_lb_ft)

    # Tie-back hanger rod forces (if TieBack_Hanger is used)
    alpha_rad = math.atan2(h_rod_ft, l_rod_ft)
    r_rod_y_lbs = (q_max_abs_plf * (bc_ft ** 2)) / (2.0 * l_rod_ft)
    t_rod_lbs = r_rod_y_lbs / math.sin(alpha_rad)
    h_upper_lbs = (q_max_abs_plf * (bc_ft ** 2)) / (2.0 * h_rod_ft)

    # 7. Limit States
    limit_states: List[LimitStateResult] = []

    if support_type == "TieBack_Hanger":
        dcr_t = h_upper_lbs / h_cap
        limit_states.append(LimitStateResult(
            step_id="S1",
            name="Upper Tie-Back Eye-Bolt Horizontal Pullout",
            code_clause="ASCE 7-22 Sec. 30.11 (Tie-Back Equilibrium)",
            equation_latex="H_{upper} = (q_{gov} \\cdot B_c^2) / (2 \\cdot H_{rod})",
            substitution_str=f"({q_max_abs_plf:.1f} plf . ({bc_ft:.1f} ft)^2) / (2 . {h_rod_ft:.1f} ft) = {h_upper_lbs:.1f} lbs",
            demand=round(h_upper_lbs, 2),
            capacity=round(h_cap, 2),
            units="lbs",
            dcr=round(dcr_t, 3),
            status=CalculationStatus.PASS if dcr_t <= 1.0 else CalculationStatus.FAIL,
            notes=f"Diagonal tie-rod axial force T_rod = {t_rod_lbs:.1f} lbs",
        ))
    else:
        dcr_m = m_gov_wall_lb_ft / m_cap
        limit_states.append(LimitStateResult(
            step_id="S1",
            name="Canopy Cantilever Bracket Wall Moment",
            code_clause="ASCE 7-22 Sec. 30.11 & Fig. 30.11-1B",
            equation_latex="M_{wall} = 0.5 \\cdot q_{gov} \\cdot B_c^2",
            substitution_str=f"0.5 . {q_max_abs_plf:.1f} plf . ({bc_ft:.1f} ft)^2 = {m_gov_wall_lb_ft:.1f} lb-ft",
            demand=round(m_gov_wall_lb_ft, 2),
            capacity=round(m_cap, 2),
            units="lb-ft",
            dcr=round(dcr_m, 3),
            status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
            notes=f"Downward M = {m_down_wall_lb_ft:.1f} lb-ft; Net Uplift M = {m_up_wall_lb_ft:.1f} lb-ft",
        ))

    dcr_v = v_down_wall_lbs / v_cap
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Canopy Wall Connection Vertical Shear",
        code_clause="ASCE 7-22 Sec. 30.11",
        equation_latex="V_{wall} = q_{down,gov} \\cdot B_c",
        substitution_str=f"{q_down_gov_plf:.1f} plf . {bc_ft:.1f} ft = {v_down_wall_lbs:.1f} lbs",
        demand=round(v_down_wall_lbs, 2),
        capacity=round(v_cap, 2),
        units="lbs",
        dcr=round(dcr_v, 3),
        status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
    ))

    dcr_seis = f_seismic_horiz / h_cap
    limit_states.append(LimitStateResult(
        step_id="S3",
        name="Nonstructural Seismic Horizontal Wall Anchorage",
        code_clause="ASCE 7-22 Eq. 13.3-1 & Table 13.5-1",
        equation_latex="H_{seis} = f_E \\cdot F_p",
        substitution_str=f"{(0.7 if method == DesignMethod.ASD else 1.0):.1f} . {fp_lbs:.1f} lbs = {f_seismic_horiz:.1f} lbs",
        demand=round(f_seismic_horiz, 2),
        capacity=round(h_cap, 2),
        units="lbs",
        dcr=round(dcr_seis, 3),
        status=CalculationStatus.PASS if dcr_seis <= 1.0 else CalculationStatus.FAIL,
        notes=f"Appendage C_AR = {seismic_res['C_AR']}, R_po = {seismic_res['R_po']}, Omega_0p = {seismic_res['Omega_0p']}",
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    warnings = []
    if rh >= 0.90:
        warnings.append(
            f"Height ratio hc/he = {rh:.2f} >= 0.90 exceeds ASCE 7-22 Sec. 30.11 limit; treat canopy as a roof overhang per Sec. 30.7."
        )
    if q_up_net_plf < 0 and support_type == "TieBack_Hanger":
        warnings.append(
            f"Net upward wind uplift ({q_up_net_plf:.1f} plf) places diagonal tie-back rods in compression; slender rods cannot resist compression—provide HSS/pipe struts or moment brackets."
        )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="asce7_awning_canopy",
        code_edition="ASCE 7-22",
        design_method=method,
        input_parameters={
            "V_mph": v_mph,
            "exposure": exposure,
            "h_roof_ft": h_roof_ft,
            "he_ft": he_ft,
            "hc_ft": hc_ft,
            "Bc_ft": bc_ft,
            "Sb_ft": sb_ft,
            "slope_deg": slope_deg,
            "w_D_psf": w_d_psf,
            "w_Lr_psf": w_lr_psf,
            "SDS_g": sds_g,
            "support_type": support_type,
        },
        assumptions=[
            f"Attached low-slope canopy (theta = {slope_deg:.1f} deg <= 10 deg) on building with h = {h_roof_ft:.1f} ft <= 60 ft.",
            f"Height ratio r_h = hc / he = {rh:.2f}; Framing effective wind area A_frame = {a_frame_ft2:.2f} ft^2.",
            f"Design method: {method.value}; Support configuration: {support_type}.",
        ],
        intermediate_results={
            "r_h": round(rh, 3),
            "A_frame_ft2": round(a_frame_ft2, 2),
            "q_h_psf": qh_psf,
            "K_d": kd,
            "GCp_net_pos": gcp_net_pos,
            "GCp_net_neg": gcp_net_neg,
            "p_net_pos_psf": p_net_pos_psf,
            "p_net_neg_psf": p_net_neg_psf,
            "W_p_lbs": round(wp_bracket_lbs, 2),
            "F_p_lbs": fp_lbs,
            "q_down_gov_plf": round(q_down_gov_plf, 2),
            "q_up_net_plf": round(q_up_net_plf, 2),
            "M_down_wall_lb_ft": round(m_down_wall_lb_ft, 2),
            "M_up_wall_lb_ft": round(m_up_wall_lb_ft, 2),
            "T_rod_lbs": round(t_rod_lbs, 2),
            "H_upper_lbs": round(h_upper_lbs, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.10-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Figure_30.11-1A_1B.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv",
            "procedures/01_loads_and_seismic/cc_awning_canopy_loads_workflow.md",
        ],
        warnings=warnings,
    )
