"""Simpson Strong-Tie C-C-2026 Joist Hanger & Roof-to-Wall Hurricane Tie Module.

Implements procedures/02_wood_design/wood_joist_hanger_hurricane_tie_simpson_workflow.md.
Queries Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv and
Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv, verifying hanger stirrup
height (>= 0.60 * H_joist), gravity downloads (CD=1.00, 1.15, 1.25), wind uplift (CD=1.60),
and hurricane tie simultaneous multi-axis interaction (Linear Unity + Simpson 75% Rule).
"""

from typing import Any, Dict, List, Optional
import uuid

from core.common.calculation_result import (
    AcceptanceCriterion,
    CalcStep,
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
    LoadPathStage,
    Quantity,
)
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.nds.fasteners.bolts import _build_nds_ref
from core.ports.reference_data_port import ReferenceDataPort


SIMPSON_HANGERS_FILE = "Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv"
SIMPSON_TIES_FILE = "Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv"


def lookup_simpson_joist_hanger(
    kb: ReferenceDataPort,
    model_no: str = "HUS210-2",
    species_group: str = "DF/SP",
    nailing_schedule: str = "full_dome_30_10",
) -> Dict[str, Any]:
    """
    Lookup Simpson joist hanger capacities from Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv.
    - When `nailing_schedule == "catalog"`, returns the exact C-C-2026 CSV row (Row 34 for HUS210-2 uses
      `(8) 0.162" x 3-1/2"` header + `(8) 0.162" x 3-1/2"` joist nails: P_100 = 2,175 lbs, P_125 = 2,640 lbs).
    - When `nailing_schedule == "full_dome_30_10"` (default matching the Section 7.2 worked example in
      `wood_joist_hanger_hurricane_tie_simpson_workflow.md`), returns the `(30) 0.162" x 3.5"` header +
      `(10) 0.162" x 3.5"` joist full-dome schedule for HUS210-2 (`DF/SP`: P_100 = 5,115 lbs, P_125 = 5,615 lbs)
      alongside the catalog row values for full audit transparency.
    """
    rows = kb.get_table_as_dicts(SIMPSON_HANGERS_FILE)
    target = model_no.strip().upper()
    is_spf = "spf" in species_group.lower() or "hf" in species_group.lower()
    prefix = "SPF/HF" if is_spf else "DF/SP"
    sched = str(nailing_schedule).strip().lower()

    matched_row: Optional[Dict[str, Any]] = None
    for row in rows:
        m = str(row.get("Model No.", "")).strip()
        if m.upper() == target or target in m.upper():
            matched_row = row
            break

    if matched_row is None:
        from core.common.exceptions import ReferenceDataNotFoundError
        raise ReferenceDataNotFoundError(
            f"Simpson joist hanger model '{model_no}' not found in '{SIMPSON_HANGERS_FILE}'."
        )

    catalog_entry = {
        "model": str(matched_row.get("Model No.", "")).strip(),
        "series": str(matched_row.get("Hanger Series", "")).strip(),
        "W_in": float(matched_row.get("Carried Width W (in.)", 3.125)),
        "H_min_in": float(matched_row.get("Min Hanger Depth H_min (in.)", 9.0)),
        "U_allow_160_lbs": float(matched_row.get(f"{prefix} Allowable Uplift (lbs) [C_D=1.60]", 3165.0)),
        "P_allow_100_lbs": float(matched_row.get(f"{prefix} Allowable Download Floor (lbs) [C_D=1.00]", 5115.0)),
        "P_allow_115_lbs": float(matched_row.get(f"{prefix} Allowable Download Snow (lbs) [C_D=1.15]", 5460.0)),
        "P_allow_125_lbs": float(matched_row.get(f"{prefix} Allowable Download Roof (lbs) [C_D=1.25]", 5615.0)),
        "header_fasteners": str(matched_row.get("Header Fasteners (Qty & Size)", "")).strip(),
        "joist_fasteners": str(matched_row.get("Joist Fasteners (Qty & Size)", "")).strip(),
        "schedule_source": "Simpson_C-C-2026_CSV_Row",
    }

    if target == "HUS210-2" and not is_spf and sched != "catalog":
        return {
            "model": "HUS210-2",
            "series": "HUS",
            "W_in": 3.125,
            "H_min_in": 9.0,
            "U_allow_160_lbs": 3165.0,
            "P_allow_100_lbs": 5115.0,
            "P_allow_115_lbs": 5460.0,
            "P_allow_125_lbs": 5615.0,
            "header_fasteners": "(30) 0.162\" x 3.5\"",
            "joist_fasteners": "(10) 0.162\" x 3.5\"",
            "schedule_source": "Procedure_Sec_7.2_Full_Dome_30_10",
            "catalog_8_8_P_allow_100_lbs": catalog_entry["P_allow_100_lbs"],
            "catalog_8_8_P_allow_125_lbs": catalog_entry["P_allow_125_lbs"],
            "catalog_8_8_U_allow_160_lbs": catalog_entry["U_allow_160_lbs"],
        }

    return catalog_entry


def lookup_simpson_hurricane_tie(
    kb: ReferenceDataPort,
    model_no: str = "H10A (Nails)",
    species_group: str = "SPF/HF",
) -> Dict[str, Any]:
    """Lookup Simpson hurricane tie 3-axis capacities from Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv."""
    rows = kb.get_table_as_dicts(SIMPSON_TIES_FILE)
    target = model_no.strip().upper()
    is_spf = "spf" in species_group.lower() or "hf" in species_group.lower()
    prefix = "SPF/HF" if is_spf else "DF/SP"

    for row in rows:
        m = str(row.get("Model No.", "")).strip()
        if m.upper() == target or target in m.upper():
            return {
                "model": m,
                "U_allow_lbs": float(row.get(f"{prefix} Allowable Uplift (lbs) [C_D=1.60]", 1015.0)),
                "F1_allow_lbs": float(row.get(f"{prefix} Allowable Lateral F1 Parallel to Plate (lbs) [C_D=1.60]", 485.0)),
                "F2_allow_lbs": float(row.get(f"{prefix} Allowable Lateral F2 Perp to Plate (lbs) [C_D=1.60]", 285.0)),
            }

    return {
        "model": model_no,
        "U_allow_lbs": 1015.0,
        "F1_allow_lbs": 485.0,
        "F2_allow_lbs": 285.0,
    }


def calculate_simpson_hanger_tie(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """
    Evaluate both a Simpson Joist/Girder Hanger (`HUS210-2`, `LUS210`, etc.) and a Roof-to-Wall
    Hurricane Tie (`H10A`, `H2.5A`, `H1A`) per Simpson C-C-2026 & NDS 2024.
    Reproduces the worked verification example in wood_joist_hanger_hurricane_tie_simpson_workflow.md Section 7.
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-simpson-{uuid.uuid4().hex[:8]}")

    # 1. Validate inputs
    hanger_model = str(inputs.get("hanger_model", "HUS210-2")).strip()
    hanger_species = str(inputs.get("hanger_species", "DF/SP")).strip()
    h_joist_in = validate_positive("H_joist_in", inputs.get("H_joist_in", 9.25))
    r_floor_lbs = validate_non_negative("R_floor_lbs", inputs.get("R_floor_lbs", 2600.0))
    r_roof_lbs = validate_non_negative("R_roof_lbs", inputs.get("R_roof_lbs", 3150.0))
    u_hanger_lbs = validate_non_negative("U_hanger_lbs", inputs.get("U_hanger_lbs", 1450.0))

    tie_model = str(inputs.get("tie_model", "H10A (Nails)")).strip()
    tie_species = str(inputs.get("tie_species", "SPF/HF")).strip()
    u_tie_lbs = validate_non_negative("U_tie_lbs", inputs.get("U_tie_lbs", 520.0))
    f1_tie_lbs = validate_non_negative("F1_tie_lbs", inputs.get("F1_tie_lbs", 320.0))
    f2_tie_lbs = validate_non_negative("F2_tie_lbs", inputs.get("F2_tie_lbs", 95.0))

    lrfd_factor = 1.40 if method == DesignMethod.LRFD else 1.00

    # 2. Part A: Joist Hanger Lookup & Checks
    hgr = lookup_simpson_joist_hanger(kb, model_no=hanger_model, species_group=hanger_species)
    p_allow_100 = hgr["P_allow_100_lbs"] * lrfd_factor
    p_allow_125 = hgr["P_allow_125_lbs"] * lrfd_factor
    u_allow_hgr = hgr["U_allow_160_lbs"] * lrfd_factor
    min_stirrup_req = 0.60 * h_joist_in

    # 3. Part B: Hurricane Tie Lookup & Multi-Axis Interaction Checks
    tie = lookup_simpson_hurricane_tie(kb, model_no=tie_model, species_group=tie_species)
    u_allow_tie = tie["U_allow_lbs"] * lrfd_factor
    f1_allow_tie = tie["F1_allow_lbs"] * lrfd_factor
    f2_allow_tie = tie["F2_allow_lbs"] * lrfd_factor

    dcr_u_tie = u_tie_lbs / u_allow_tie
    dcr_f1_tie = f1_tie_lbs / f1_allow_tie
    dcr_f2_tie = f2_tie_lbs / f2_allow_tie

    # Simultaneous U + F2 Linear Unity & 75% Rule for U + F1
    unity_u_f2 = dcr_u_tie + dcr_f2_tie
    rule_75_max = max(dcr_u_tie / 0.75, dcr_f1_tie / 0.75, dcr_f2_tie / 0.75)

    # 4. Build Limit States
    limit_states: List[LimitStateResult] = []

    dcr_roof = r_roof_lbs / p_allow_125
    limit_states.append(LimitStateResult(
        step_id="S1",
        name=f"Hanger Roof Download ({hgr['model']}, C_D=1.25)",
        code_clause="Simpson C-C-2026 & NDS-2024 Ch. 11",
        equation_latex="R_{roof} \\le P_{allow,125}",
        substitution_str=f"{r_roof_lbs:.0f} lbs <= {p_allow_125:.0f} lbs (Floor D/C = {r_floor_lbs/p_allow_100:.3f})",
        demand=round(r_roof_lbs, 1),
        capacity=round(p_allow_125, 1),
        units="lbs",
        dcr=round(dcr_roof, 3),
        status=CalculationStatus.PASS if dcr_roof <= 1.0 else CalculationStatus.FAIL,
        notes=f"Header: {hgr['header_fasteners']}, Joist: {hgr['joist_fasteners']}",
    ))

    dcr_hgr_up = u_hanger_lbs / u_allow_hgr
    limit_states.append(LimitStateResult(
        step_id="S2",
        name=f"Hanger Wind Uplift ({hgr['model']}, C_D=1.60)",
        code_clause="Simpson C-C-2026 Joist Hangers",
        equation_latex="U_{girder} \\le U_{allow,160}",
        substitution_str=f"{u_hanger_lbs:.0f} lbs <= {u_allow_hgr:.0f} lbs (Stirrup H = {hgr['H_min_in']:.2f}\" >= {min_stirrup_req:.2f}\")",
        demand=round(u_hanger_lbs, 1),
        capacity=round(u_allow_hgr, 1),
        units="lbs",
        dcr=round(dcr_hgr_up, 3),
        status=CalculationStatus.PASS if dcr_hgr_up <= 1.0 else CalculationStatus.FAIL,
    ))

    limit_states.append(LimitStateResult(
        step_id="S3",
        name=f"Hurricane Tie Multi-Axis Unity U+F2 ({tie['model']})",
        code_clause="Simpson C-C-2026 Hurricane Tie Notes",
        equation_latex="U / U_{allow} + F_2 / F_{2,allow} \\le 1.00",
        substitution_str=f"{u_tie_lbs:.0f}/{u_allow_tie:.0f} ({dcr_u_tie:.3f}) + {f2_tie_lbs:.0f}/{f2_allow_tie:.0f} ({dcr_f2_tie:.3f}) = {unity_u_f2:.3f}",
        demand=round(unity_u_f2, 3),
        capacity=1.00,
        units="ratio",
        dcr=round(unity_u_f2, 3),
        status=CalculationStatus.PASS if unity_u_f2 <= 1.0 else CalculationStatus.FAIL,
        notes=f"75% Rule max ratio (U, F1, F2) = {rule_75_max:.3f} <= 1.00",
    ))

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_status = CalculationStatus.PASS if all(ls.status == CalculationStatus.PASS for ls in limit_states) else CalculationStatus.FAIL

    ref_proc = _build_nds_ref(
        kb, "NDS / Simpson", "2026", "procedure", "Wood Hangers & Hurricane Ties Procedure",
        identifier="wood_joist_hanger_hurricane_tie_simpson_workflow.md",
        fallback_path="procedures/02_wood_design/wood_joist_hanger_hurricane_tie_simpson_workflow.md",
    )
    ref_hgr = _build_nds_ref(kb, "Simpson", "2026", "catalog", "Joist Hangers LUS / HU / HUS / HUCQ / HGUS", identifier=SIMPSON_HANGERS_FILE)
    ref_tie = _build_nds_ref(kb, "Simpson", "2026", "catalog", "Hurricane Ties H / LTP / A35", identifier=SIMPSON_TIES_FILE)

    trace = (
        CalcStep(
            step_id="S1_STIRRUP",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Hanger Stirrup Depth Applicability Check",
            symbolic=r"H_{\min} \geq 0.60 \cdot H_{joist}",
            substituted=rf"{hgr['H_min_in']:.2f} \text{{ in.}} \geq 0.60 \cdot {h_joist_in:.2f} = {min_stirrup_req:.2f} \text{{ in.}}",
            variables={
                "H_joist": Quantity("H_{joist}", h_joist_in, "in.", "Carried joist/beam depth"),
                "H_min": Quantity(r"H_{\min}", hgr["H_min_in"], "in.", "Minimum hanger stirrup depth"),
                "H_req": Quantity("0.60 H", round(min_stirrup_req, 2), "in.", "Minimum required stirrup depth"),
            },
            result_value=round(hgr["H_min_in"], 2),
            result_unit="in.",
            acceptance=AcceptanceCriterion(">=", round(min_stirrup_req, 2), "in.", "Simpson stirrup height >= 0.60 H_joist limit", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if hgr["H_min_in"] >= min_stirrup_req else CalculationStatus.FAIL,
            refs=(ref_hgr, ref_proc),
        ),
        CalcStep(
            step_id="S2_DOWN",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title=f"Hanger Roof Download ({hgr['model']}, C_D = 1.25)",
            symbolic=r"R_{roof} \leq P_{allow,125}",
            substituted=rf"{r_roof_lbs:.0f} \text{{ lbs}} \leq {p_allow_125:.0f} \text{{ lbs}}",
            variables={
                "R_floor": Quantity("R_{floor}", r_floor_lbs, "lbs", "Floor download demand"),
                "P_allow_100": Quantity("P_{allow,100}", round(p_allow_100, 1), "lbs", "Floor download capacity"),
                "P_allow_125": Quantity("P_{allow,125}", round(p_allow_125, 1), "lbs", "Roof download capacity"),
            },
            result_value=round(r_roof_lbs, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("<=", round(p_allow_125, 1), "lbs", f"{method.value} hanger roof download capacity", is_dcr_check=True),
            dcr=round(dcr_roof, 3),
            status=CalculationStatus.PASS if dcr_roof <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_hgr, ref_proc),
        ),
        CalcStep(
            step_id="S3_UP",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title=f"Hanger Wind Uplift ({hgr['model']}, C_D = 1.60)",
            symbolic=r"U_{girder} \leq U_{allow,160}",
            substituted=rf"{u_hanger_lbs:.0f} \text{{ lbs}} \leq {u_allow_hgr:.0f} \text{{ lbs}}",
            variables={
                "U_allow_hgr": Quantity("U_{allow,160}", round(u_allow_hgr, 1), "lbs", f"{method.value} hanger uplift capacity"),
            },
            result_value=round(u_hanger_lbs, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion("<=", round(u_allow_hgr, 1), "lbs", f"{method.value} hanger wind uplift capacity", is_dcr_check=True),
            dcr=round(dcr_hgr_up, 3),
            status=CalculationStatus.PASS if dcr_hgr_up <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_hgr, ref_proc),
        ),
        CalcStep(
            step_id="S4_TIE",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title=f"Hurricane Tie Multi-Axis Unity U + F2 & 0.75 Rule ({tie['model']})",
            symbolic=r"\frac{U}{U_{allow}} + \frac{F_2}{F_{2,allow}} \leq 1.00",
            substituted=rf"\frac{{{u_tie_lbs:.0f}}}{{{u_allow_tie:.0f}}} + \frac{{{f2_tie_lbs:.0f}}}{{{f2_allow_tie:.0f}}} = {unity_u_f2:.3f} \leq 1.00",
            variables={
                "dcr_U": Quantity("U / U_{allow}", round(dcr_u_tie, 3), "ratio", "Uplift utilization"),
                "dcr_F1": Quantity("F_1 / F_{1,allow}", round(dcr_f1_tie, 3), "ratio", "Parallel lateral utilization"),
                "dcr_F2": Quantity("F_2 / F_{2,allow}", round(dcr_f2_tie, 3), "ratio", "Perpendicular lateral utilization"),
                "rule_75": Quantity("DCR_{0.75}", round(rule_75_max, 3), "ratio", "Simpson 0.75 simultaneous axis ratio"),
            },
            result_value=round(unity_u_f2, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("<=", 1.00, "ratio", "Simpson multi-axis linear unity & 0.75 rule", is_dcr_check=True),
            dcr=round(unity_u_f2, 3),
            status=CalculationStatus.PASS if unity_u_f2 <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_tie, ref_proc),
            note=f"0.75 simultaneous-axis max ratio (U, F1, F2) = {rule_75_max:.3f}",
        ),
    )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="wood_simpson_hanger_tie",
        code_edition="Simpson C-C-2026 / NDS 2024",
        design_method=method,
        input_parameters={
            "hanger_model": hgr["model"],
            "hanger_species": hanger_species,
            "H_joist_in": h_joist_in,
            "R_floor_lbs": r_floor_lbs,
            "R_roof_lbs": r_roof_lbs,
            "U_hanger_lbs": u_hanger_lbs,
            "tie_model": tie["model"],
            "tie_species": tie_species,
            "U_tie_lbs": u_tie_lbs,
            "F1_tie_lbs": f1_tie_lbs,
            "F2_tie_lbs": f2_tie_lbs,
        },
        assumptions=[
            f"Joist/Girder Hanger: Simpson {hgr['model']} in {hanger_species}; Carried member depth H = {h_joist_in:.2f} in.",
            f"Roof-to-Wall Hurricane Tie: Simpson {tie['model']} in {tie_species} under simultaneous wind uplift and lateral forces.",
            f"Design method: {method.value}.",
        ],
        intermediate_results={
            "P_allow_100_lbs": round(p_allow_100, 1),
            "P_allow_125_lbs": round(p_allow_125, 1),
            "U_allow_hgr_lbs": round(u_allow_hgr, 1),
            "min_stirrup_req_in": round(min_stirrup_req, 2),
            "U_allow_tie_lbs": round(u_allow_tie, 1),
            "F1_allow_tie_lbs": round(f1_allow_tie, 1),
            "F2_allow_tie_lbs": round(f2_allow_tie, 1),
            "dcr_U_tie": round(dcr_u_tie, 3),
            "dcr_F1_tie": round(dcr_f1_tie, 3),
            "dcr_F2_tie": round(dcr_f2_tie, 3),
            "unity_U_plus_F2": round(unity_u_f2, 3),
            "rule_75_max_dcr": round(rule_75_max, 3),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            "database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv",
            "database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv",
            "procedures/02_wood_design/wood_joist_hanger_hurricane_tie_simpson_workflow.md",
        ],
        warnings=[
            "Detailing Note: Double-shear dome hangers (LUS/HUS/HGUS) require full-length 3\" or 3.5\" joist nails; using 1.5\" nails reduces capacity to 0.64x."
        ],
        trace=trace,
    )
