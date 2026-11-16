"""ASCE 7-22 Section 27.3.4 & Section 30.9 Parapet Wind Loads Calculation Module.

Implements procedures/01_loads_and_seismic/cc_wind_parapet_workflow.md.
Evaluates MWFRS and C&C wind pressures (Windward Case A and Leeward Case B),
cantilever parapet stud base shear V_base, base moment M_base, and continuous
balloon-stud roof diaphragm reaction R_roof under ASD or LRFD.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.services.knowledge_base_service import KnowledgeBaseService
from core.asce7.wind.c_and_c_pressure import lookup_roof_gcp, lookup_wall_gcp
from core.asce7.wind.velocity_pressure import calculate_velocity_pressure, lookup_gcpi
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


def calculate_parapet_wind(
    inputs: Dict[str, Any],
    kb: KnowledgeBaseService,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Calculate MWFRS & C&C wind pressures and cantilever base demands on a building parapet
    per ASCE 7-22 Sections 26.10, 27.3.4, and 30.9 (Figure 30.9-1).
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-parapet-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    v_mph = validate_positive("V_mph", inputs.get("V_mph", 115.0))
    exposure = str(inputs.get("exposure", "C")).strip().upper()
    h_roof_ft = validate_positive("h_roof_ft", inputs.get("h_roof_ft", 25.0))
    h_par_ft = validate_positive("h_par_ft", inputs.get("h_par_ft", 3.5))
    spacing_ft = validate_positive("spacing_ft", inputs.get("spacing_ft", 1.3333))
    roof_slope_deg = validate_non_negative("roof_slope_deg", inputs.get("roof_slope_deg", 5.0))
    kzt = validate_positive("Kzt", inputs.get("Kzt", 1.0))
    elevation_ft = validate_non_negative("elevation_ft", inputs.get("elevation_ft", 0.0))
    wall_zone = str(inputs.get("wall_zone", "Zone 5")).strip()
    roof_zone = str(inputs.get("roof_zone", "Zone 3")).strip()
    enclosure = str(inputs.get("enclosure", "Enclosed")).strip()
    backspan_ft = validate_positive("backspan_ft", inputs.get("backspan_ft", 10.0))

    # Member / connection capacities (for limit-state DCR evaluation)
    m_cap_asd = validate_positive("M_cap_asd_lb_ft", inputs.get("M_cap_asd_lb_ft", 650.0))
    v_cap_asd = validate_positive("V_cap_asd_lbs", inputs.get("V_cap_asd_lbs", 450.0))
    r_cap_asd = validate_positive("R_cap_asd_lbs", inputs.get("R_cap_asd_lbs", 600.0))

    # Scale capacities if LRFD is selected and explicit LRFD capacities are not provided
    m_cap = float(inputs.get("M_cap_lrfd_lb_ft", m_cap_asd * 1.5)) if method == DesignMethod.LRFD else m_cap_asd
    v_cap = float(inputs.get("V_cap_lrfd_lbs", v_cap_asd * 1.5)) if method == DesignMethod.LRFD else v_cap_asd
    r_cap = float(inputs.get("R_cap_lrfd_lbs", r_cap_asd * 1.5)) if method == DesignMethod.LRFD else r_cap_asd

    # 2. Step 4.1: Effective Wind Area (A)
    hp_ft = h_roof_ft + h_par_ft
    b_eff_ft = max(spacing_ft, h_par_ft / 3.0)
    area_eff_ft2 = h_par_ft * b_eff_ft

    # 3. Step 4.2: Velocity Pressure at Top of Parapet (qp)
    vp_res = calculate_velocity_pressure(
        kb=kb,
        v_mph=v_mph,
        z_ft=hp_ft,
        exposure=exposure,
        kzt=kzt,
        elevation_ft=elevation_ft,
        structure_type="Components and Cladding",
    )
    qp_psf = vp_res["qz_psf"]
    kd = vp_res["Kd"]
    kp = vp_res["Kz"]
    ke = vp_res["Ke"]

    # 4. Step 4.3: MWFRS Parapet Pressure (pp) per ASCE 7-22 Eq. 27.3-4
    gcpn_windward = 1.5
    gcpn_leeward = -1.0
    pp_windward_psf = qp_psf * kd * gcpn_windward
    pp_leeward_psf = qp_psf * kd * gcpn_leeward

    # 5. Step 4.4: C&C Parapet Pressures per ASCE 7-22 Section 30.9 (Eq. 30.9-1)
    wall_gcp = lookup_wall_gcp(kb, effective_area_ft2=area_eff_ft2, zone=wall_zone, roof_slope_deg=roof_slope_deg)
    roof_gcp = lookup_roof_gcp(
        kb,
        effective_area_ft2=area_eff_ft2,
        zone=roof_zone,
        roof_slope_deg=roof_slope_deg,
        parapet_height_ft=h_par_ft,
    )
    gcpi_pos, gcpi_neg = lookup_gcpi(kb, enclosure=enclosure)

    # Case A (Windward Parapet): Front wall positive + Back roof negative
    gcp_wall_pos = wall_gcp["GCp_pos"]
    gcp_roof_neg = roof_gcp["GCp_neg"]
    p_net_a_psf = qp_psf * kd * (abs(gcp_wall_pos) + abs(gcp_roof_neg))

    # Case B (Leeward Parapet): Front wall negative + Back roof positive
    gcp_wall_neg = wall_gcp["GCp_neg"]
    gcp_roof_pos = roof_gcp["GCp_pos"]
    p_net_b_psf = qp_psf * kd * (abs(gcp_wall_neg) + abs(gcp_roof_pos))

    # Cladding single-surface pressure check (including internal cavity GCpi)
    p_cladding_max_psf = qp_psf * kd * ( max(abs(gcp_wall_neg), abs(gcp_roof_neg)) + abs(gcpi_pos) )

    # Minimum C&C pressure 16.0 psf per ASCE 7-22 Section 30.2.2
    p_gov_unfactored_psf = max(p_net_a_psf, p_net_b_psf, 16.0)

    # 6. Step 4.5: Factored Cantilever Base Shear, Moment & Backspan Reaction
    wind_factor = 0.6 if method == DesignMethod.ASD else 1.0
    w_factored_plf = wind_factor * p_gov_unfactored_psf * spacing_ft
    v_base_lbs = w_factored_plf * h_par_ft
    m_base_lb_ft = 0.5 * w_factored_plf * (h_par_ft ** 2)
    r_roof_lbs = v_base_lbs * (1.0 + h_par_ft / (2.0 * backspan_ft))

    # 7. Build Limit States
    limit_states: List[LimitStateResult] = []

    dcr_m = m_base_lb_ft / m_cap
    limit_states.append(LimitStateResult(
        step_id="S1",
        name="Parapet Cantilever Base Moment",
        code_clause="ASCE 7-22 Sec. 30.9 & Sec. 2.4.1" if method == DesignMethod.ASD else "ASCE 7-22 Sec. 30.9 & Sec. 2.3.1",
        equation_latex="M_{base} = 0.5 \\cdot (f_W \\cdot p_{gov} \\cdot s) \\cdot h_{par}^2",
        substitution_str=f"0.5 . ({wind_factor:.1f} . {p_gov_unfactored_psf:.2f} psf . {spacing_ft:.2f} ft) . ({h_par_ft:.2f} ft)^2 = {m_base_lb_ft:.1f} lb-ft",
        demand=round(m_base_lb_ft, 2),
        capacity=round(m_cap, 2),
        units="lb-ft",
        dcr=round(dcr_m, 3),
        status=CalculationStatus.PASS if dcr_m <= 1.0 else CalculationStatus.FAIL,
        notes="Governing C&C Case A (Windward Inward Bending)" if p_net_a_psf >= p_net_b_psf else "Governing C&C Case B",
    ))

    dcr_v = v_base_lbs / v_cap
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Parapet Cantilever Base Shear",
        code_clause="ASCE 7-22 Eq. 30.9-1",
        equation_latex="V_{base} = (f_W \\cdot p_{gov} \\cdot s) \\cdot h_{par}",
        substitution_str=f"({wind_factor:.1f} . {p_gov_unfactored_psf:.2f} psf . {spacing_ft:.2f} ft) . {h_par_ft:.2f} ft = {v_base_lbs:.1f} lbs",
        demand=round(v_base_lbs, 2),
        capacity=round(v_cap, 2),
        units="lbs",
        dcr=round(dcr_v, 3),
        status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
        notes="Horizontal shear at roof diaphragm attachment line",
    ))

    dcr_r = r_roof_lbs / r_cap
    limit_states.append(LimitStateResult(
        step_id="S3",
        name="Balloon-Stud Roof Diaphragm Reaction",
        code_clause="ASCE 7-22 Sec. 30.9 (Continuous Stud)",
        equation_latex="R_{roof} = V_{base} \\cdot (1 + h_{par} / (2 \\cdot L_{back}))",
        substitution_str=f"{v_base_lbs:.1f} lbs . (1 + {h_par_ft:.2f} / (2 . {backspan_ft:.2f})) = {r_roof_lbs:.1f} lbs",
        demand=round(r_roof_lbs, 2),
        capacity=round(r_cap, 2),
        units="lbs",
        dcr=round(dcr_r, 3),
        status=CalculationStatus.PASS if dcr_r <= 1.0 else CalculationStatus.FAIL,
        notes="Reaction at roof framing connection for continuous balloon stud",
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    warnings: List[str] = []
    if h_par_ft >= 3.0 and roof_slope_deg <= 7.0 and "3" in roof_zone:
        warnings.append(
            "Parapet height h_par >= 3.0 ft on low-slope roof (theta <= 7 deg): Roof Zone 3 negative (GCp) reduced to Zone 2 per Figure 30.3-2A Note 5."
        )
    warnings.append(
        "Detailing Note: Never splice parapet studs at the roof line without a dedicated moment connection or continuous balloon stud extending >= 2*h_par below the roof diaphragm."
    )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="asce7_parapet_wind",
        code_edition="ASCE 7-22",
        design_method=method,
        input_parameters={
            "V_mph": v_mph,
            "exposure": exposure,
            "h_roof_ft": h_roof_ft,
            "h_par_ft": h_par_ft,
            "spacing_ft": round(spacing_ft, 3),
            "roof_slope_deg": roof_slope_deg,
            "wall_zone": wall_gcp["zone"],
            "roof_zone": roof_gcp["zone"],
            "enclosure": enclosure,
            "backspan_ft": backspan_ft,
            "Kzt": kzt,
            "elevation_ft": elevation_ft,
            "M_cap_lb_ft": round(m_cap, 2),
            "V_cap_lbs": round(v_cap, 2),
            "R_cap_lbs": round(r_cap, 2),
        },
        assumptions=[
            f"Low-rise building (h = {h_roof_ft:.1f} ft <= 60 ft), Exposure {exposure}, enclosed cavity internal pressure cancels across dual-sheathed framing stud.",
            f"Top of parapet height h_p = h + h_par = {hp_ft:.2f} ft; Effective wind area A = {area_eff_ft2:.2f} ft^2.",
            f"Design method: {method.value} (wind load factor = {wind_factor:.1f}W).",
        ],
        intermediate_results={
            "h_p_ft": round(hp_ft, 2),
            "A_eff_ft2": round(area_eff_ft2, 2),
            "K_p": kp,
            "K_d": kd,
            "K_e": ke,
            "q_p_psf": qp_psf,
            "p_p_MWFRS_windward_psf": round(pp_windward_psf, 2),
            "p_p_MWFRS_leeward_psf": round(pp_leeward_psf, 2),
            "GCp_wall_pos": gcp_wall_pos,
            "GCp_wall_neg": gcp_wall_neg,
            "GCp_roof_pos": gcp_roof_pos,
            "GCp_roof_neg": gcp_roof_neg,
            "p_net_CaseA_psf": round(p_net_a_psf, 2),
            "p_net_CaseB_psf": round(p_net_b_psf, 2),
            "p_cladding_max_psf": round(p_cladding_max_psf, 2),
            "p_gov_unfactored_psf": round(p_gov_unfactored_psf, 2),
            "w_factored_plf": round(w_factored_plf, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/asce_7/v7_22/ASCE7-22_Table_26.6-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.9-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.10-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_26.13-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_C30.3-1.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_C30.3-2_C30.3-3.csv",
            "procedures/01_loads_and_seismic/cc_wind_parapet_workflow.md",
        ],
        warnings=warnings,
    )
