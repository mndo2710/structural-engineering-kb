"""2024 IBC Section 1607.9 / 2025 CBC / ASCE 7-22 Section 4.5.1 Guardrail & Handrail Loads Module.

Implements procedures/01_loads_and_seismic/guardrail_handrail_loads_ibc_workflow.md.
Queries IBC-2024_Section_1607.9_Guardrail_Loads.csv for concentrated (200 lb) and uniform (50 plf)
live loads, evaluates top rail bending/shear, post base shear & overturning moment,
and anchor bolt / tension tie force under ASD and LRFD.
"""

from typing import Any, Dict, List, Optional
import uuid

from core.asce7.wind.velocity_pressure import _build_ref
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


IBC_GUARDRAIL_FILE = "IBC-2024_Section_1607.9_Guardrail_Loads.csv"


def lookup_ibc_guardrail_loads(
    kb: ReferenceDataPort,
    occupancy: str = "R-3_Residential",
) -> Dict[str, float]:
    """Lookup IBC Section 1607.9 / ASCE 7-22 Section 4.5.1 guardrail live loads from CSV."""
    rows = kb.get_table_as_dicts(IBC_GUARDRAIL_FILE)
    p_conc_lbs = 200.0
    w_unif_plf = 50.0
    p_infill_lbs = 50.0
    fs_glass = 4.0

    for row in rows:
        elem = str(row.get("Element / Load Case", "")).strip()
        mag_str = str(row.get("Magnitude", "")).strip()
        if "Concentrated Load" in elem and "200" in mag_str:
            p_conc_lbs = 200.0
        elif "Uniform Load" in elem and "Exception" not in elem and "50" in mag_str:
            w_unif_plf = 50.0
        elif "Infill" in elem and "50" in mag_str:
            p_infill_lbs = 50.0
        elif "Glass" in elem and "4.0" in mag_str:
            fs_glass = 4.0

    occ_lower = occupancy.strip().lower()
    if "r-3" in occ_lower or "residential" in occ_lower or "dwelling" in occ_lower:
        w_unif_plf = 0.0  # Exception 1: One- and two-family dwellings governed by 200 lb concentrated load

    return {
        "P_conc_lbs": p_conc_lbs,
        "w_unif_plf": w_unif_plf,
        "P_infill_lbs": p_infill_lbs,
        "FS_glass": fs_glass,
    }


def calculate_guardrail_loads(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Calculate guardrail top rail, post base overturning, and anchor bolt tension demands
    per 2024 IBC Section 1607.9 / 2025 CBC and ASCE 7-22 Section 4.5.1.
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-guardrail-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    occupancy = str(inputs.get("occupancy", "R-3_Residential")).strip()
    h_guard_in = validate_positive("H_guard_in", inputs.get("H_guard_in", 42.0))
    s_post_ft = validate_positive("S_post_ft", inputs.get("S_post_ft", 5.0))
    e_fas_in = validate_non_negative("e_fas_in", inputs.get("e_fas_in", 0.0))
    infill_type = str(inputs.get("infill_type", "Open_Pickets_Cables")).strip()
    p_wind_psf = validate_non_negative("p_W_psf", inputs.get("p_W_psf", 20.0))
    epsilon_guard = validate_positive("epsilon_guard", inputs.get("epsilon_guard", 0.30))
    n_t_bolts = int(validate_positive("N_t_bolts", inputs.get("N_t_bolts", 2)))
    d_bolt_in = validate_positive("d_bolt_in", inputs.get("d_bolt_in", 4.25))

    # Capacities
    t_bolt_cap_asd = validate_positive("T_bolt_cap_asd_lbs", inputs.get("T_bolt_cap_asd_lbs", 1250.0))
    m_post_cap_asd = validate_positive("M_post_cap_asd_lb_ft", inputs.get("M_post_cap_asd_lb_ft", 950.0))
    m_rail_cap_asd = validate_positive("M_rail_cap_asd_lb_ft", inputs.get("M_rail_cap_asd_lb_ft", 450.0))

    t_bolt_cap = float(inputs.get("T_bolt_cap_lrfd_lbs", t_bolt_cap_asd * 1.6)) if method == DesignMethod.LRFD else t_bolt_cap_asd
    m_post_cap = float(inputs.get("M_post_cap_lrfd_lb_ft", m_post_cap_asd * 1.6)) if method == DesignMethod.LRFD else m_post_cap_asd
    m_rail_cap = float(inputs.get("M_rail_cap_lrfd_lb_ft", m_rail_cap_asd * 1.6)) if method == DesignMethod.LRFD else m_rail_cap_asd

    # 2. Step 1: Lookup IBC Section 1607.9 Live Loads
    ibc_loads = lookup_ibc_guardrail_loads(kb, occupancy=occupancy)
    p_conc_lbs = ibc_loads["P_conc_lbs"]
    w_unif_plf = ibc_loads["w_unif_plf"]

    # 3. Step 2: Top Rail Bending & Shear Demands (Unfactored Live Load)
    m_rail_conc_lb_ft = (p_conc_lbs * s_post_ft) / 4.0
    v_rail_conc_lbs = p_conc_lbs / 2.0

    m_rail_unif_lb_ft = (w_unif_plf * (s_post_ft ** 2)) / 8.0
    v_rail_unif_lbs = (w_unif_plf * s_post_ft) / 2.0

    m_rail_l_lb_ft = max(m_rail_conc_lb_ft, m_rail_unif_lb_ft)
    v_rail_l_lbs = max(v_rail_conc_lbs, v_rail_unif_lbs)

    # 4. Step 3: Guardrail Post & Base Connection Demands
    h_eff_ft = (h_guard_in + e_fas_in) / 12.0
    v_post_conc_lbs = p_conc_lbs
    v_post_unif_lbs = w_unif_plf * s_post_ft
    v_post_l_lbs = max(v_post_conc_lbs, v_post_unif_lbs)
    m_base_l_lb_ft = v_post_l_lbs * h_eff_ft

    # Exterior Wind on Post
    v_post_w_lbs = p_wind_psf * epsilon_guard * s_post_ft * (h_guard_in / 12.0)
    h_wind_arm_ft = (0.5 * h_guard_in + e_fas_in) / 12.0
    m_base_w_lb_ft = v_post_w_lbs * h_wind_arm_ft

    # 5. Step 4: Factored Design Loads (ASD vs. LRFD)
    if method == DesignMethod.ASD:
        f_l = 1.0
        v_post_gov_lbs = max(1.0 * v_post_l_lbs, 0.6 * v_post_w_lbs, 0.75 * v_post_l_lbs + 0.45 * v_post_w_lbs)
        m_base_gov_lb_ft = max(1.0 * m_base_l_lb_ft, 0.6 * m_base_w_lb_ft, 0.75 * m_base_l_lb_ft + 0.45 * m_base_w_lb_ft)
        m_rail_gov_lb_ft = 1.0 * m_rail_l_lb_ft
    else:
        f_l = 1.6
        v_post_gov_lbs = max(1.6 * v_post_l_lbs, 1.0 * v_post_w_lbs, 1.0 * v_post_l_lbs + 1.0 * v_post_w_lbs)
        m_base_gov_lb_ft = max(1.6 * m_base_l_lb_ft, 1.0 * m_base_w_lb_ft, 1.0 * m_base_l_lb_ft + 1.0 * m_base_w_lb_ft)
        m_rail_gov_lb_ft = 1.6 * m_rail_l_lb_ft

    # 6. Step 5: Anchor Bolt / Tension Tie Force
    m_base_gov_lb_in = m_base_gov_lb_ft * 12.0
    t_bolt_gov_lbs = m_base_gov_lb_in / (n_t_bolts * d_bolt_in)

    # 7. Limit States
    limit_states: List[LimitStateResult] = []

    dcr_bolt = t_bolt_gov_lbs / t_bolt_cap
    limit_states.append(LimitStateResult(
        step_id="S1",
        name="Post Base Anchor Bolt / Tension Tie Pullout",
        code_clause="2024 IBC Sec. 1607.9.1 & ASCE 7-22 Sec. 4.5.1",
        equation_latex="T_{bolt} = (M_{base} \\cdot 12) / (N_t \\cdot d_{bolt})",
        substitution_str=f"({m_base_gov_lb_ft:.1f} lb-ft . 12) / ({n_t_bolts} . {d_bolt_in:.2f} in.) = {t_bolt_gov_lbs:.1f} lbs/bolt",
        demand=round(t_bolt_gov_lbs, 2),
        capacity=round(t_bolt_cap, 2),
        units="lbs",
        dcr=round(dcr_bolt, 3),
        status=CalculationStatus.PASS if dcr_bolt <= 1.0 else CalculationStatus.FAIL,
        notes=f"Effective post height H_eff = {h_eff_ft:.2f} ft; {n_t_bolts} tension bolts at lever arm d_bolt = {d_bolt_in:.2f} in.",
    ))

    dcr_post = m_base_gov_lb_ft / m_post_cap
    limit_states.append(LimitStateResult(
        step_id="S2",
        name="Guardrail Post Flexural Bending at Base",
        code_clause="2024 IBC Sec. 1607.9.1.1",
        equation_latex="M_{base} = f_L \\cdot V_{post,L} \\cdot H_{eff}",
        substitution_str=f"{f_l:.1f} . {v_post_l_lbs:.1f} lbs . {h_eff_ft:.2f} ft = {m_base_gov_lb_ft:.1f} lb-ft",
        demand=round(m_base_gov_lb_ft, 2),
        capacity=round(m_post_cap, 2),
        units="lb-ft",
        dcr=round(dcr_post, 3),
        status=CalculationStatus.PASS if dcr_post <= 1.0 else CalculationStatus.FAIL,
    ))

    dcr_rail = m_rail_gov_lb_ft / m_rail_cap
    limit_states.append(LimitStateResult(
        step_id="S3",
        name="Top Rail Midspan Flexural Bending",
        code_clause="2024 IBC Sec. 1607.9.1",
        equation_latex="M_{rail} = f_L \\cdot \\max(P_{conc} S / 4, w_{unif} S^2 / 8)",
        substitution_str=f"{f_l:.1f} . {m_rail_l_lb_ft:.1f} lb-ft = {m_rail_gov_lb_ft:.1f} lb-ft",
        demand=round(m_rail_gov_lb_ft, 2),
        capacity=round(m_rail_cap, 2),
        units="lb-ft",
        dcr=round(dcr_rail, 3),
        status=CalculationStatus.PASS if dcr_rail <= 1.0 else CalculationStatus.FAIL,
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    ref_proc = _build_ref(
        kb, "IBC", "2024", "procedure", "Guardrail & Handrail Loads Procedure",
        identifier="guardrail_handrail_loads_ibc_workflow.md",
        fallback_path="procedures/01_loads_and_seismic/guardrail_handrail_loads_ibc_workflow.md",
    )
    ref_ibc = _build_ref(kb, "IBC", "2024", "table", "Sec. 1607.9", identifier=IBC_GUARDRAIL_FILE)
    ref_combos = _build_ref(
        kb, "ASCE 7-22", "2022", "table",
        "Table 2.4-1" if method == DesignMethod.ASD else "Table 2.3-1",
        identifier="ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv",
    )

    trace = (
        CalcStep(
            step_id="S1_GEO",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Guardrail Effective Post Height & Lever Arm",
            symbolic=r"H_{eff} = \frac{H_{guard} + e_{fas}}{12}",
            substituted=rf"\frac{{{h_guard_in:.1f} + {e_fas_in:.1f}}}{{12}} = {h_eff_ft:.3f} \text{{ ft}}",
            variables={
                "H_guard": Quantity("H_{guard}", h_guard_in, "in.", "Guardrail top rail height"),
                "e_fas": Quantity("e_{fas}", e_fas_in, "in.", "Fascia attachment offset"),
                "H_eff": Quantity("H_{eff}", round(h_eff_ft, 3), "ft", "Effective cantilever height"),
                "S_post": Quantity("S_{post}", s_post_ft, "ft", "Guardrail post spacing"),
            },
            result_value=round(h_eff_ft, 3),
            result_unit="ft",
            acceptance=AcceptanceCriterion("info", description="2024 IBC Sec. 1607.9 post lever arm geometry", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(ref_ibc, ref_proc),
        ),
        CalcStep(
            step_id="S2_LOADS",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Governing Live & Wind Guardrail Post Loads",
            symbolic=r"V_{post,gov} = \max\left(f_L \cdot V_{post,L}, 0.6 \cdot V_{post,W}\right)" if method == DesignMethod.ASD else r"V_{post,gov} = \max\left(1.6 \cdot V_{post,L}, 1.0 \cdot V_{post,W}\right)",
            substituted=rf"V_{{post,gov}} = {v_post_gov_lbs:.2f} \text{{ lbs}}",
            variables={
                "P_conc": Quantity("P_{conc}", p_conc_lbs, "lbs", "Concentrated guardrail live load"),
                "w_unif": Quantity("w_{unif}", w_unif_plf, "plf", "Uniform guardrail live load"),
                "V_post_L": Quantity("V_{post,L}", round(v_post_l_lbs, 2), "lbs", "Unfactored live post shear"),
                "V_post_W": Quantity("V_{post,W}", round(v_post_w_lbs, 2), "lbs", "Unfactored wind post shear"),
            },
            result_value=round(v_post_gov_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("info", description="Non-concurrent live vs. wind governing post shear", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(ref_ibc, RefSpec("ASCE 7-22", "2022", "section", "Sec. 4.5.1"), ref_combos),
        ),
        CalcStep(
            step_id="S3_RAIL",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Top Rail Midspan Flexural Bending",
            symbolic=r"M_{rail} = f_L \cdot \max\left(\frac{P_{conc} \cdot S}{4}, \frac{w_{unif} \cdot S^2}{8}\right)",
            substituted=rf"{f_l:.1f} \cdot {m_rail_l_lb_ft:.2f} = {m_rail_gov_lb_ft:.2f} \text{{ lb-ft}}",
            variables={
                "f_L": Quantity("f_L", f_l, "", f"{method.value} live load factor"),
                "M_rail_cap": Quantity("M_{rail,cap}", round(m_rail_cap, 2), "lb-ft", f"{method.value} top rail capacity"),
            },
            result_value=round(m_rail_gov_lb_ft, 2),
            result_unit="lb-ft",
            acceptance=AcceptanceCriterion("<=", round(m_rail_cap, 2), "lb-ft", f"{method.value} top rail flexural capacity", is_dcr_check=True),
            dcr=round(dcr_rail, 3),
            status=CalculationStatus.PASS if dcr_rail <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("IBC", "2024", "section", "Sec. 1607.9.1"), ref_ibc, ref_proc),
        ),
        CalcStep(
            step_id="S3_POST",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Guardrail Post Flexural Bending at Base",
            symbolic=r"M_{base} = f_L \cdot V_{post,L} \cdot H_{eff}",
            substituted=rf"{f_l:.1f} \cdot {v_post_l_lbs:.1f} \cdot {h_eff_ft:.2f} = {m_base_gov_lb_ft:.2f} \text{{ lb-ft}}",
            variables={
                "M_post_cap": Quantity("M_{post,cap}", round(m_post_cap, 2), "lb-ft", f"{method.value} post flexural capacity"),
            },
            result_value=round(m_base_gov_lb_ft, 2),
            result_unit="lb-ft",
            acceptance=AcceptanceCriterion("<=", round(m_post_cap, 2), "lb-ft", f"{method.value} post base flexural capacity", is_dcr_check=True),
            dcr=round(dcr_post, 3),
            status=CalculationStatus.PASS if dcr_post <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("IBC", "2024", "section", "Sec. 1607.9.1.1"), ref_combos, ref_proc),
        ),
        CalcStep(
            step_id="S4_BOLT",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Post Base Anchor Bolt / Tension Tie Pullout",
            symbolic=r"T_{bolt} = \frac{M_{base} \cdot 12}{N_t \cdot d_{bolt}}",
            substituted=rf"\frac{{{m_base_gov_lb_ft:.1f} \cdot 12}}{{{n_t_bolts} \cdot {d_bolt_in:.2f}}} = {t_bolt_gov_lbs:.2f} \text{{ lbs}}",
            variables={
                "N_t": Quantity("N_t", n_t_bolts, "", "Number of tension bolts"),
                "d_bolt": Quantity("d_{bolt}", d_bolt_in, "in.", "Tension couple lever arm"),
                "T_bolt_cap": Quantity("T_{bolt,cap}", round(t_bolt_cap, 2), "lbs", f"{method.value} anchor tension capacity"),
            },
            result_value=round(t_bolt_gov_lbs, 2),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("<=", round(t_bolt_cap, 2), "lbs", f"{method.value} anchor bolt tension capacity", is_dcr_check=True),
            dcr=round(dcr_bolt, 3),
            status=CalculationStatus.PASS if dcr_bolt <= 1.0 else CalculationStatus.FAIL,
            refs=(RefSpec("IBC", "2024", "section", "Sec. 1607.9.1 & ASCE 7-22 Sec. 4.5.1"), ref_proc),
        ),
    )

    warnings = [
        "Detailing Note: Never rely on cross-grain bending of a wood rim joist to resist guardrail post overturning; provide positive mechanical tension ties (e.g., Simpson DTT2Z/HDU2) into floor joists or blocking."
    ]
    if "glass" in infill_type.lower():
        warnings.append("IBC Section 2407.1: Structural glass handrail panels and shoes require a Safety Factor of 4.0.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="ibc_guardrail_loads",
        code_edition="2024 IBC / ASCE 7-22",
        design_method=method,
        input_parameters={
            "occupancy": occupancy,
            "H_guard_in": h_guard_in,
            "S_post_ft": s_post_ft,
            "e_fas_in": e_fas_in,
            "infill_type": infill_type,
            "p_W_psf": p_wind_psf,
            "epsilon_guard": epsilon_guard,
            "N_t_bolts": n_t_bolts,
            "d_bolt_in": d_bolt_in,
            "T_bolt_cap_lbs": round(t_bolt_cap, 2),
            "M_post_cap_lb_ft": round(m_post_cap, 2),
            "M_rail_cap_lb_ft": round(m_rail_cap, 2),
        },
        assumptions=[
            f"Occupancy: {occupancy}; Guard height H_guard = {h_guard_in:.1f} in., Post spacing S_post = {s_post_ft:.1f} ft.",
            f"Concentrated load P_conc = {p_conc_lbs:.0f} lbs, Uniform load w_unif = {w_unif_plf:.0f} plf (non-concurrent per IBC Sec. 1607.9.1).",
            f"Design method: {method.value} (Live load factor = {f_l:.1f}L).",
        ],
        intermediate_results={
            "P_conc_lbs": p_conc_lbs,
            "w_unif_plf": w_unif_plf,
            "H_eff_ft": round(h_eff_ft, 3),
            "V_post_L_lbs": round(v_post_l_lbs, 2),
            "M_base_L_lb_ft": round(m_base_l_lb_ft, 2),
            "V_post_W_lbs": round(v_post_w_lbs, 2),
            "M_base_W_lb_ft": round(m_base_w_lb_ft, 2),
            "V_post_gov_lbs": round(v_post_gov_lbs, 2),
            "M_base_gov_lb_ft": round(m_base_gov_lb_ft, 2),
            "M_base_gov_lb_in": round(m_base_gov_lb_in, 2),
            "T_bolt_gov_lbs": round(t_bolt_gov_lbs, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/ibc_cbc/v2024_ibc_v2025_cbc/IBC-2024_Section_1607.9_Guardrail_Loads.csv",
            "database/asce_7/v7_22/ASCE7-22_Table_2.3-1_2.4-1_Load_Combinations.csv",
            "procedures/01_loads_and_seismic/guardrail_handrail_loads_ibc_workflow.md",
        ],
        warnings=warnings,
        trace=trace,
    )
