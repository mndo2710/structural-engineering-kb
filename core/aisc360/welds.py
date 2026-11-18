"""ANSI/AISC 360-22 Chapter J Steel Welded Connection Module.

Implements procedures/03_steel_design/steel_welded_connection_aisc_workflow.md.
Evaluates Dual ASD/LRFD fillet weld size limits (Table J2.4, Sec. J2.2b),
elastic vector weld-group capacity under eccentric shear/moment (Table J2.5),
directional strength factor restrictions for HSS/eccentric joints, bracket plate
base-metal shear yielding/rupture (Sec. J4.2), and supporting member flange check.
"""

from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Optional
import uuid

from core.aisc360.bolts import (
    MATERIAL_GRADES_FILE,
    SHAPES_DATABASE_FILE,
    TABLE_J2_4_FILE,
    TABLE_J2_5_FILE,
    _build_aisc_ref,
    _check_blank_inputs,
    _make_incomplete_result,
    _parse_fraction,
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
from core.common.exceptions import InputValidationError
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort


PROC_WELDS_FILE = "steel_welded_connection_aisc_workflow.md"


def lookup_min_fillet_weld_j2_4(kb: ReferenceDataPort, thinner_part_in: float) -> float:
    """Lookup minimum fillet weld size w_min (in.) from AISC 360-22 Table J2.4."""
    csv_path = kb.get_file_path(TABLE_J2_4_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    # Verify table structure dynamically (title row 0, header row 1, brackets rows 2..5)
    bracket_mins: Dict[str, float] = {}
    for row in rows[2:6]:
        if len(row) >= 2:
            bracket_mins[row[0].strip().lower()] = _parse_fraction(row[1], 0.1875)

    if thinner_part_in <= 0.25 + 1e-6:
        for k, val in bracket_mins.items():
            if "to 1/4" in k:
                return val
        return 0.125
    if thinner_part_in <= 0.50 + 1e-6:
        for k, val in bracket_mins.items():
            if "to 1/2" in k:
                return val
        return 0.1875
    if thinner_part_in <= 0.75 + 1e-6:
        for k, val in bracket_mins.items():
            if "to 3/4" in k:
                return val
        return 0.25
    for k, val in bracket_mins.items():
        if "over 3/4" in k:
            return val
    return 0.3125


def lookup_fillet_weld_factors_j2_5(kb: ReferenceDataPort) -> Dict[str, float]:
    """Lookup fillet weld shear factors (phi, Omega) from AISC 360-22 Table J2.5."""
    csv_path = kb.get_file_path(TABLE_J2_5_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            wt = (row.get("Weld Type") or "").strip().lower()
            lt = (row.get("Load Type and Direction Relative to Weld Axis") or "").strip().lower()
            pm = (row.get("Pertinent Metal") or "").strip().lower()
            if "fillet" in wt and "shear" in lt and "weld" in pm:
                return {
                    "phi": float(row["phi (LRFD)"]),
                    "Omega": float(row["Omega (ASD)"]),
                }
    raise InputValidationError("Fillet weld shear row not found in AISC360-22_Table_J2.5_Welded_Joints.csv.")


def calculate_steel_welded_connection(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 Chapter J fillet-welded connection across all 4 load-path stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-steel-welds-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "Steel Welded Connection Workflow",
        identifier=PROC_WELDS_FILE,
        fallback_path="procedures/03_steel_design/steel_welded_connection_aisc_workflow.md",
    )
    ref_j2_4 = _build_aisc_ref(kb, "table", "Table J2.4", identifier=TABLE_J2_4_FILE)
    ref_j2_5 = _build_aisc_ref(kb, "table", "Table J2.5", identifier=TABLE_J2_5_FILE)
    ref_shapes = _build_aisc_ref(kb, "catalog", "AISC 16th Shapes Database", identifier=SHAPES_DATABASE_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)

    req_keys = ("w_leg_in", "d_w_in", "t_plate_in", "support_section")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_welded_connection", "AISC 360-22 (16th Ed.)", method, inputs, blank_reasons,
            [ref_proc, ref_j2_4, ref_j2_5, ref_shapes, ref_mat],
        )

    # 1. Benchmark defaults matching procedures/03_steel_design/steel_welded_connection_aisc_workflow.md Sec. 7
    weld_config = str(inputs.get("weld_config", "C_shape")).strip().lower()
    w_leg_in = validate_positive("w_leg_in", inputs.get("w_leg_in", 0.25))
    f_exx_ksi = validate_positive("F_EXX_ksi", inputs.get("F_EXX_ksi", 70.0))
    b_w_in = validate_non_negative("b_w_in", inputs.get("b_w_in", 5.0 if "c" in weld_config else 0.0))
    d_w_in = validate_positive("d_w_in", inputs.get("d_w_in", 10.0))
    e_face_in = validate_non_negative("e_face_in", inputs.get("e_face_in", 8.0))

    plate_grade = str(inputs.get("plate_grade", "A36")).strip()
    t_plate_in = validate_positive("t_plate_in", inputs.get("t_plate_in", 0.50))
    support_section = str(inputs.get("support_section", "W12x65")).strip()
    support_grade = str(inputs.get("support_grade", "A992")).strip()
    is_hss_end = bool(inputs.get("is_hss_end_weld", False))
    theta_load_deg = validate_non_negative("theta_load_deg", inputs.get("theta_load_deg", 0.0))

    mat_plate = lookup_material_grade(kb, plate_grade)
    fy_p = float(inputs.get("Fy_plate_ksi", mat_plate["Fy_ksi"]))
    fu_p = float(inputs.get("Fu_plate_ksi", mat_plate["Fu_ksi"]))

    mat_sup = lookup_material_grade(kb, support_grade)
    fy_sup = float(inputs.get("Fy_support_ksi", mat_sup["Fy_ksi"]))
    fu_sup = float(inputs.get("Fu_support_ksi", mat_sup["Fu_ksi"]))

    shape_sup = lookup_shape_imperial(kb, support_section)
    t_sup_in = float(inputs.get("t_support_in", shape_sup["tf"] or shape_sup["tdes"] or 0.605))

    if method == DesignMethod.LRFD:
        v_demand = validate_non_negative("V_u_kips", inputs.get("V_u_kips", 36.0))
    else:
        v_demand = validate_non_negative("V_a_kips", inputs.get("V_a_kips", 24.0))

    # 2. Stage 1 Weld Size Limits (Table J2.4 & Sec. J2.2b)
    thinner_part = min(t_plate_in, t_sup_in)
    w_min_in = lookup_min_fillet_weld_j2_4(kb, thinner_part)
    w_max_in = t_plate_in if t_plate_in < 0.25 else (t_plate_in - 0.0625)
    weld_size_ok = (w_leg_in >= w_min_in - 1e-6) and (w_leg_in <= w_max_in + 1e-6)

    # 3. Stage 2 Weld Group Geometry, Centroid, Polar Moment of Inertia & Unit Demand (kips/in.)
    if weld_config in ("c", "c_shape", "c-shape", "three_sided") or weld_config.startswith("c_"):
        l_w = 2.0 * b_w_in + d_w_in
        x_bar = (b_w_in ** 2) / l_w if l_w > 0 else 0.0
        i_x = (d_w_in ** 3) / 12.0 + 2.0 * b_w_in * ((d_w_in / 2.0) ** 2)
        i_y = d_w_in * (x_bar ** 2) + 2.0 * ((b_w_in ** 3) / 12.0 + b_w_in * ((b_w_in / 2.0 - x_bar) ** 2))
        i_p = i_x + i_y
        e_cg = max(0.0, e_face_in - x_bar)
        cx_max = max(x_bar, b_w_in - x_bar)
        cy_max = d_w_in / 2.0
    elif "double" in weld_config or "two" in weld_config:
        l_w = 2.0 * d_w_in
        x_bar = 0.0
        i_x = 2.0 * (d_w_in ** 3) / 12.0
        i_y = 0.0
        i_p = i_x
        e_cg = e_face_in
        cx_max = 0.0
        cy_max = d_w_in / 2.0
    else:
        l_w = d_w_in
        x_bar = 0.0
        i_x = (d_w_in ** 3) / 12.0
        i_y = 0.0
        i_p = i_x
        e_cg = e_face_in
        cx_max = 0.0
        cy_max = d_w_in / 2.0

    m_ecc = v_demand * e_cg
    r_direct_y = v_demand / l_w if l_w > 0 else 0.0
    r_torsion_x = (m_ecc * cy_max / i_p) if i_p > 0 else 0.0
    r_torsion_y = (m_ecc * cx_max / i_p) if i_p > 0 else 0.0
    r_demand_max = math.hypot(r_torsion_x, r_direct_y + r_torsion_y)

    # Weld strength per linear inch (Table J2.5)
    weld_factors = lookup_fillet_weld_factors_j2_5(kb)
    phi_w = weld_factors["phi"]
    omega_w = weld_factors["Omega"]
    t_eff = 0.70710678 * w_leg_in

    # Directional factor disabled for HSS end welds or multi-axis eccentric bracket torsion
    dir_factor = 1.0
    if not is_hss_end and "single" in weld_config and theta_load_deg > 0.0:
        dir_factor = 1.0 + 0.50 * (math.sin(math.radians(min(90.0, theta_load_deg))) ** 1.5)

    f_nw_ksi = 0.60 * f_exx_ksi * dir_factor
    r_n_per_in = f_nw_ksi * t_eff
    cap_weld_per_in = phi_w * r_n_per_in if method == DesignMethod.LRFD else r_n_per_in / omega_w
    dcr_weld = r_demand_max / cap_weld_per_in

    # 4. Stage 3 Bracket Plate Base Metal Shear Yielding & Rupture along weld leg (Sec. J4.2)
    r_bm_yield_per_in = 0.60 * fy_p * t_plate_in
    r_bm_rupture_per_in = 0.60 * fu_p * t_plate_in
    cap_bm_yield = 1.00 * r_bm_yield_per_in if method == DesignMethod.LRFD else r_bm_yield_per_in / 1.50
    cap_bm_rupture = 0.75 * r_bm_rupture_per_in if method == DesignMethod.LRFD else r_bm_rupture_per_in / 2.00
    cap_bm_gov = min(cap_bm_yield, cap_bm_rupture)
    # Two-sided weld doubles shear demand on single shared bracket plate toe only if double-sided
    bm_demand_plate = (2.0 * r_demand_max) if "double" in weld_config else r_demand_max
    dcr_bm_plate = bm_demand_plate / cap_bm_gov

    # 5. Stage 4 Supporting Member Local Flange Base-Metal Shear Check
    r_sup_yield = 0.60 * fy_sup * t_sup_in
    r_sup_rupture = 0.60 * fu_sup * t_sup_in
    cap_sup_yield = 1.00 * r_sup_yield if method == DesignMethod.LRFD else r_sup_yield / 1.50
    cap_sup_rupture = 0.75 * r_sup_rupture if method == DesignMethod.LRFD else r_sup_rupture / 2.00
    cap_sup_gov = min(cap_sup_yield, cap_sup_rupture)
    dcr_sup = r_demand_max / cap_sup_gov

    d_sixteenths = w_leg_in * 16.0

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_WELD",
            name="Fillet Weld Group Elastic Vector Capacity (Table J2.5)",
            code_clause="AISC 360-22 Sec. J2.4 & Table J2.5",
            equation_latex=r"\phi R_n = \phi \cdot 0.60 F_{EXX} \cdot 0.707 w" if method == DesignMethod.LRFD else r"R_n / \Omega = 0.60 F_{EXX} \cdot 0.707 w / \Omega",
            substitution_str=f"f_max={r_demand_max:.3f} kips/in. vs cap={cap_weld_per_in:.3f} kips/in.",
            demand=round(r_demand_max, 3),
            capacity=round(cap_weld_per_in, 3),
            units="kips/in.",
            dcr=round(dcr_weld, 3),
            status=CalculationStatus.PASS if dcr_weld <= 1.0 else CalculationStatus.FAIL,
            notes=f"w={w_leg_in:.4f} in. (D={d_sixteenths:.1f}), L_w={l_w:.2f} in., I_p={i_p:.2f} in.^3",
        ),
        LimitStateResult(
            step_id="S3_BM",
            name="Bracket Plate Base Metal Shear Check (Sec. J4.2)",
            code_clause="AISC 360-22 Sec. J4.2(a)-(b)",
            equation_latex=r"R_{BM} = \min\left(\phi_v 0.60 F_y t,  \phi_r 0.60 F_u t\right)",
            substitution_str=f"min(yield={cap_bm_yield:.2f}, rupture={cap_bm_rupture:.2f}) kips/in.",
            demand=round(bm_demand_plate, 3),
            capacity=round(cap_bm_gov, 3),
            units="kips/in.",
            dcr=round(dcr_bm_plate, 3),
            status=CalculationStatus.PASS if dcr_bm_plate <= 1.0 else CalculationStatus.FAIL,
            notes=f"t_plate={t_plate_in:.3f} in. ({plate_grade})",
        ),
        LimitStateResult(
            step_id="S4_SUP",
            name=f"Supporting Member ({shape_sup['label']}) Local Base Metal Check",
            code_clause="AISC 360-22 Sec. J4.2",
            equation_latex=r"R_{sup} = \min\left(\phi_v 0.60 F_{y,sup} t_{sup},  \phi_r 0.60 F_{u,sup} t_{sup}\right)",
            substitution_str=f"t_sup={t_sup_in:.3f} in., min={cap_sup_gov:.2f} kips/in.",
            demand=round(r_demand_max, 3),
            capacity=round(cap_sup_gov, 3),
            units="kips/in.",
            dcr=round(dcr_sup, 3),
            status=CalculationStatus.PASS if dcr_sup <= 1.0 else CalculationStatus.FAIL,
        ),
    ]

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = weld_size_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    if method == DesignMethod.LRFD:
        w_sym = _validated_markup(r"\phi r_n = \phi \cdot 0.60 \cdot F_{EXX} \cdot 0.7071 \cdot w")
        w_sub = _validated_markup(rf"0.75 \cdot 0.60 \cdot {f_exx_ksi:.0f} \cdot 0.7071 \cdot {w_leg_in:.4f} = {cap_weld_per_in:.3f} \text{{ kips/in.}}")
    else:
        w_sym = _validated_markup(r"\frac{r_n}{\Omega} = \frac{0.60 \cdot F_{EXX} \cdot 0.7071 \cdot w}{\Omega}")
        w_sub = _validated_markup(rf"\frac{{0.60 \cdot {f_exx_ksi:.0f} \cdot 0.7071 \cdot {w_leg_in:.4f}}}{{2.00}} = {cap_weld_per_in:.3f} \text{{ kips/in.}}")

    trace = (
        CalcStep(
            step_id="S1_WELD_SIZE",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Minimum & Maximum Fillet Weld Leg Size Check",
            symbolic=_validated_markup(r"w_{\min} \leq w \leq w_{\max}"),
            substituted=_validated_markup(
                rf"{w_min_in:.4f} \text{{ in.}} \leq {w_leg_in:.4f} \text{{ in.}} \leq {w_max_in:.4f} \text{{ in.}}"
            ),
            variables={
                "t_thin": Quantity("t_{thin}", round(thinner_part, 3), "in.", "Thinner part joined"),
                "w": Quantity("w", w_leg_in, "in.", "Specified fillet weld leg"),
                "w_min": Quantity("w_{\\min}", round(w_min_in, 4), "in.", "Minimum weld size (Table J2.4)"),
                "w_max": Quantity("w_{\\max}", round(w_max_in, 4), "in.", "Maximum weld size along edge (Sec. J2.2b)"),
            },
            result_value=round(w_leg_in, 4),
            result_unit="in.",
            acceptance=AcceptanceCriterion(
                "in_range",
                f"[{w_min_in:.4f}, {w_max_in:.4f}]",
                "in.",
                "Table J2.4 min / Sec. J2.2b max fillet weld size",
                is_dcr_check=False,
            ),
            dcr=None,
            status=CalculationStatus.PASS if weld_size_ok else CalculationStatus.FAIL,
            refs=(ref_j2_4, ref_proc),
        ),
        CalcStep(
            step_id="S2_WELD_DEMAND",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Weld Group Centroid, Polar Moment of Inertia & Resultant Stress",
            symbolic=_validated_markup(r"f_{\max} = \sqrt{\left(\frac{M c_y}{I_p}\right)^2 + \left(\frac{V}{L_w} + \frac{M c_x}{I_p}\right)^2}"),
            substituted=_validated_markup(
                rf"\sqrt{{({r_torsion_x:.3f})^2 + ({r_direct_y:.3f} + {r_torsion_y:.3f})^2}} = {r_demand_max:.3f} \text{{ kips/in.}}"
            ),
            variables={
                "L_w": Quantity("L_w", round(l_w, 2), "in.", "Total fillet weld length"),
                "x_bar": Quantity("x_{bar}", round(x_bar, 3), "in.", "Weld group centroid from vertical leg"),
                "e_cg": Quantity("e_{cg}", round(e_cg, 3), "in.", "Eccentricity to weld centroid"),
                "I_p": Quantity("I_p", round(i_p, 2), "in.^3", "Unit polar moment of inertia"),
                "f_max": Quantity("f_{\\max}", round(r_demand_max, 3), "kips/in.", "Peak resultant unit weld demand"),
            },
            result_value=round(r_demand_max, 3),
            result_unit="kips/in.",
            acceptance=AcceptanceCriterion("info", description="Peak resultant weld force per inch", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS,
            refs=(ref_proc,),
        ),
        CalcStep(
            step_id="S2_WELD_CAP",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Fillet Weld Shear Capacity vs. Peak Demand",
            symbolic=w_sym,
            substituted=w_sub,
            variables={
                "F_EXX": Quantity("F_{EXX}", f_exx_ksi, "ksi", "Electrode tensile strength"),
                "t_eff": Quantity("t_e", round(t_eff, 4), "in.", "Effective weld throat (0.7071 w)"),
                "r_demand": Quantity("f_{\\max}", round(r_demand_max, 3), "kips/in.", f"{method.value} peak weld force"),
                "r_cap": Quantity("r_{cap}", round(cap_weld_per_in, 3), "kips/in.", f"{method.value} unit weld capacity"),
            },
            result_value=round(cap_weld_per_in, 3),
            result_unit="kips/in.",
            acceptance=AcceptanceCriterion(">=", round(r_demand_max, 3), "kips/in.", f"{method.value} fillet weld shear check", is_dcr_check=True),
            dcr=round(dcr_weld, 3),
            status=CalculationStatus.PASS if dcr_weld <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_j2_5, ref_proc),
        ),
        CalcStep(
            step_id="S3_BASE_METAL",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Bracket Plate Base-Metal Shear Yielding & Rupture (Sec. J4.2)",
            symbolic=_validated_markup(r"r_{BM} = \min\left(r_{BM,y},  r_{BM,r}\right)"),
            substituted=_validated_markup(
                rf"\min({cap_bm_yield:.2f}, {cap_bm_rupture:.2f}) = {cap_bm_gov:.2f} \text{{ kips/in.}}"
            ),
            variables={
                "Fy_p": Quantity("F_{y,p}", fy_p, "ksi", "Plate yield strength"),
                "Fu_p": Quantity("F_{u,p}", fu_p, "ksi", "Plate tensile strength"),
                "t_plate": Quantity("t_p", t_plate_in, "in.", "Bracket plate thickness"),
                "r_BM": Quantity("r_{BM}", round(cap_bm_gov, 3), "kips/in.", f"{method.value} base-metal shear capacity"),
            },
            result_value=round(cap_bm_gov, 3),
            result_unit="kips/in.",
            acceptance=AcceptanceCriterion(">=", round(bm_demand_plate, 3), "kips/in.", f"{method.value} bracket base-metal check", is_dcr_check=True),
            dcr=round(dcr_bm_plate, 3),
            status=CalculationStatus.PASS if dcr_bm_plate <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, ref_j2_5, ref_proc),
        ),
        CalcStep(
            step_id="S4_SUPPORT",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title=f"Supporting Member ({shape_sup['label']}) Flange Base-Metal Check",
            symbolic=_validated_markup(r"r_{sup} = \min\left(r_{sup,y},  r_{sup,r}\right)"),
            substituted=_validated_markup(
                rf"\min({cap_sup_yield:.2f}, {cap_sup_rupture:.2f}) = {cap_sup_gov:.2f} \text{{ kips/in.}}"
            ),
            variables={
                "t_sup": Quantity("t_{sup}", t_sup_in, "in.", "Supporting flange/wall thickness"),
                "r_sup": Quantity("r_{sup}", round(cap_sup_gov, 3), "kips/in.", f"{method.value} supporting base-metal capacity"),
            },
            result_value=round(cap_sup_gov, 3),
            result_unit="kips/in.",
            acceptance=AcceptanceCriterion(">=", round(r_demand_max, 3), "kips/in.", f"{method.value} supporting flange base-metal check", is_dcr_check=True),
            dcr=round(dcr_sup, 3),
            status=CalculationStatus.PASS if dcr_sup <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_shapes, ref_mat, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not weld_size_ok:
        warnings.append(
            f"Fillet weld size w={w_leg_in:.4f} in. outside code range [{w_min_in:.4f}, {w_max_in:.4f}] in."
        )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_welded_connection",
        code_edition="AISC 360-22 (16th Ed.)",
        design_method=method,
        input_parameters={
            "weld_config": weld_config,
            "w_leg_in": w_leg_in,
            "F_EXX_ksi": f_exx_ksi,
            "b_w_in": b_w_in,
            "d_w_in": d_w_in,
            "e_face_in": e_face_in,
            "plate_grade": plate_grade,
            "t_plate_in": t_plate_in,
            "support_section": support_section,
            "V_demand_kips": v_demand,
        },
        assumptions=[
            "Elastic vector method applied along weld throat centerline (conservative relative to ICOR).",
            "Directional strength enhancement (1 + 0.50*sin^1.5(theta)) conservatively omitted for eccentric C-welds and HSS joints.",
        ],
        intermediate_results={
            "L_w_in": round(l_w, 2),
            "x_bar_in": round(x_bar, 3),
            "e_cg_in": round(e_cg, 3),
            "I_p_in3": round(i_p, 2),
            "w_min_in": round(w_min_in, 4),
            "w_max_in": round(w_max_in, 4),
            "f_max_kips_per_in": round(r_demand_max, 3),
            "cap_weld_kips_per_in": round(cap_weld_per_in, 3),
            "t_support_in": round(t_sup_in, 3),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path for r in (ref_proc, ref_j2_4, ref_j2_5, ref_shapes, ref_mat) if r.source_path
        ],
        warnings=warnings,
        trace=trace,
    )
