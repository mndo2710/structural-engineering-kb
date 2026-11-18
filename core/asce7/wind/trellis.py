"""ASCE 7-22 Section 29.4 & Chapter 13/15 Open-Frame Trellis & Pergola Loads Module.

Implements procedures/01_loads_and_seismic/cc_trellis_open_wind_seismic_workflow.md.
Queries ASCE7-22_Figure_29.4-2.csv for open-frame force coefficient Cf,
evaluates horizontal wind drag F_W,horiz, vertical slat uplift, seismic force Fp/Vs,
and cantilevered post base shear and overturning moment demands.
"""

import math
from typing import Any, Dict, List, Optional
import uuid

from core.asce7.seismic.seismic_loads import TABLE_13_5_1_FILE, calculate_nonstructural_seismic_fp
from core.asce7.wind.velocity_pressure import (
    TABLE_26_6_1_FILE,
    TABLE_26_10_1_FILE,
    _build_ref,
    calculate_velocity_pressure,
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


FIGURE_29_4_2_FILE = "ASCE7-22_Figure_29.4-2.csv"


def lookup_open_frame_cf(
    kb: ReferenceDataPort,
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
    kb: ReferenceDataPort,
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

    ref_proc = _build_ref(
        kb, "ASCE 7-22", "2022", "procedure", "Open-Frame Trellis Loads Procedure",
        identifier="cc_trellis_open_wind_seismic_workflow.md",
        fallback_path="procedures/01_loads_and_seismic/cc_trellis_open_wind_seismic_workflow.md",
    )
    ref_f29 = _build_ref(kb, "ASCE 7-22", "2022", "figure", "Fig. 29.4-2", identifier=FIGURE_29_4_2_FILE)
    ref_t26_6 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.6-1", identifier=TABLE_26_6_1_FILE)
    ref_t26_10 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.10-1", identifier=TABLE_26_10_1_FILE)
    ref_t13_5 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 13.5-1", identifier=TABLE_13_5_1_FILE)

    if "wall" in support_condition.lower() or "ledger" in support_condition.lower():
        seis_sym = r"F_p = \frac{0.4 \cdot S_{DS} \cdot I_p \cdot W_p \cdot H_f}{R_{\mu}} \cdot \left(\frac{C_{AR}}{R_{po}}\right)"
        seis_sub = rf"F_p = {fp_seismic_lbs:.2f} \text{{ lbs}} \text{{ (Ch. 13 nonstructural)}}"
        seis_refs = (RefSpec("ASCE 7-22", "2022", "equation", "Eq. 13.3-1"), ref_t13_5, ref_proc)
    else:
        seis_sym = r"V_s = \frac{S_{DS}}{R} \cdot W_p"
        seis_sub = rf"\frac{{{sds_g:.2f}}}{{{float(inputs.get('R_freestanding', 2.5)):.2f}}} \cdot {wp_total_lbs:.1f} = {fp_seismic_lbs:.2f} \text{{ lbs}}"
        seis_refs = (RefSpec("ASCE 7-22", "2022", "table", "Table 15.4-2"), ref_proc)

    trace = (
        CalcStep(
            step_id="S1_GEO",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Open-Frame Elevation Solidity & Effective Area",
            symbolic=r"\epsilon_{elev} = \frac{A_s}{A_g} \leq 0.70",
            substituted=rf"\epsilon_{{elev}} = {epsilon_elev:.3f} \leq 0.70, A_{{f,eff}} = {af_eff_ft2:.2f} \text{{ ft}}^2",
            variables={
                "epsilon_elev": Quantity(r"\epsilon_{elev}", epsilon_elev, "ratio", "Elevation solidity ratio"),
                "epsilon_plan": Quantity(r"\epsilon_{plan}", epsilon_plan, "ratio", "Plan slat solidity ratio"),
                "Af_eff": Quantity("A_{f,eff}", af_eff_ft2, "ft^2", "Effective projected solid area"),
                "N_p": Quantity("N_p", num_posts, "", "Number of supporting posts"),
            },
            result_value=round(epsilon_elev, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("<=", 0.70, "ratio", "ASCE 7-22 Fig. 29.4-2 open-frame solidity limit", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if epsilon_elev <= 0.70 else CalculationStatus.REQUIRES_REVIEW,
            refs=(ref_f29, ref_proc),
        ),
        CalcStep(
            step_id="S2_WIND",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Velocity Pressure & Open-Frame Horizontal Wind Drag",
            symbolic=r"F_{W,horiz} = q_z \cdot K_d \cdot G \cdot C_f \cdot A_{f,eff}",
            substituted=rf"{qz_psf:.2f} \cdot {kd:.2f} \cdot {gust_g:.2f} \cdot {cf:.2f} \cdot {af_eff_ft2:.2f} = {fw_horiz_lbs:.2f} \text{{ lbs}}",
            variables={
                "q_z": Quantity("q_z", qz_psf, "psf", "Velocity pressure at trellis height"),
                "K_d": Quantity("K_d", kd, "", "Wind directionality factor"),
                "G": Quantity("G", gust_g, "", "Gust effect factor"),
                "C_f": Quantity("C_f", cf, "", "Open-frame force coefficient"),
                "F_W_vert": Quantity("F_{W,vert}", round(fw_vert_lbs, 2), "lbs", "Total vertical slat uplift"),
            },
            result_value=round(fw_horiz_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("info", description="ASCE 7-22 Eq. 29.4-1 horizontal wind drag", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(RefSpec("ASCE 7-22", "2022", "equation", "Eq. 29.4-1 & Fig. 29.4-2"), ref_f29, ref_t26_6, ref_t26_10),
        ),
        CalcStep(
            step_id="S2_SEIS",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Seismic Lateral Force Evaluation",
            symbolic=seis_sym,
            substituted=seis_sub,
            variables={
                "W_p": Quantity("W_p", round(wp_total_lbs, 2), "lbs", "Total trellis dead weight"),
                "H_wind_f": Quantity("f_W F_{W,horiz}", round(h_wind_factored, 2), "lbs", f"{method.value} factored wind lateral force"),
                "H_seis_f": Quantity("f_E F_p", round(h_seis_factored, 2), "lbs", f"{method.value} factored seismic lateral force"),
            },
            result_value=round(fp_seismic_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("info", description="Unfactored seismic lateral demand", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=seis_refs,
        ),
        CalcStep(
            step_id="S3_SHR",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Post Base Shear per Column",
            symbolic=r"V_{post} = \frac{\max(f_W \cdot F_{W,horiz}, f_E \cdot F_p)}{N_p}",
            substituted=rf"\frac{{{h_tot_factored:.1f}}}{{{num_posts}}} = {v_post_lbs:.2f} \text{{ lbs}}",
            variables={
                "V_cap": Quantity("V_{cap}", round(v_cap, 2), "lbs", f"{method.value} post shear capacity"),
            },
            result_value=round(v_post_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("<=", round(v_cap, 2), "lbs", f"{method.value} post base shear capacity", is_dcr_check=True),
            dcr=round(dcr_v, 3),
            status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("ASCE 7-22", "2022", "section", "Sec. 29.4"), ref_proc),
        ),
        CalcStep(
            step_id="S4_OTM",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Cantilevered Post Base Overturning Moment",
            symbolic=r"M_{base} = V_{post} \cdot H_p",
            substituted=rf"{v_post_lbs:.2f} \cdot {hp_ft:.1f} = {m_base_lb_ft:.2f} \text{{ lb-ft}}",
            variables={
                "H_p": Quantity("H_p", hp_ft, "ft", "Post cantilever height"),
                "M_cap": Quantity("M_{cap}", round(m_cap, 2), "lb-ft", f"{method.value} post base moment capacity"),
            },
            result_value=round(m_base_lb_ft, 2),
            result_unit="lb-ft",
            acceptance=AcceptanceCriterion("<=", round(m_cap, 2), "lb-ft", f"{method.value} post base overturning capacity", is_dcr_check=True),
            dcr=round(dcr_m, 3),
            status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("ASCE 7-22", "2022", "equation", "Eq. 29.4-1 & Fig. 29.4-2"), ref_proc),
            note="Wind governs lateral post design" if h_wind_factored >= h_seis_factored else "Seismic governs lateral post design",
        ),
    )

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
        trace=trace,
    )
