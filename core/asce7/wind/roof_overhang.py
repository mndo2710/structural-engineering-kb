"""ASCE 7-22 Section 30.7 Roof Overhang C&C Wind Loads Calculation Module.

Implements procedures/01_loads_and_seismic/cc_wind_overhang_workflow.md.
Combines top roof surface negative (GCp) with adjacent wall positive (GCp) acting
upward on the bottom soffit surface per ASCE 7-22 Figure 30.7-1, and evaluates
rafter cantilever moment M_oh and exterior wall hurricane tie uplift reaction R_uplift.
"""

from typing import Any, Dict, List, Optional
import uuid

from core.asce7.wind.c_and_c_pressure import (
    TABLE_C30_3_1_FILE,
    TABLE_C30_3_2_FILE,
    lookup_roof_gcp,
    lookup_wall_gcp,
)
from core.asce7.wind.velocity_pressure import (
    TABLE_26_6_1_FILE,
    TABLE_26_9_1_FILE,
    TABLE_26_10_1_FILE,
    TABLE_26_13_1_FILE,
    _build_ref,
    calculate_velocity_pressure,
    lookup_gcpi,
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


def calculate_roof_overhang_wind(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Calculate roof overhang net uplift wind pressures, cantilever moment at exterior wall bearing,
    and net hurricane tie uplift reaction per ASCE 7-22 Section 30.7 (Figure 30.7-1).
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-overhang-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    v_mph = validate_positive("V_mph", inputs.get("V_mph", 115.0))
    exposure = str(inputs.get("exposure", "C")).strip().upper()
    h_roof_ft = validate_positive("h_roof_ft", inputs.get("h_roof_ft", 20.0))
    l_oh_ft = validate_positive("L_oh_ft", inputs.get("L_oh_ft", 2.5))
    l_back_ft = validate_positive("L_back_ft", inputs.get("L_back_ft", 14.0))
    spacing_ft = validate_positive("spacing_ft", inputs.get("spacing_ft", 2.0))
    roof_slope_deg = validate_non_negative("roof_slope_deg", inputs.get("roof_slope_deg", 15.0))
    roof_zone = str(inputs.get("roof_zone", "Zone 2")).strip()
    enclosure = str(inputs.get("enclosure", "Enclosed")).strip()
    dead_load_psf = validate_non_negative("dead_load_psf", inputs.get("dead_load_psf", 12.0))
    kzt = validate_positive("Kzt", inputs.get("Kzt", 1.0))
    elevation_ft = validate_non_negative("elevation_ft", inputs.get("elevation_ft", 0.0))

    # Member & hurricane tie capacities
    m_cap_asd = validate_positive("M_cap_asd_lb_ft", inputs.get("M_cap_asd_lb_ft", 950.0))
    r_tie_cap_asd = validate_positive("R_tie_cap_asd_lbs", inputs.get("R_tie_cap_asd_lbs", 685.0))

    m_cap = float(inputs.get("M_cap_lrfd_lb_ft", m_cap_asd * 1.5)) if method == DesignMethod.LRFD else m_cap_asd
    r_tie_cap = float(inputs.get("R_tie_cap_lrfd_lbs", r_tie_cap_asd * 1.5)) if method == DesignMethod.LRFD else r_tie_cap_asd

    # 2. Step 4.1: Velocity Pressure qh at mean roof height h
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

    # 3. Step 4.2: Effective Wind Areas (Overhang cantilever vs Full rafter)
    area_oh_ft2 = max(l_oh_ft * spacing_ft, (l_oh_ft ** 2) / 3.0)
    l_total_ft = l_back_ft + l_oh_ft
    area_rafter_ft2 = max(l_total_ft * spacing_ft, (l_total_ft ** 2) / 3.0)

    # 4. Step 4.3: Combined Overhang Pressure Coefficient (GCp)_oh per Section 30.7 & Figure 30.7-1
    # Map Roof Zone 1/2 -> Wall Zone 4; Roof Zone 3 -> Wall Zone 5
    adj_wall_zone = "Zone 5" if "3" in roof_zone else "Zone 4"

    roof_gcp_oh = lookup_roof_gcp(kb, effective_area_ft2=area_oh_ft2, zone=roof_zone, roof_slope_deg=roof_slope_deg)
    wall_gcp_oh = lookup_wall_gcp(kb, effective_area_ft2=area_oh_ft2, zone=adj_wall_zone, roof_slope_deg=roof_slope_deg)
    gcp_oh_net_neg = roof_gcp_oh["GCp_neg"] - wall_gcp_oh["GCp_pos"]

    # Interior span (L_back) uses effective wind area of full rafter and includes internal pressure (+GCpi)
    roof_gcp_main = lookup_roof_gcp(kb, effective_area_ft2=area_rafter_ft2, zone="Zone 1", roof_slope_deg=roof_slope_deg)
    gcpi_pos, _ = lookup_gcpi(kb, enclosure=enclosure)
    gcp_main_net_neg = roof_gcp_main["GCp_neg"] - gcpi_pos

    # 5. Step 4.4: Unfactored Design Wind Pressures (magnitude of uplift in psf, min 16 psf)
    p_oh_uplift_psf = max(abs(qh_psf * kd * gcp_oh_net_neg), 16.0)
    p_main_uplift_psf = max(abs(qh_psf * kd * gcp_main_net_neg), 16.0)

    # 6. Step 4.5: Factored Rafter Cantilever Moment & Hurricane Tie Uplift Reaction
    # ASD Uplift Combo 7: 0.6W - 0.6D; LRFD Uplift Combo 5: 1.0W - 0.9D
    f_w = 0.6 if method == DesignMethod.ASD else 1.0
    f_d = 0.6 if method == DesignMethod.ASD else 0.9

    w_d_plf = dead_load_psf * spacing_ft
    w_w_oh_plf = p_oh_uplift_psf * spacing_ft
    w_w_main_plf = p_main_uplift_psf * spacing_ft

    w_net_oh_plf = max(0.0, f_w * w_w_oh_plf - f_d * w_d_plf)
    w_net_main_plf = max(0.0, f_w * w_w_main_plf - f_d * w_d_plf)

    m_oh_factored_lb_ft = 0.5 * w_net_oh_plf * (l_oh_ft ** 2)
    r_uplift_factored_lbs = (
        0.5 * w_net_main_plf * l_back_ft
        + w_net_oh_plf * l_oh_ft * (1.0 + l_oh_ft / (2.0 * l_back_ft))
    )

    # 7. Build Limit States
    limit_states: List[LimitStateResult] = []

    dcr_tie = r_uplift_factored_lbs / r_tie_cap
    limit_states.append(LimitStateResult(
        step_id="S1",
        name="Rafter-to-Wall Hurricane Tie Uplift",
        code_clause="ASCE 7-22 Sec. 30.7 & Fig. 30.7-1",
        equation_latex="R_{uplift} = 0.5 \\cdot w_{net,main} \\cdot L_{back} + w_{net,oh} \\cdot L_{oh} \\cdot (1 + L_{oh}/(2 L_{back}))",
        substitution_str=(
            f"0.5 . {w_net_main_plf:.1f} . {l_back_ft:.1f} + {w_net_oh_plf:.1f} . {l_oh_ft:.1f} . "
            f"(1 + {l_oh_ft:.1f}/(2 . {l_back_ft:.1f})) = {r_uplift_factored_lbs:.1f} lbs"
        ),
        demand=round(r_uplift_factored_lbs, 2),
        capacity=round(r_tie_cap, 2),
        units="lbs",
        dcr=round(dcr_tie, 3),
        status=CalculationStatus.PASS if dcr_tie <= 1.0 else CalculationStatus.FAIL,
        notes=f"Net uplift combination ({f_w:.1f}W - {f_d:.1f}D) at exterior top plate",
    ))

    dcr_m = m_oh_factored_lb_ft / m_cap
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Overhang Cantilever Bending at Wall Plate",
        code_clause="ASCE 7-22 Sec. 30.7",
        equation_latex="M_{oh} = 0.5 \\cdot w_{net,oh} \\cdot L_{oh}^2",
        substitution_str=f"0.5 . {w_net_oh_plf:.1f} plf . ({l_oh_ft:.2f} ft)^2 = {m_oh_factored_lb_ft:.1f} lb-ft",
        demand=round(m_oh_factored_lb_ft, 2),
        capacity=round(m_cap, 2),
        units="lb-ft",
        dcr=round(dcr_m, 3),
        status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
        notes="Check reduced section modulus at birdsmouth notch per NDS Sec. 3.4.3",
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    ref_proc = _build_ref(
        kb, "ASCE 7-22", "2022", "procedure", "Roof Overhang Wind Procedure",
        identifier="cc_wind_overhang_workflow.md",
        fallback_path="procedures/01_loads_and_seismic/cc_wind_overhang_workflow.md",
    )
    ref_t26_6 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.6-1", identifier=TABLE_26_6_1_FILE)
    ref_t26_9 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.9-1", identifier=TABLE_26_9_1_FILE)
    ref_t26_10 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.10-1", identifier=TABLE_26_10_1_FILE)
    ref_t26_13 = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table 26.13-1", identifier=TABLE_26_13_1_FILE)
    ref_wall = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table C30.3-1", identifier=TABLE_C30_3_1_FILE)
    ref_roof = _build_ref(kb, "ASCE 7-22", "2022", "table", "Table C30.3-2 / C30.3-3", identifier=TABLE_C30_3_2_FILE)
    ref_combos = _build_ref(
        kb, "ASCE 7-22", "2022", "table",
        "Table 2.4-1" if method == DesignMethod.ASD else "Table 2.3-1",
        identifier="ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv",
    )

    trace = (
        CalcStep(
            step_id="S1_AREA",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Overhang & Full Rafter Effective Wind Areas",
            symbolic=r"A_{oh} = \max\left(L_{oh} \cdot s, \frac{L_{oh}^2}{3}\right)",
            substituted=rf"\max\left({l_oh_ft:.2f} \cdot {spacing_ft:.2f}, \frac{{{l_oh_ft:.2f}^2}}{{3}}\right) = {area_oh_ft2:.2f} \text{{ ft}}^2",
            variables={
                "L_oh": Quantity("L_{oh}", l_oh_ft, "ft", "Overhang cantilever length"),
                "L_back": Quantity("L_{back}", l_back_ft, "ft", "Interior rafter backspan"),
                "s": Quantity("s", spacing_ft, "ft", "Rafter spacing"),
                "A_oh": Quantity("A_{oh}", round(area_oh_ft2, 2), "ft^2", "Overhang effective wind area"),
                "A_rafter": Quantity("A_{rafter}", round(area_rafter_ft2, 2), "ft^2", "Full rafter effective wind area"),
            },
            result_value=round(area_oh_ft2, 2),
            result_unit="ft^2",
            acceptance=AcceptanceCriterion("info", description="ASCE 7-22 Sec. 26.2 effective wind area", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(RefSpec("ASCE 7-22", "2022", "section", "Sec. 26.2 & Sec. 30.7"), ref_proc),
        ),
        CalcStep(
            step_id="S2_QH",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Velocity Pressure at Mean Roof Height",
            symbolic=r"q_h = 0.00256 \cdot K_h \cdot K_{zt} \cdot K_e \cdot V^2",
            substituted=rf"0.00256 \cdot {vp_res['Kz']:.2f} \cdot {kzt:.2f} \cdot {vp_res['Ke']:.2f} \cdot {v_mph:.1f}^2 = {qh_psf:.2f} \text{{ psf}}",
            variables={
                "K_h": Quantity("K_h", vp_res["Kz"], "", "Exposure coefficient at mean roof height"),
                "K_d": Quantity("K_d", kd, "", "Wind directionality factor"),
                "V": Quantity("V", v_mph, "mph", "Basic wind speed"),
            },
            result_value=qh_psf,
            result_unit="psf",
            acceptance=AcceptanceCriterion("info", description="ASCE 7-22 Eq. 26.10-1 velocity pressure", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(RefSpec("ASCE 7-22", "2022", "equation", "Eq. 26.10-1"), ref_t26_10, ref_t26_9, ref_t26_6),
        ),
        CalcStep(
            step_id="S2_POH",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Combined Overhang & Main Roof Uplift Pressures",
            symbolic=r"p_{oh} = \max\left(|q_h \cdot K_d \cdot ((GC_p)_{roof}^- - (GC_p)_{wall}^+)|, 16.0\right)",
            substituted=rf"\max\left(|{qh_psf:.2f} \cdot {kd:.2f} \cdot ({roof_gcp_oh['GCp_neg']:.2f} - {wall_gcp_oh['GCp_pos']:.2f})|, 16.00\right) = {p_oh_uplift_psf:.2f} \text{{ psf}}",
            variables={
                "GCp_oh_net": Quantity("(GC_p)_{oh,net}^-", round(gcp_oh_net_neg, 4), "", "Combined overhang pressure coefficient"),
                "GCp_main_net": Quantity("(GC_p)_{main,net}^-", round(gcp_main_net_neg, 4), "", "Main span net pressure coefficient"),
                "p_oh": Quantity("p_{oh}", round(p_oh_uplift_psf, 2), "psf", "Overhang uplift pressure"),
                "p_main": Quantity("p_{main}", round(p_main_uplift_psf, 2), "psf", "Main roof uplift pressure"),
            },
            result_value=round(p_oh_uplift_psf, 2),
            result_unit="psf",
            acceptance=AcceptanceCriterion(">=", 16.0, "psf", "ASCE 7-22 Sec. 30.2.2 minimum C&C pressure", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(RefSpec("ASCE 7-22", "2022", "figure", "Sec. 30.7 & Fig. 30.7-1"), ref_roof, ref_wall, ref_t26_13),
        ),
        CalcStep(
            step_id="S3_MOH",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Overhang Cantilever Bending at Wall Plate",
            symbolic=r"M_{oh} = 0.5 \cdot w_{net,oh} \cdot L_{oh}^2",
            substituted=rf"0.5 \cdot {w_net_oh_plf:.2f} \cdot {l_oh_ft:.2f}^2 = {m_oh_factored_lb_ft:.2f} \text{{ lb-ft}}",
            variables={
                "w_net_oh": Quantity("w_{net,oh}", round(w_net_oh_plf, 2), "plf", "Factored net overhang uplift line load"),
                "M_cap": Quantity("M_{cap}", round(m_cap, 2), "lb-ft", f"{method.value} rafter flexural capacity"),
            },
            result_value=round(m_oh_factored_lb_ft, 2),
            result_unit="lb-ft",
            acceptance=AcceptanceCriterion("<=", round(m_cap, 2), "lb-ft", f"{method.value} rafter cantilever moment capacity", is_dcr_check=True),
            dcr=round(dcr_m, 3),
            status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("ASCE 7-22", "2022", "section", "Sec. 30.7"), ref_combos, ref_proc),
        ),
        CalcStep(
            step_id="S4_TIE",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Rafter-to-Wall Hurricane Tie Uplift",
            symbolic=r"R_{uplift} = 0.5 \cdot w_{net,main} \cdot L_{back} + w_{net,oh} \cdot L_{oh} \cdot \left(1 + \frac{L_{oh}}{2 \cdot L_{back}}\right)",
            substituted=rf"0.5 \cdot {w_net_main_plf:.1f} \cdot {l_back_ft:.1f} + {w_net_oh_plf:.1f} \cdot {l_oh_ft:.1f} \cdot \left(1 + \frac{{{l_oh_ft:.1f}}}{{2 \cdot {l_back_ft:.1f}}}\right) = {r_uplift_factored_lbs:.2f} \text{{ lbs}}",
            variables={
                "w_net_main": Quantity("w_{net,main}", round(w_net_main_plf, 2), "plf", "Factored net main-span uplift line load"),
                "R_tie_cap": Quantity("R_{tie,cap}", round(r_tie_cap, 2), "lbs", f"{method.value} hurricane tie uplift capacity"),
            },
            result_value=round(r_uplift_factored_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("<=", round(r_tie_cap, 2), "lbs", f"{method.value} hurricane tie uplift capacity", is_dcr_check=True),
            dcr=round(dcr_tie, 3),
            status=CalculationStatus.PASS if dcr_tie <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("ASCE 7-22", "2022", "figure", "Sec. 30.7 & Fig. 30.7-1"), ref_combos, ref_proc),
        ),
    )

    warnings = []
    if r_uplift_factored_lbs > 150.0:
        warnings.append(
            f"Net uplift R_uplift = {r_uplift_factored_lbs:.0f} lbs > 150 lbs: Toe-nails alone are prohibited; provide rated metal hurricane tie (e.g., Simpson H2.5A, H1, or H10A)."
        )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="asce7_roof_overhang",
        code_edition="ASCE 7-22",
        design_method=method,
        input_parameters={
            "V_mph": v_mph,
            "exposure": exposure,
            "h_roof_ft": h_roof_ft,
            "L_oh_ft": l_oh_ft,
            "L_back_ft": l_back_ft,
            "spacing_ft": spacing_ft,
            "roof_slope_deg": roof_slope_deg,
            "roof_zone": roof_zone,
            "enclosure": enclosure,
            "dead_load_psf": dead_load_psf,
            "R_tie_cap_lbs": round(r_tie_cap, 2),
            "M_cap_lb_ft": round(m_cap, 2),
        },
        assumptions=[
            f"ASCE 7-22 Section 30.7 (Figure 30.7-1): Overhang underside pressure equals adjacent wall positive pressure ({adj_wall_zone}).",
            f"Overhang effective wind area A_oh = {area_oh_ft2:.2f} ft^2; Full rafter area A_rafter = {area_rafter_ft2:.2f} ft^2.",
            f"Design method: {method.value} ({f_w:.1f}W - {f_d:.1f}D counteracting dead load).",
        ],
        intermediate_results={
            "q_h_psf": qh_psf,
            "K_d": kd,
            "A_oh_ft2": round(area_oh_ft2, 2),
            "A_rafter_ft2": round(area_rafter_ft2, 2),
            "GCp_roof_neg_oh": roof_gcp_oh["GCp_neg"],
            "GCp_wall_pos_soffit": wall_gcp_oh["GCp_pos"],
            "GCp_oh_net_neg": round(gcp_oh_net_neg, 4),
            "GCp_main_net_neg": round(gcp_main_net_neg, 4),
            "p_oh_uplift_psf": round(p_oh_uplift_psf, 2),
            "p_main_uplift_psf": round(p_main_uplift_psf, 2),
            "w_net_oh_plf": round(w_net_oh_plf, 2),
            "w_net_main_plf": round(w_net_main_plf, 2),
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
            "database/asce_7/v7_22/ASCE7-22_Table_26.13-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_C30.3-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_C30.3-2_C30.3-3.csv",
            "procedures/01_loads_and_seismic/cc_wind_overhang_workflow.md",
        ],
        warnings=warnings,
        trace=trace,
    )
